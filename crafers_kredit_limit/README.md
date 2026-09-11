# crafers_kredit_limit

**Talab #5:** «Ulgurji mijozlar nasiyaga oladi, har birining limiti bor.
Limitdan oshsa — buyurtma to'xtasin, menejer tasdiqlasin.»

---

## Nima uchun kod kerak bo'ldi

Odoo 19 kredit limitini **biladi** — `res.partner.credit_limit` va
`res.company.account_use_credit_limit` standart maydonlar. Lekin limitdan
oshganda u faqat **sariq ogohlantirish lentasini** ko'rsatadi:

```python
# sale/models/sale_order.py:778
@api.depends('company_id', 'partner_id', 'amount_total')
def _compute_partner_credit_warning(self):
    ...
    order.partner_credit_warning = self.env['account.move']._build_credit_warning_message(...)
```

Bu matn. Tasdiqlashni to'xtatmaydi, «menejer tasdig'i» degan tushuncha esa
Odoo savdo modulida umuman yo'q.

## Standartda nima urinib ko'rildi

**1. Sozlama bilan.** `account_use_credit_limit` yoqildi, 30 ta ulgurji
mijozga 35–250 mln so'mlik limit qo'yildi. Natija: buyurtma baribir
tasdiqlanaverdi, faqat lenta chiqdi. Talab bajarilmadi.

**2. Studio Approval Rules.** Studio'da `studio.approval.rule` bor va u
haqiqiy mexanizm: `_register_hook()` model metodini **server tomonda** patch
qiladi (`web_studio/models/studio_approval.py:383`), `domain` maydoni orqali
shartli ishlaydi, `approval_group_id` bilan kim tasdiqlashi belgilanadi.

Lekin ikkita to'siq bor:

- Domen **saqlanadigan** maydon talab qiladi. `res.partner.credit` esa
  `store=False`, va uning compute'ida (`account/models/partner.py:500` →
  `_credit_debit_get`) birorta maydonga bog'liqlik **yo'q** — faqat
  `@api.depends_context('company')`. Demak unga tayangan saqlanadigan maydon
  mijoz qarzi o'zgarganda hech qachon qayta hisoblanmaydi. Kecha limit ichida
  bo'lgan mijoz bugun undan oshib ketsa, lekin buyurtmaga hech kim tegmasa —
  bayroq eski qiymatda qolib, buyurtma bemalol o'tib ketadi. Aynan talab
  tekshiradigan joyda teshik.
- `self.env.su` bo'lsa Studio tasdiqni **butunlay o'tkazib yuboradi**
  (`studio_approval.py:403`).

**3. Shu modul.** Tekshiruv `action_confirm()` chaqirilgan **aniq daqiqada**
bajariladi. Saqlanadigan hisob maydoni yo'q — eskirish mumkin emas.

## Qanday ishlaydi

```
Sotuvchi «Tasdiqlash» bosadi
        │
        ├─ limit ichida ──────────────────► odatdagidek tasdiqlanadi
        │
        └─ limitdan oshadi
                 │
                 ├─ holat = «kutilmoqda»
                 ├─ chatterga hisob-kitob yoziladi
                 ├─ menejerlarga vazifa qo'yiladi
                 └─ ekranda sabab ko'rsatiladi (raqamlari bilan)
                          │
                          ├─ Menejer «Tasdiqlash» ──► buyurtma darhol o'tadi
                          └─ Menejer «Rad etish»  ──► izoh bilan yopiladi
```

Foydalanuvchi ko'radigan xabar:

```
«Shirin Savdo MCHJ» uchun kredit limiti oshib ketadi.

  Limit                       : 250 000 000 so'm
  Joriy qarz                  : 230 000 000 so'm
  Shu buyurtma                :  45 000 000 so'm
  ─────────────────────────────────────────────
  Tasdiqlangandan keyin       : 275 000 000 so'm
  LIMITDAN OSHADI             :  25 000 000 so'm
```

## Hisob-kitob

```
joriy qarz = partner.credit              # kitobga olingan debitorlik
           + partner.credit_to_invoice   # tasdiqlangan, hali faktura qilinmagan SO lar

buyurtma   = order.amount_total / order.currency_rate   # kompaniya valyutasiga
oshgan     = (joriy qarz + buyurtma) − credit_limit
```

- Joriy **qoralama** buyurtma `credit_to_invoice` ga kirmaydi (u faqat
  tasdiqlangan buyurtmalarni sanaydi), shuning uchun ikki marta hisoblanmaydi.
- `credit` va `credit_limit` buxgalteriya guruhlari bilan himoyalangan —
  sotuvchi ularni o'qiy olmaydi. Shuning uchun `sudo()` ishlatiladi; Odoo ning
  o'zi ham aynan shu sababdan shunday qiladi (`sale_order.py:786`).
- Tasdiqlash daqiqasida `credit` va `credit_to_invoice` **keshi tozalanadi**.
  Ularning compute'ida bog'liqlik yo'qligi sababli bitta so'rov ichida eskirgan
  qiymat qaytishi mumkin edi — sinov `test_03` aynan shuni tekshiradi.

## Huquqlar

Yangi guruh: **«Kredit limitidan oshishni tasdiqlash»**
(`crafers_kredit_limit.group_kredit_menejer`).
`sales_team.group_sale_manager` uni avtomatik oladi.

Sotuvchi tasdiqlashga urinsa `AccessError` chiqadi.

## Chetlab o'tish

`skip_kredit_tekshiruvi=True` konteksti bilan tekshiruv o'tkazib yuboriladi.
Faqat ma'lumot ko'chirish va avtomatik oqimlar uchun. Studio'dan farqli
o'laroq, `sudo` o'zi tekshiruvni **o'chirmaydi**.

## Sinovlar

10 ta test, `TransactionCase`:

```bash
python run_odoo.py -c odoo-crafers.conf -d crafers \
    -u crafers_kredit_limit --test-enable --stop-after-init
```

Oxirgi natija: `0 failed, 0 error(s) of 10 tests`.

| Test | Nimani tekshiradi |
|---|---|
| 01 | limit ichidagi buyurtma odatdagidek o'tadi |
| 02 | limitdan oshsa bloklanadi, vazifa qo'yiladi, sabab ko'rsatiladi |
| 03 | oldingi tasdiqlangan buyurtma ham qarzga qo'shiladi (kesh tuzog'i) |
| 04 | sotuvchi tasdiqlay/rad eta olmaydi |
| 05 | menejer tasdiqlagach buyurtma darhol o'tadi, vazifa yopiladi |
| 06 | rad etilgandan keyin ham o'tmaydi |
| 07 | tasdiq kutmayotgan buyurtmani tasdiqlash xato beradi |
| 08 | `skip_kredit_tekshiruvi` konteksti ishlaydi |
| 09 | limiti yo'q mijoz tekshirilmaydi |
| 10 | kompaniya sozlamasi o'chiq bo'lsa modul aralashmaydi |

## O'rnatish

```bash
python run_odoo.py -c odoo-crafers.conf -d crafers \
    -i crafers_kredit_limit --stop-after-init
```

Serverda: Ilovalar → ro'yxatni yangilash → «Crafers — kredit limiti va
menejer tasdig'i».

Talab: `sale` (Odoo 19).
