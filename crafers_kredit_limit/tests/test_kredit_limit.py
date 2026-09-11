# -*- coding: utf-8 -*-
"""Kredit limiti va menejer tasdig'i sinovlari.

Ishga tushirish:
    python run_odoo.py -c odoo-crafers.conf -d <baza> \
        -u crafers_kredit_limit --test-enable --stop-after-init
"""
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKreditLimit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.sudo().account_use_credit_limit = True
        cls.mahsulot = cls.env['product.product'].create({
            'name': 'Sinov shokolad',
            'type': 'consu',
            'list_price': 100000.0,
        })
        cls.mijoz = cls.env['res.partner'].create({
            'name': 'Sinov Ulgurji MCHJ',
            'is_company': True,
            'customer_rank': 1,
            'credit_limit': 1000000.0,
        })

    def _buyurtma(self, qty):
        return self.env['sale.order'].create({
            'partner_id': self.mijoz.id,
            'order_line': [(0, 0, {
                'product_id': self.mahsulot.id,
                'product_uom_qty': qty,
            })],
        })

    # ------------------------------------------------------------------
    def test_01_limit_ichida_tasdiqlanadi(self):
        """Limitdan oshmasa buyurtma odatdagidek tasdiqlanadi."""
        so = self._buyurtma(5)
        self.assertFalse(so.kredit_limitdan_oshdi)
        so.action_confirm()
        self.assertEqual(so.state, 'sale')
        self.assertEqual(so.kredit_holat, 'yoq',
                         "limit ichidagi buyurtma tasdiq so'ramasligi kerak")

    def test_02_limitdan_oshsa_bloklanadi(self):
        """Limitdan oshsa buyurtma tasdiqlanmaydi va menejerga yuboriladi."""
        so = self._buyurtma(20)
        res = so.action_confirm()

        self.assertIn(so.state, ('draft', 'sent'), 'buyurtma tasdiqlanmasligi kerak')
        self.assertEqual(so.kredit_holat, 'kutilmoqda')
        self.assertTrue(so.kredit_limitdan_oshdi)
        self.assertGreater(so.kredit_oshgan_summa, 0)
        self.assertEqual(res.get('tag'), 'display_notification',
                         'foydalanuvchiga sabab ko\'rsatilishi kerak')
        akt = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'), ('res_id', '=', so.id)])
        self.assertTrue(akt, "menejerga vazifa qo'yilishi kerak")

    def test_03_oldingi_buyurtmalar_ham_sanaladi(self):
        """Tasdiqlangan, hali faktura qilinmagan buyurtma ham qarzga kiradi.

        Bu `credit_to_invoice` keshi bilan bog'liq: uning compute'ida maydonga
        bog'liqlik yo'q, shuning uchun modul tasdiqlash daqiqasida keshni
        tozalaydi. Busiz oldingi buyurtmaning ta'siri e'tibordan chetda qolardi.
        """
        birinchi = self._buyurtma(6)          # 600 000 + soliq
        birinchi.action_confirm()
        self.assertEqual(birinchi.state, 'sale')

        ikkinchi = self._buyurtma(5)          # 500 000 + soliq
        ikkinchi.action_confirm()
        self.assertEqual(
            ikkinchi.kredit_holat, 'kutilmoqda',
            'ikkala buyurtma birgalikda limitdan oshadi, ikkinchisi bloklanishi kerak')

    def test_04_faqat_menejer_tasdiqlaydi(self):
        so = self._buyurtma(20)
        so.action_confirm()

        sotuvchi = self.env['res.users'].create({
            'name': 'Oddiy sotuvchi',
            'login': 'sinov_sotuvchi_test',
            'group_ids': [(6, 0, [self.env.ref('sales_team.group_sale_salesman').id])],
        })
        with self.assertRaises(AccessError):
            so.with_user(sotuvchi).action_kredit_tasdiqlash()
        with self.assertRaises(AccessError):
            so.with_user(sotuvchi).action_kredit_rad_etish()

    def test_05_menejer_tasdiqlagach_otadi(self):
        so = self._buyurtma(20)
        so.action_confirm()
        so.action_kredit_tasdiqlash()

        self.assertEqual(so.kredit_holat, 'tasdiqlangan')
        self.assertEqual(so.state, 'sale', 'tasdiqdan keyin buyurtma o\'tishi kerak')
        self.assertTrue(so.kredit_tasdiqlagan_id)
        self.assertTrue(so.kredit_tasdiq_sana)
        akt = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'), ('res_id', '=', so.id)])
        self.assertFalse(akt, 'vazifa yopilishi kerak')

    def test_06_rad_etilgan_otmaydi(self):
        so = self._buyurtma(20)
        so.action_confirm()
        so.kredit_izoh = 'Mijoz eski qarzini yopmagan'
        so.action_kredit_rad_etish()

        self.assertEqual(so.kredit_holat, 'rad_etilgan')
        so.action_confirm()
        self.assertIn(so.state, ('draft', 'sent'),
                      'rad etilgandan keyin ham tasdiqlanmasligi kerak')

    def test_07_holat_notogri_bolsa_xato(self):
        so = self._buyurtma(5)          # limit ichida, tasdiq kutmaydi
        with self.assertRaises(UserError):
            so.action_kredit_tasdiqlash()

    def test_08_kontekst_bilan_chetlab_otish(self):
        """Ma'lumot ko'chirish uchun ataylab qoldirilgan chiqish yo'li."""
        so = self._buyurtma(20)
        so.with_context(skip_kredit_tekshiruvi=True).action_confirm()
        self.assertEqual(so.state, 'sale')

    def test_09_limitsiz_mijoz_tekshirilmaydi(self):
        limitsiz = self.env['res.partner'].create({
            'name': 'Limitsiz mijoz', 'is_company': True, 'customer_rank': 1,
        })
        so = self.env['sale.order'].create({
            'partner_id': limitsiz.id,
            'order_line': [(0, 0, {
                'product_id': self.mahsulot.id, 'product_uom_qty': 500})],
        })
        self.assertFalse(so.kredit_limitdan_oshdi)
        so.action_confirm()
        self.assertEqual(so.state, 'sale')

    def test_10_kompaniya_sozlamasi_ochiq_bolsa(self):
        """`account_use_credit_limit` o'chiq bo'lsa modul aralashmaydi."""
        self.env.company.sudo().account_use_credit_limit = False
        so = self._buyurtma(20)
        self.assertFalse(so.kredit_limitdan_oshdi)
        so.action_confirm()
        self.assertEqual(so.state, 'sale')
