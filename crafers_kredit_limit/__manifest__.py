# -*- coding: utf-8 -*-
{
    'name': "Crafers — kredit limiti va menejer tasdig'i",
    'summary': "Ulgurji mijoz limitidan oshsa buyurtma to'xtaydi, menejer tasdiqlaydi",
    'description': """
Talab #5: «Ulgurji mijozlar nasiyaga oladi, har birining limiti bor.
Limitdan oshsa — buyurtma to'xtasin, menejer tasdiqlasin.»

NIMA UCHUN KOD KERAK
--------------------
Odoo 19 standarti kredit limitini biladi (`res.partner.credit_limit`,
`res.company.account_use_credit_limit`), lekin limitdan oshganda faqat
**ogohlantirish matnini** ko'rsatadi — `sale.order.partner_credit_warning`
(sale/models/sale_order.py:778). Tasdiqlashni to'xtatmaydi va «menejer
tasdig'i» degan tushuncha umuman yo'q.

STANDARTDA NIMA URINIB KO'RILDI
-------------------------------
1. `account_use_credit_limit` yoqildi va 30 mijozga limit qo'yildi —
   buyurtma baribir tasdiqlanaverdi, faqat sariq lenta chiqdi.
2. Studio Approval Rules (`studio.approval.rule`) ko'rib chiqildi. U server
   tomonda metodni patch qiladi va `domain` orqali shartli ishlaydi, ya'ni
   mexanizm bor. Ammo domen **saqlanadigan** maydon talab qiladi, `credit`
   esa `store=False` va uning compute'ida (`account/models/partner.py:500,
   `_credit_debit_get`) birorta maydonga bog'liqlik yo'q — faqat
   `@api.depends_context('company')`. Demak unga tayangan saqlanadigan
   maydon mijoz qarzi o'zgarganda hech qachon qayta hisoblanmaydi va
   limitdan oshgan buyurtma jimgina o'tib ketadi. Aynan talab tekshiradigan
   joyda teshik.
3. Studio yana bir kamchilik: `self.env.su` bo'lsa tasdiq umuman
   o'tkazib yuboriladi (web_studio/models/studio_approval.py:403).

SHU MODUL NIMA QILADI
---------------------
Tekshiruv `action_confirm()` chaqirilgan **aniq daqiqada** bajariladi,
saqlanadigan maydon yo'q — eskirish mumkin emas.
""",
    'author': "NOVA CODE",
    'website': "https://novaodoo.uz",
    'category': 'Crafers/Sales',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['sale'],
    'data': [
        'security/res_groups.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
