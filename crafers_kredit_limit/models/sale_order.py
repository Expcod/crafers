# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

HOLAT = [
    ('yoq', 'Talab qilinmaydi'),
    ('kutilmoqda', 'Menejer tasdig\'i kutilmoqda'),
    ('tasdiqlangan', 'Menejer tasdiqlagan'),
    ('rad_etilgan', 'Menejer rad etgan'),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Hisoblanadigan ko'rsatkichlar.
    # HECH BIRI SAQLANMAYDI: har o'qishda qaytadan hisoblanadi, shuning
    # uchun mijozning qarzi o'zgarsa ham qiymat eskirmaydi. Studio yechimi
    # aynan shu joyda qulaydi (qarang: __manifest__.py).
    # ------------------------------------------------------------------
    kredit_limit = fields.Monetary(
        string='Kredit limiti', compute='_compute_kredit', currency_field='company_currency_id')
    kredit_joriy_qarz = fields.Monetary(
        string='Joriy qarz', compute='_compute_kredit', currency_field='company_currency_id',
        help="Kitobga olingan debitorlik + tasdiqlangan, lekin hali faktura "
             "qilinmagan buyurtmalar.")
    kredit_buyurtma_summasi = fields.Monetary(
        string='Shu buyurtma', compute='_compute_kredit', currency_field='company_currency_id',
        help='Buyurtma summasi kompaniya valyutasida.')
    kredit_yangi_qoldiq = fields.Monetary(
        string='Tasdiqlangandan keyingi qarz', compute='_compute_kredit',
        currency_field='company_currency_id')
    kredit_oshgan_summa = fields.Monetary(
        string='Limitdan oshgan summa', compute='_compute_kredit',
        currency_field='company_currency_id')
    kredit_limitdan_oshdi = fields.Boolean(
        string='Limitdan oshdi', compute='_compute_kredit')

    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Kompaniya valyutasi')

    # --- tasdiqlash holati (bu esa saqlanadi) --------------------------
    kredit_holat = fields.Selection(
        HOLAT, string='Kredit tasdig\'i', default='yoq', copy=False, tracking=True)
    kredit_tasdiqlagan_id = fields.Many2one(
        'res.users', string='Tasdiqlagan/rad etgan', readonly=True, copy=False)
    kredit_tasdiq_sana = fields.Datetime(
        string='Tasdiq vaqti', readonly=True, copy=False)
    kredit_izoh = fields.Text(
        string='Menejer izohi', copy=False,
        help='Rad etish sababi yoki tasdiqlash sharti.')

    # ==================================================================
    # Hisob
    # ==================================================================
    @api.depends('partner_id', 'amount_total', 'currency_rate', 'company_id')
    def _compute_kredit(self):
        for order in self:
            order.kredit_limit = 0.0
            order.kredit_joriy_qarz = 0.0
            order.kredit_buyurtma_summasi = 0.0
            order.kredit_yangi_qoldiq = 0.0
            order.kredit_oshgan_summa = 0.0
            order.kredit_limitdan_oshdi = False

            if not order.partner_id or not order.company_id.account_use_credit_limit:
                continue

            # `credit` va `credit_limit` buxgalteriya guruhlari bilan
            # himoyalangan - sotuvchi ularni o'qiy olmaydi. Odoo ning o'zi
            # ham shu sababdan sudo ishlatadi (sale_order.py:786).
            partner = order.partner_id.commercial_partner_id.sudo()
            limit = partner.credit_limit
            if not limit:
                continue

            # Buyurtma valyutasidan kompaniya valyutasiga - Odoo ning o'z
            # usuli (_compute_partner_credit_warning da ham shunday).
            rate = order.currency_rate or 1.0
            buyurtma = order.amount_total / rate

            # credit          = kitobga olingan debitorlik
            # credit_to_invoice = tasdiqlangan, hali faktura qilinmagan SO lar
            # Joriy qoralama buyurtma credit_to_invoice ga KIRMAYDI (u faqat
            # tasdiqlangan buyurtmalarni sanaydi), shuning uchun ikki marta
            # hisoblanmaydi.
            qarz = partner.credit + partner.credit_to_invoice

            order.kredit_limit = limit
            order.kredit_joriy_qarz = qarz
            order.kredit_buyurtma_summasi = buyurtma
            order.kredit_yangi_qoldiq = qarz + buyurtma
            oshgan = (qarz + buyurtma) - limit
            if order.company_currency_id.compare_amounts(oshgan, 0) > 0:
                order.kredit_limitdan_oshdi = True
                order.kredit_oshgan_summa = oshgan

    # ==================================================================
    # Bloklash
    # ==================================================================
    def _kredit_bloklanadimi(self):
        """Buyurtma menejer tasdig'isiz tasdiqlanmasligi kerakmi?"""
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            return False
        if self.kredit_holat == 'tasdiqlangan':
            return False

        # `credit` va `credit_to_invoice` compute'ida maydonga bog'liqlik yo'q
        # (faqat @api.depends_context('company')), shuning uchun bitta
        # tranzaksiya ichida kesh eskirib qolishi mumkin: masalan shu so'rovda
        # boshqa buyurtma tasdiqlangan bo'lsa qarz yangilanmaydi. Tasdiqlash -
        # yagona qaror nuqtasi, shuning uchun aynan shu yerda keshni tozalaymiz.
        partner = self.partner_id.commercial_partner_id
        partner.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.invalidate_recordset([
            'kredit_limitdan_oshdi', 'kredit_joriy_qarz', 'kredit_yangi_qoldiq',
            'kredit_oshgan_summa', 'kredit_limit', 'kredit_buyurtma_summasi'])
        return self.kredit_limitdan_oshdi

    def _kredit_xabar_matni(self):
        self.ensure_one()
        val = self.company_currency_id

        def f(summa):
            # 1 234 567 ko'rinishida (o'zbekcha ajratgich - probel)
            return format(summa, ',.0f').replace(',', ' ')

        return _(
            "«%(mijoz)s» uchun kredit limiti oshib ketadi.\n\n"
            "  Limit                       : %(limit)s %(val)s\n"
            "  Joriy qarz                  : %(qarz)s %(val)s\n"
            "  Shu buyurtma                : %(buyurtma)s %(val)s\n"
            "  ─────────────────────────────────────────────\n"
            "  Tasdiqlangandan keyin       : %(yangi)s %(val)s\n"
            "  LIMITDAN OSHADI             : %(oshgan)s %(val)s",
            mijoz=self.partner_id.display_name,
            limit=f(self.kredit_limit),
            qarz=f(self.kredit_joriy_qarz),
            buyurtma=f(self.kredit_buyurtma_summasi),
            yangi=f(self.kredit_yangi_qoldiq),
            oshgan=f(self.kredit_oshgan_summa),
            val=val.symbol or val.name,
        )

    def _kredit_menejerlar(self):
        guruh = self.env.ref(
            'crafers_kredit_limit.group_kredit_menejer', raise_if_not_found=False)
        return guruh.sudo().all_user_ids if guruh else self.env['res.users']

    def _kredit_sorov_ochish(self):
        """Holatni «kutilmoqda» ga o'tkazib, menejerga vazifa qo'yadi."""
        menejerlar = self._kredit_menejerlar()
        for order in self:
            order.kredit_holat = 'kutilmoqda'
            order.message_post(
                body=order._kredit_xabar_matni().replace('\n', '<br/>'),
                subject=_('Kredit limiti: menejer tasdig\'i kerak'))
            for user in menejerlar:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=_('Kredit limitidan oshgan buyurtmani ko\'rib chiqish'),
                    note=order._kredit_xabar_matni().replace('\n', '<br/>'))

    def action_confirm(self):
        # Ma'lumot ko'chirish / avtomatik oqimlar uchun ataylab chiqish yo'li.
        if self.env.context.get('skip_kredit_tekshiruvi'):
            return super().action_confirm()

        bloklangan = self.filtered(lambda o: o._kredit_bloklanadimi())
        if not bloklangan:
            return super().action_confirm()

        bloklangan._kredit_sorov_ochish()
        qolgan = self - bloklangan
        res = super(SaleOrder, qolgan).action_confirm() if qolgan else True

        if len(bloklangan) == 1:
            xabar = bloklangan._kredit_xabar_matni()
        else:
            xabar = _('%s ta buyurtma kredit limitidan oshdi va menejer '
                      'tasdig\'iga yuborildi.', len(bloklangan))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'title': _('Buyurtma to\'xtatildi'),
                'message': xabar,
                'sticky': True,
                'next': res if isinstance(res, dict) else {'type': 'ir.actions.act_window_close'},
            },
        }

    # ==================================================================
    # Menejer tugmalari
    # ==================================================================
    def _kredit_huquq_tekshir(self):
        if not self.env.user.has_group('crafers_kredit_limit.group_kredit_menejer'):
            raise AccessError(_(
                'Kredit limitidan oshgan buyurtmani faqat savdo menejeri '
                'tasdiqlashi yoki rad etishi mumkin.'))

    def action_kredit_tasdiqlash(self):
        self._kredit_huquq_tekshir()
        for order in self:
            if order.kredit_holat != 'kutilmoqda':
                raise UserError(_('«%s» tasdiq kutayotgan holatda emas.', order.display_name))
            order.write({
                'kredit_holat': 'tasdiqlangan',
                'kredit_tasdiqlagan_id': self.env.user.id,
                'kredit_tasdiq_sana': fields.Datetime.now(),
            })
            order.message_post(body=_(
                'Kredit limitidan oshish <b>tasdiqlandi</b> — %(user)s. '
                'Oshgan summa: %(summa)s',
                user=self.env.user.display_name,
                summa=order.kredit_oshgan_summa))
            order.activity_unlink(['mail.mail_activity_data_todo'])
        # Tasdiqdan keyin buyurtma darhol o'tsin.
        return self.action_confirm()

    def action_kredit_rad_etish(self):
        self._kredit_huquq_tekshir()
        for order in self:
            if order.kredit_holat != 'kutilmoqda':
                raise UserError(_('«%s» tasdiq kutayotgan holatda emas.', order.display_name))
            order.write({
                'kredit_holat': 'rad_etilgan',
                'kredit_tasdiqlagan_id': self.env.user.id,
                'kredit_tasdiq_sana': fields.Datetime.now(),
            })
            order.message_post(body=_(
                'Kredit limitidan oshish <b>rad etildi</b> — %(user)s.%(izoh)s',
                user=self.env.user.display_name,
                izoh=(' Sabab: %s' % order.kredit_izoh) if order.kredit_izoh else ''))
            order.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_kredit_qayta_sorash(self):
        """Rad etilgandan keyin (masalan mijoz to'lov qilgach) qayta so'rash."""
        for order in self:
            if order.kredit_holat not in ('rad_etilgan', 'tasdiqlangan'):
                raise UserError(_('«%s» qayta so\'rash holatida emas.', order.display_name))
            order.write({
                'kredit_holat': 'yoq',
                'kredit_tasdiqlagan_id': False,
                'kredit_tasdiq_sana': False,
            })
        return True
