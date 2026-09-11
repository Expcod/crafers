# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    ishbay_narx = fields.Float(
        string='Ishbay narx (dona uchun)', digits='Product Price',
        help="Shu operatsiyada ishlagan xodimga bir dona tayyor mahsulot "
             "uchun to'lanadigan summa. 0 bo'lsa operatsiya ishbay haqqa "
             "kirmaydi (masalan texnolog nazorati).")


class IshbayHisob(models.Model):
    _name = 'crafers.ishbay.hisob'
    _description = "Sex ishchilarining ishbay haqi"
    _inherit = ['mail.thread']
    _order = 'sana_oxiri desc, id desc'

    name = fields.Char(string='Raqam', default=lambda s: _('Yangi'),
                       readonly=True, copy=False)
    sana_boshi = fields.Date(string='Davr boshi', required=True,
                             default=lambda s: fields.Date.today().replace(day=1))
    sana_oxiri = fields.Date(string='Davr oxiri', required=True,
                             default=lambda s: fields.Date.today())
    state = fields.Selection([
        ('qoralama', 'Qoralama'),
        ('hisoblangan', 'Hisoblangan'),
        ('tasdiqlangan', "To'lovga tasdiqlangan"),
    ], string='Holat', default='qoralama', tracking=True, copy=False)

    qator_ids = fields.One2many('crafers.ishbay.qator', 'hisob_id',
                                string='Qatorlar', copy=False)
    jami_summa = fields.Monetary(string='Jami summa', compute='_compute_jami',
                                 store=True, currency_field='currency_id')
    jami_miqdor = fields.Float(string='Jami dona', compute='_compute_jami', store=True)
    xodim_soni = fields.Integer(string='Xodimlar soni', compute='_compute_jami', store=True)
    ogohlantirish = fields.Text(string='Diqqat', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Kompaniya', required=True,
                                 default=lambda s: s.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.depends('qator_ids.summa', 'qator_ids.miqdor', 'qator_ids.employee_id')
    def _compute_jami(self):
        for hisob in self:
            hisob.jami_summa = sum(hisob.qator_ids.mapped('summa'))
            hisob.jami_miqdor = sum(hisob.qator_ids.mapped('miqdor'))
            hisob.xodim_soni = len(hisob.qator_ids.employee_id)

    @api.constrains('sana_boshi', 'sana_oxiri')
    def _check_sanalar(self):
        for hisob in self:
            if hisob.sana_boshi > hisob.sana_oxiri:
                raise UserError(_('Davr boshi oxiridan keyin bo\'lishi mumkin emas.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Yangi')) == _('Yangi'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'crafers.ishbay.hisob') or _('Yangi')
        return super().create(vals_list)

    # ==================================================================
    # Hisoblash
    # ==================================================================
    def action_hisoblash(self):
        """Shop Floor da yozilgan vaqtdan ishbay haqni hisoblaydi.

        Mantiq: ish buyrug'ida ishlab chiqarilgan miqdor xodimlar o'rtasida
        SHU ish buyrug'iga sarflagan vaqtlari ulushiga qarab bo'linadi, keyin
        operatsiyaning dona narxiga ko'paytiriladi.

        Ulush maxraji - ish buyrug'ining BUTUN vaqti (davrdan tashqarisi ham),
        surati esa faqat shu davrdagi vaqt. Shunda ish buyrug'i ikki davrga
        cho'zilsa ham miqdor ikki marta hisoblanmaydi.
        """
        self.ensure_one()
        if self.state == 'tasdiqlangan':
            raise UserError(_('Tasdiqlangan hisobni qayta hisoblab bo\'lmaydi.'))
        self.qator_ids.unlink()

        Vaqt = self.env['mrp.workcenter.productivity']
        davr = [
            ('date_end', '>=', fields.Datetime.to_datetime(self.sana_boshi)),
            ('date_end', '<=', fields.Datetime.to_datetime(self.sana_oxiri).replace(
                hour=23, minute=59, second=59)),
            ('employee_id', '!=', False),
            ('workorder_id', '!=', False),
            ('loss_type', '=', 'productive'),
            ('company_id', '=', self.company_id.id),
        ]
        davr_yozuvlari = Vaqt.search(davr)
        if not davr_yozuvlari:
            self.ogohlantirish = _(
                "Bu davrda Shop Floor da yozilgan xodim vaqti topilmadi. "
                "Ishbay haq faqat xodim ish buyrug'ini o'z nomidan boshlab-"
                "to'xtatgan bo'lsa hisoblanadi.")
            self.state = 'hisoblangan'
            return

        # davrdagi vaqt: {(workorder, employee): daqiqa}
        davr_vaqti = defaultdict(float)
        for y in davr_yozuvlari:
            davr_vaqti[(y.workorder_id, y.employee_id)] += y.duration

        # ish buyrug'ining butun vaqti (ulush maxraji uchun)
        wo_lar = davr_yozuvlari.workorder_id
        butun_yozuvlar = Vaqt.search([
            ('workorder_id', 'in', wo_lar.ids),
            ('employee_id', '!=', False),
            ('loss_type', '=', 'productive'),
        ])
        butun_vaqt = defaultdict(float)
        for y in butun_yozuvlar:
            butun_vaqt[y.workorder_id] += y.duration

        qatorlar = []
        narxsiz, miqdorsiz = set(), set()
        for (wo, xodim), daqiqa in davr_vaqti.items():
            if not wo.qty_produced:
                miqdorsiz.add(wo.display_name)
                continue
            narx = wo.operation_id.ishbay_narx
            if not narx:
                narxsiz.add(wo.operation_id.display_name or wo.display_name)
                continue
            umumiy = butun_vaqt.get(wo, 0.0)
            if not umumiy:
                continue
            ulush = daqiqa / umumiy
            miqdor = wo.qty_produced * ulush
            qatorlar.append({
                'hisob_id': self.id,
                'employee_id': xodim.id,
                'workorder_id': wo.id,
                'ishbay_narx': narx,
                'wo_miqdor': wo.qty_produced,
                'xodim_vaqti': daqiqa,
                'umumiy_vaqt': umumiy,
                'miqdor': miqdor,
                'summa': miqdor * narx,
            })

        self.env['crafers.ishbay.qator'].create(qatorlar)

        ogoh = []
        if narxsiz:
            ogoh.append(_(
                "%(soni)s ta operatsiyada dona narxi qo'yilmagan, ular "
                "hisobga kirmadi: %(royxat)s",
                soni=len(narxsiz), royxat=', '.join(sorted(narxsiz)[:5])))
        if miqdorsiz:
            ogoh.append(_(
                "%(soni)s ta ish buyrug'ida ishlab chiqarilgan miqdor 0.",
                soni=len(miqdorsiz)))
        self.ogohlantirish = '\n'.join(ogoh) or False
        self.state = 'hisoblangan'
        self.message_post(body=_(
            'Hisoblandi: %(xodim)s xodim, %(dona).2f dona, %(summa)s.',
            xodim=self.xodim_soni, dona=self.jami_miqdor,
            summa=self.jami_summa))

    def action_tasdiqlash(self):
        for hisob in self:
            if hisob.state != 'hisoblangan':
                raise UserError(_('Avval hisoblang.'))
            if not hisob.qator_ids:
                raise UserError(_('Bo\'sh hisobni tasdiqlab bo\'lmaydi.'))
            hisob.state = 'tasdiqlangan'
        return True

    def action_qoralamaga(self):
        self.write({'state': 'qoralama'})
        return True

    def action_qatorlarni_korish(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ishbay haq qatorlari'),
            'res_model': 'crafers.ishbay.qator',
            'view_mode': 'list,pivot',
            'domain': [('hisob_id', '=', self.id)],
            'context': {'search_default_group_employee': 1},
        }


class IshbayQator(models.Model):
    _name = 'crafers.ishbay.qator'
    _description = 'Ishbay haq qatori'
    _order = 'employee_id, id'

    hisob_id = fields.Many2one('crafers.ishbay.hisob', string='Hisob',
                               required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Xodim',
                                  required=True, index=True)
    workorder_id = fields.Many2one('mrp.workorder', string='Ish buyrug\'i',
                                   required=True)
    production_id = fields.Many2one(related='workorder_id.production_id',
                                    string='Ishlab chiqarish', store=True)
    product_id = fields.Many2one(related='workorder_id.product_id',
                                 string='Mahsulot', store=True)
    operation_id = fields.Many2one(related='workorder_id.operation_id',
                                   string='Operatsiya', store=True)
    workcenter_id = fields.Many2one(related='workorder_id.workcenter_id',
                                    string='Ish markazi', store=True)

    ishbay_narx = fields.Float(string='Dona narxi', digits='Product Price')
    wo_miqdor = fields.Float(string='Buyurtma miqdori',
                             help="Ish buyrug'ida jami ishlab chiqarilgan dona.")
    xodim_vaqti = fields.Float(string='Xodim vaqti (daq)')
    umumiy_vaqt = fields.Float(string='Umumiy vaqt (daq)')
    ulush = fields.Float(string='Ulush, %', compute='_compute_ulush', store=True)
    miqdor = fields.Float(string='Tegishli dona')
    summa = fields.Monetary(string='Summa', currency_field='currency_id')

    company_id = fields.Many2one(related='hisob_id.company_id', store=True)
    currency_id = fields.Many2one(related='hisob_id.currency_id')
    sana_oxiri = fields.Date(related='hisob_id.sana_oxiri', store=True,
                             string='Davr oxiri')

    @api.depends('xodim_vaqti', 'umumiy_vaqt')
    def _compute_ulush(self):
        for q in self:
            q.ulush = (q.xodim_vaqti / q.umumiy_vaqt * 100) if q.umumiy_vaqt else 0.0
