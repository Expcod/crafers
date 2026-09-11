# crafers

**Crafers** qandolat fabrikasi uchun Odoo 19 Enterprise custom modullari.


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

Modul emas: Odoo **Scheduled Action** (`ir.cron`) ning *Python Code*
maydoni uchun kod. Studio shart emas. Har kuni ertalab egaga kechagi sotuv,
kassa va muddati o'tgan qarzlarni yuboradi.

Server kodi `safe_eval` da ishlaydi — unda `requests` ham, `import` ham yo'q.
Shuning uchun transport tayyor moduldan olinadi: **Telegram Notification
Center** (`telegram_notification`, LGPL-3). Uning manbasidan aniqlangan API:

```python
env['telegram.notification.mixin']._telegram_send(message)  # -> bool
```

Token va chat ID appning Settings'idan olinadi. `_` bilan boshlanishi
muammo emas: `safe_eval` faqat `__` li nomlarni bloklaydi.

Fayl boshida to'liq o'rnatish yo'riqnomasi bor.

