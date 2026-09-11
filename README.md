# crafers

**Crafers** qandolat fabrikasi uchun Odoo 19 Enterprise custom modullari.

Bu repoda faqat **kod bilan yechilgan** ikkita talab va bitta Studio skripti
bor. Sozlash bilan yechilgan talablar (xarid, ishlab chiqarish, muddat/FEFO,
POS, qaytarish, hisobotlar) kod talab qilmagani uchun bu yerda emas.

## Modullar

### `crafers_kredit_limit` — kredit limiti va menejer tasdig'i

Ulgurji mijoz kredit limitidan oshsa sotuv buyurtmasi tasdiqlanmaydi,
menejer tasdig'iga yuboriladi.

Standart Odoo limitdan oshganda faqat **ogohlantirish matnini** ko'rsatadi
(`sale/models/sale_order.py:778`) va tasdiqlashni to'xtatmaydi. Studio
Approval Rules saqlanadigan maydon talab qiladi, `res.partner.credit` esa
`store=False` va compute'ida bog'liqlik yo'q — bayroq eskiradi. Shu modul
tekshiruvni `action_confirm()` chaqirilgan aniq daqiqada bajaradi.

Batafsil: [crafers_kredit_limit/README.md](crafers_kredit_limit/README.md)

### `crafers_ishbay_haq` — sex ishchilarining ishbay haqi

Ish buyrug'ida ishlab chiqarilgan miqdorni xodimlar o'rtasida vaqt ulushiga
qarab bo'lib, operatsiyaning dona narxiga ko'paytiradi.

Shop Floor xodimning **soat**ini yozadi, `qty_produced` esa **dona**ni biladi
— ikkisini bog'lash standartda yo'q. `hr_payroll` bor, lekin
`l10n_uz_hr_payroll` yo'q va payroll ishbayni o'zi hisoblamaydi.

Batafsil: [crafers_ishbay_haq/README.md](crafers_ishbay_haq/README.md)

### `studio/telegram_kunlik_digest.py` — kunlik Telegram digest

Modul emas: Odoo Studio ning **rejalashtirilgan amali** uchun kod. Har kuni
ertalab egaga kechagi sotuv, kassa va muddati o'tgan qarzlarni yuboradi.

Studio yolg'iz yetmaydi — `safe_eval` da `requests` ham, `import` ham yo'q.
Transport tayyor moduldan olinadi (Telegram Notification Center, LGPL-3).
Fayl boshida to'liq o'rnatish yo'riqnomasi bor.

## O'rnatish

```bash
git clone https://github.com/Expcod/crafers.git
# addons_path ga shu papkani qo'shing, keyin:
odoo -c <conf> -d <baza> -i crafers_kredit_limit,crafers_ishbay_haq --stop-after-init
```

Yoki Odoo interfeysida: Ilovalar → ro'yxatni yangilash → modul nomini qidiring.

## Sinovlar

```bash
odoo -c <conf> -d <baza> \
     -u crafers_kredit_limit,crafers_ishbay_haq \
     --test-enable --stop-after-init
```

| Modul | Testlar | Natija |
|---|---|---|
| `crafers_kredit_limit` | 10 | `0 failed, 0 error(s)` |
| `crafers_ishbay_haq` | 8 | `0 failed, 0 error(s)` |

## Talab

Odoo **19.0 Enterprise**. `crafers_ishbay_haq` Shop Floor ga tayanadi
(`mrp_workorder`, `mrp_workorder_hr_account`).

## Litsenziya

LGPL-3
