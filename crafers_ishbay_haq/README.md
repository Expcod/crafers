# crafers_ishbay_haq

**Talab #7:** «Sex ishchilari ishlab chiqargan miqdorga qarab haq oladi
(dona uchun narx).»

## Nima uchun kod kerak bo'ldi

Standartda **ma'lumot bor, hisob yo'q**:

| Manba | Nima beradi | Nima yetmaydi |
|---|---|---|
| `mrp.workcenter.productivity` (Shop Floor) | xodimning ish buyrug'iga sarflagan **vaqti** | soat, dona emas |
| `mrp.workorder.qty_produced` | ishlab chiqarilgan **dona** | xodimlar o'rtasida taqsimlanmaydi |
| `hr_payroll` (Enterprise) | ish haqi hujjati | `l10n_uz_hr_payroll` **yo'q**; ishbayni o'zi hisoblamaydi |

**Studioda urinib ko'rildi:** `mrp.workorder` ga hisoblanadigan maydon qo'shib,
keyin xodim kesimida yig'ish. Bir necha model bo'ylab agregatsiya va davrga
bo'lish kerak bo'lgani uchun mo'rt chiqadi.

## Mantiq

```
xodim_dona = wo.qty_produced × (xodimning shu WO dagi vaqti / WO ning BUTUN vaqti)
xodim_summa = xodim_dona × operatsiyaning ishbay_narx i
```

Ulush **maxraji** — ish buyrug'ining butun vaqti (davrdan tashqarisi ham),
**surati** — faqat hisob davridagi vaqt. Shunda ish buyrug'i ikki oyga
cho'zilsa ham miqdor ikki marta berilmaydi (`test_03` shuni qo'riqlaydi).

## Dona narxi qayerda

`mrp.routing.workcenter.ishbay_narx` — ya'ni **retseptning har bir
operatsiyasida alohida**. Qadoqlash 120 so'm/dona, qoliplash 200 so'm/dona
bo'lishi mumkin. 0 bo'lsa operatsiya ishbay haqqa kirmaydi (texnolog nazorati
kabi).

## Foydalanish

1. Retseptda (BoM) har operatsiyaga dona narxini qo'ying.
2. Ishchilar Shop Floor da ish buyrug'ini **o'z nomidan** boshlab-to'xtatsin —
   busiz vaqt yozilmaydi va hisob bo'sh chiqadi.
3. Ishlab chiqarish → **Ishbay haq** → yangi hujjat, davrni tanlang →
   **Hisoblash** → **To'lovga tasdiqlash**.
4. Ishlab chiqarish → Hisobot → **Ishbay haq tahlili** — xodim/mahsulot
   kesimidagi pivot.

Modul `hr_payroll` ga **bog'lanmaydi**: natija alohida hujjat. Oylikka qo'lda
yoki keyingi bosqichda avtomatik kiritiladi.

## Sinovlar

```bash
python run_odoo.py -c odoo-crafers.conf -d crafers \
    -u crafers_ishbay_haq --test-enable --stop-after-init
```

Natija: `0 failed, 0 error(s) of 8 tests`.

| Test | Nimani tekshiradi |
|---|---|
| 01 | 100 dona, Ali 60 daq / Vali 20 daq → 75/25 dona, 15 000/5 000 so'm |
| 02 | bitta xodim ishlasa hammasini oladi |
| 03 | ish buyrug'i ikki davrga cho'zilsa miqdor ikkilanmaydi |
| 04 | narxsiz operatsiya hisobga kirmaydi va sabab yoziladi |
| 05 | vaqt yozilmagan bo'lsa ogohlantiradi |
| 06 | qayta hisoblash qatorlarni takrorlamaydi |
| 07 | tasdiqlangach qayta hisoblab bo'lmaydi |
| 08 | ketma-ketlikdan raqam beriladi (ISHBAY/2026/0001) |
