# -*- coding: utf-8 -*-
"""Ishbay haq hisobi sinovlari."""
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestIshbayHaq(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wc = cls.env['mrp.workcenter'].create({
            'name': 'Sinov qadoqlash', 'costs_hour': 50000,
        })
        cls.mahsulot = cls.env['product.product'].create({
            'name': 'Sinov plitka', 'type': 'consu', 'is_storable': True,
        })
        cls.xomashyo = cls.env['product.product'].create({
            'name': 'Sinov shakar', 'type': 'consu', 'is_storable': True,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.mahsulot.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': cls.xomashyo.id, 'product_qty': 1})],
            'operation_ids': [(0, 0, {
                'name': 'Qadoqlash',
                'workcenter_id': cls.wc.id,
                'time_cycle_manual': 30,
                'ishbay_narx': 200.0,          # 200 so'm / dona
            })],
        })
        cls.ali = cls.env['hr.employee'].create({'name': 'Ali Ishchi'})
        cls.vali = cls.env['hr.employee'].create({'name': 'Vali Ishchi'})
        cls.productive = cls.env['mrp.workcenter.productivity.loss'].search(
            [('loss_type', '=', 'productive')], limit=1)

    def _ish_buyrugi(self, qty=100):
        mo = self.env['mrp.production'].create({
            'product_id': self.mahsulot.id,
            'product_qty': qty,
            'bom_id': self.bom.id,
        })
        mo.action_confirm()
        wo = mo.workorder_ids[:1]
        self.assertTrue(wo, 'BoM operatsiyasidan ish buyrug\'i chiqishi kerak')
        wo.qty_produced = qty
        return wo

    def _vaqt(self, wo, xodim, daqiqa, kun_oldin=0):
        boshi = datetime.now() - timedelta(days=kun_oldin, minutes=daqiqa)
        return self.env['mrp.workcenter.productivity'].create({
            'workorder_id': wo.id,
            'workcenter_id': wo.workcenter_id.id,
            'employee_id': xodim.id,
            'loss_id': self.productive.id,
            'date_start': boshi,
            'date_end': boshi + timedelta(minutes=daqiqa),
        })

    def _hisob(self, kun=7):
        return self.env['crafers.ishbay.hisob'].create({
            'sana_boshi': fields.Date.today() - timedelta(days=kun),
            'sana_oxiri': fields.Date.today(),
        })

    # ------------------------------------------------------------------
    def test_01_vaqt_ulushiga_qarab_bolinadi(self):
        """100 dona, Ali 60 daq, Vali 20 daq -> 75/25 dona, 15 000/5 000 so'm."""
        wo = self._ish_buyrugi(100)
        self._vaqt(wo, self.ali, 60)
        self._vaqt(wo, self.vali, 20)

        hisob = self._hisob()
        hisob.action_hisoblash()

        self.assertEqual(hisob.state, 'hisoblangan')
        self.assertEqual(len(hisob.qator_ids), 2)

        ali = hisob.qator_ids.filtered(lambda q: q.employee_id == self.ali)
        vali = hisob.qator_ids.filtered(lambda q: q.employee_id == self.vali)

        self.assertAlmostEqual(ali.miqdor, 75.0, places=2)
        self.assertAlmostEqual(vali.miqdor, 25.0, places=2)
        self.assertAlmostEqual(ali.summa, 15000.0, places=2)
        self.assertAlmostEqual(vali.summa, 5000.0, places=2)
        self.assertAlmostEqual(hisob.jami_summa, 20000.0, places=2)
        self.assertAlmostEqual(hisob.jami_miqdor, 100.0, places=2,
                               msg='taqsimlangan dona jami ishlab chiqarilganga teng bo\'lsin')

    def test_02_bir_xodim_hammasini_oladi(self):
        wo = self._ish_buyrugi(50)
        self._vaqt(wo, self.ali, 40)

        hisob = self._hisob()
        hisob.action_hisoblash()

        self.assertEqual(len(hisob.qator_ids), 1)
        self.assertAlmostEqual(hisob.qator_ids.miqdor, 50.0, places=2)
        self.assertAlmostEqual(hisob.qator_ids.summa, 10000.0, places=2)
        self.assertAlmostEqual(hisob.qator_ids.ulush, 100.0, places=1)

    def test_03_davrdan_tashqari_vaqt_ikki_marta_sanalmaydi(self):
        """Ish buyrug'i ikki davrga cho'zilsa miqdor ikki marta berilmaydi.

        Ali 30 kun oldin 60 daq ishlagan (davrdan tashqarida),
        Vali kecha 20 daq. Hisob davri - oxirgi 7 kun.
        Vali faqat o'z ulushini (20/80 = 25 dona) olishi kerak, hammasini emas.
        """
        wo = self._ish_buyrugi(100)
        self._vaqt(wo, self.ali, 60, kun_oldin=30)
        self._vaqt(wo, self.vali, 20, kun_oldin=1)

        hisob = self._hisob(kun=7)
        hisob.action_hisoblash()

        self.assertEqual(len(hisob.qator_ids), 1, 'faqat Vali kirishi kerak')
        self.assertEqual(hisob.qator_ids.employee_id, self.vali)
        self.assertAlmostEqual(hisob.qator_ids.miqdor, 25.0, places=2,
                               msg='ulush maxraji butun ish buyrug\'i vaqti bo\'lsin')

    def test_04_narxsiz_operatsiya_hisobga_kirmaydi(self):
        self.bom.operation_ids.ishbay_narx = 0.0
        wo = self._ish_buyrugi(100)
        self._vaqt(wo, self.ali, 60)

        hisob = self._hisob()
        hisob.action_hisoblash()

        self.assertFalse(hisob.qator_ids)
        self.assertTrue(hisob.ogohlantirish, 'sabab yozilishi kerak')
        self.assertIn('narx', hisob.ogohlantirish.lower())

    def test_05_vaqt_yozilmagan_bolsa_ogohlantiradi(self):
        self._ish_buyrugi(100)          # vaqt yozilmadi
        hisob = self._hisob()
        hisob.action_hisoblash()

        self.assertFalse(hisob.qator_ids)
        self.assertTrue(hisob.ogohlantirish)

    def test_06_qayta_hisoblash_takrorlamaydi(self):
        wo = self._ish_buyrugi(100)
        self._vaqt(wo, self.ali, 60)

        hisob = self._hisob()
        hisob.action_hisoblash()
        birinchi = hisob.jami_summa
        hisob.action_hisoblash()

        self.assertEqual(len(hisob.qator_ids), 1, 'qatorlar ikkilanmasin')
        self.assertAlmostEqual(hisob.jami_summa, birinchi, places=2)

    def test_07_tasdiqlangach_qayta_hisoblanmaydi(self):
        from odoo.exceptions import UserError
        wo = self._ish_buyrugi(100)
        self._vaqt(wo, self.ali, 60)

        hisob = self._hisob()
        hisob.action_hisoblash()
        hisob.action_tasdiqlash()
        self.assertEqual(hisob.state, 'tasdiqlangan')

        with self.assertRaises(UserError):
            hisob.action_hisoblash()

    def test_08_raqam_beriladi(self):
        hisob = self._hisob()
        self.assertTrue(hisob.name.startswith('ISHBAY/'),
                        'ketma-ketlikdan raqam olinsin: %s' % hisob.name)
