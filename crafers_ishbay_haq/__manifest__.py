# -*- coding: utf-8 -*-
{
    'name': "Crafers — sex ishchilarining ishbay haqi",
    'summary': "Ishlab chiqarilgan dona miqdoriga qarab ish haqi hisobi",
    'description': """
Talab #7: «Sex ishchilari ishlab chiqargan miqdorga qarab haq oladi
(dona uchun narx).»

NIMA UCHUN KOD KERAK
--------------------
Standartda ma'lumot BOR, lekin hisob YO'Q:

* Shop Floor (`mrp_workorder` + `mrp_workorder_hr_account`) xodimning ish
  buyrug'iga sarflagan **vaqtini** yozadi (`mrp.workcenter.productivity`).
  Bu SOAT, dona emas.
* `mrp.workorder.qty_produced` ishlab chiqarilgan **dona**ni biladi, lekin
  uni xodimlar o'rtasida taqsimlamaydi.
* `hr_payroll` (Enterprise) bor, ammo `l10n_uz_hr_payroll` YO'Q — ya'ni
  O'zbekiston uchun tayyor ish haqi tuzilmasi kelmaydi. Ustiga payroll
  ishbay hisobni o'zi qilmaydi, unga tayyor summa kiritiladi.

STANDARTDA NIMA URINIB KO'RILDI
-------------------------------
1. Shop Floor hisobotidan (Ish markazi unumdorligi) xodim kesimida pivot
   olindi — u soatni beradi, donani emas. Ishbay haq uchun yaramaydi.
2. Studio: `mrp.workorder` ga hisoblanadigan maydon qo'shib, keyin
   xodim kesimida yig'ish. Bir necha model bo'ylab agregatsiya kerak
   bo'lgani uchun mo'rt chiqadi va davrlarga bo'lishni uddalamaydi.

SHU MODUL NIMA QILADI
---------------------
Ish buyrug'ida ishlab chiqarilgan miqdorni xodimlar o'rtasida SHU
buyurtmaga sarflagan vaqtlari ulushiga qarab bo'ladi va operatsiyaning
dona narxiga ko'paytiradi.

Ulush maxraji — ish buyrug'ining butun vaqti, surati esa faqat hisob
davridagi vaqt. Shunda ish buyrug'i ikki oyga cho'zilsa ham miqdor ikki
marta hisoblanmaydi.

`hr_payroll` ga bog'lanmaydi: natija alohida hujjat, uni oylikka qo'lda
yoki keyingi bosqichda avtomatik kiritish mumkin.
""",
    'author': "NOVA CODE",
    'website': "https://novaodoo.uz",
    'category': 'Crafers/Manufacturing',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['mrp_workorder', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/ishbay_hisob_views.xml',
        'views/mrp_bom_views.xml',
    ],
    'installable': True,
    'application': False,
}
