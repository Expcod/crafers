# -*- coding: utf-8 -*-
# =====================================================================
#  TALAB #8 — Egaga har kuni ertalab Telegram digest
#
#  BU FAYL MODUL EMAS. Bu Odoo ning Scheduled Action (ir.cron) "Python
#  Code" maydoniga qo'yiladigan matn. Studio shart emas - ir.cron `base`
#  modulining qismi.
#  Repoda versiyalanishi va ko'rib chiqilishi uchun saqlanadi.
#
#  O'RNATISH
#  ---------
#  1. "Telegram Notification Center" (telegram_notification) ni o'rnating,
#     Settings da bot token va chat ID ni kiriting, "Enable" ni yoqing.
#  2. Settings -> Technical -> Automation -> Scheduled Actions -> New:
#         Nomi         : Telegram - egaga kunlik digest
#         Model        : Kompaniya (res.company)
#         Interval     : 1 kun
#         Keyingi ijro : ertaga 08:00 (Asia/Tashkent)
#     Kod maydoniga shu fayldagi kodni qo'ying.
#  3. Alohida parametr kerak emas: token va chat ID appning o'z
#     sozlamalaridan olinadi (tnc.telegram_bot_token / tnc.telegram_chat_id).
#     "Run Manually" bilan sinab ko'ring.
#
#  NEGA STUDIO YOLG'IZ YETMAYDI
#  -----------------------------
#  Server amallari `safe_eval` da ishlaydi. Uning konteksti (odoo/addons/
#  base/models/ir_actions.py:1109) faqat quyidagilarni beradi:
#      env, model, record, records, user, uid, time, datetime, dateutil,
#      timezone, float_compare, b64encode, b64decode, Command, UserError,
#      log, _logger
#  `requests` YO'Q, `import` YO'Q. Ya'ni Telegram API ga to'g'ridan-to'g'ri
#  HTTP so'rov yuborib bo'lmaydi.
#
#  YECHIM: transport tayyor moduldan olinadi. `env` mavjud bo'lgani uchun
#  Studio kodi o'rnatilgan modulning modelini bemalol chaqiradi.
#  Tavsiya etilgan: "Telegram Notification Center" (`telegram_notification`,
#  LGPL-3, bepul, Odoo 19) - apps.odoo.com/apps/modules/19.0/telegram_notification
#
#  Pastdagi YUBORISH bo'limida modul o'rnatilmagan bo'lsa kod yiqilmaydi:
#  matn jurnalga yoziladi va kompaniya chatteriga qo'yiladi, ya'ni hisob-
#  kitob qismini modulsiz ham sinash mumkin.
# =====================================================================

kecha = datetime.date.today() - datetime.timedelta(days=1)
boshi = datetime.datetime.combine(kecha, datetime.time.min)
oxiri = datetime.datetime.combine(kecha, datetime.time.max)
bugun = datetime.date.today()
kompaniya = env.company
valyuta = kompaniya.currency_id.symbol or kompaniya.currency_id.name


def pul(summa):
    """1 234 567 ko'rinishida.

    DIQQAT: `format()` safe_eval ning ruxsat etilgan built-in'lari ro'yxatida
    YO'Q (odoo/tools/safe_eval.py:309 dagi _BUILTINS ga qarang), shuning uchun
    ajratgich qo'lda qo'yiladi. `def` esa ruxsat etilgan (MAKE_FUNCTION
    _SAFE_OPCODES ichida).
    """
    matn = '%.0f' % (summa or 0.0)
    manfiy = matn[:1] == '-'
    if manfiy:
        matn = matn[1:]
    bolaklar = []
    while len(matn) > 3:
        bolaklar.insert(0, matn[-3:])
        matn = matn[:-3]
    bolaklar.insert(0, matn)
    return ('-' if manfiy else '') + ' '.join(bolaklar)


def esc(matn):
    """Telegram parse_mode=HTML uchun. Mijoz nomida `&` yoki `<` bo'lsa
    Telegram 400 qaytaradi va xabar jimgina chatterga tushib qoladi."""
    return (matn or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ------------------------------------------------------- 1. KECHAGI SOTUV
ulgurji = env['sale.order'].search([
    ('state', '=', 'sale'),
    ('date_order', '>=', boshi),
    ('date_order', '<=', oxiri),
    ('company_id', '=', kompaniya.id),
])
ulgurji_summa = sum(ulgurji.mapped('amount_total'))

pos_buyurtma = env['pos.order'].search([
    ('state', 'in', ['paid', 'done', 'invoiced']),
    ('date_order', '>=', boshi),
    ('date_order', '<=', oxiri),
    ('company_id', '=', kompaniya.id),
])
dokon_summa = sum(pos_buyurtma.mapped('amount_total'))

# do'kon kesimida
dokon_qatorlari = []
for cfg in env['pos.config'].search([('company_id', '=', kompaniya.id)]):
    buyurtmalar = pos_buyurtma.filtered(lambda p: p.config_id == cfg)
    if buyurtmalar:
        dokon_qatorlari.append('     %s — %s %s (%s chek)' % (
            esc(cfg.name), pul(sum(buyurtmalar.mapped('amount_total'))),
            valyuta, len(buyurtmalar)))

# ------------------------------------------------------------- 2. KASSA
naqd_tolovlar = env['pos.payment'].search([
    ('payment_date', '>=', boshi),
    ('payment_date', '<=', oxiri),
    ('payment_method_id.is_cash_count', '=', True),
    ('company_id', '=', kompaniya.id),
])
naqd_summa = sum(naqd_tolovlar.mapped('amount'))

karta_tolovlar = env['pos.payment'].search([
    ('payment_date', '>=', boshi),
    ('payment_date', '<=', oxiri),
    ('payment_method_id.is_cash_count', '=', False),
    ('company_id', '=', kompaniya.id),
])
karta_summa = sum(karta_tolovlar.mapped('amount'))

# kechagi yopilgan smenalarda sanoq farqi bo'lganmi
farqli_smenalar = []
for ses in env['pos.session'].search([
        ('state', '=', 'closed'),
        ('stop_at', '>=', boshi),
        ('stop_at', '<=', oxiri)]):
    farq = (ses.cash_register_balance_end_real or 0.0) - (ses.cash_register_balance_end or 0.0)
    if abs(farq) > 0.01:
        farqli_smenalar.append('     %s — farq %s %s' % (
            esc(ses.config_id.name), pul(farq), valyuta))

# ------------------------------------------- 3. MUDDATI O'TGAN QARZLAR
kechikkan = env['account.move.line'].search([
    ('account_id.account_type', '=', 'asset_receivable'),
    ('parent_state', '=', 'posted'),
    ('full_reconcile_id', '=', False),
    ('date_maturity', '<', bugun),
    ('company_id', '=', kompaniya.id),
])
qarz_summa = sum(kechikkan.mapped('amount_residual'))

# eng katta 5 ta qarzdor
qarz_kesim = {}
for qator in kechikkan:
    nom = esc(qator.partner_id.display_name) or '—'
    qarz_kesim[nom] = qarz_kesim.get(nom, 0.0) + qator.amount_residual
eng_kattalar = sorted(qarz_kesim.items(), key=lambda x: -x[1])[:5]

# ------------------------------------------------------------ 4. MATN
qatorlar = [
    '<b>CRAFERS — %s kuni</b>' % kecha.strftime('%d.%m.%Y'),
    '',
    '<b>SOTUV: %s %s</b>' % (pul(ulgurji_summa + dokon_summa), valyuta),
    '  Ulgurji: %s %s (%s buyurtma)' % (pul(ulgurji_summa), valyuta, len(ulgurji)),
    "  Do'konlar: %s %s (%s chek)" % (pul(dokon_summa), valyuta, len(pos_buyurtma)),
]
qatorlar += dokon_qatorlari
qatorlar += [
    '',
    '<b>KASSA</b>',
    '  Naqd: %s %s' % (pul(naqd_summa), valyuta),
    '  Karta: %s %s' % (pul(karta_summa), valyuta),
]
if farqli_smenalar:
    qatorlar.append('  <b>Sanoq farqi bor:</b>')
    qatorlar += farqli_smenalar
else:
    qatorlar.append('  Sanoq farqi yo\'q')

qatorlar += [
    '',
    "<b>MUDDATI O'TGAN QARZLAR: %s %s</b>" % (pul(qarz_summa), valyuta),
]
if eng_kattalar:
    for nom, summa in eng_kattalar:
        qatorlar.append('  %s — %s %s' % (nom, pul(summa), valyuta))
else:
    qatorlar.append('  Muddati o\'tgan qarz yo\'q')

matn = '\n'.join(qatorlar)

# --------------------------------------------------------- 5. YUBORISH
# Transport: "Telegram Notification Center" (telegram_notification).
# Uning manbasidan (models/telegram_mixin.py) aniqlangan API:
#     env['telegram.notification.mixin']._telegram_send(message) -> bool
# Token va chat ID ni o'zi oladi: Settings dagi tnc.telegram_bot_token /
# tnc.telegram_chat_id / tnc.telegram_enabled. parse_mode = HTML.
#
# `_` bilan boshlanishi muammo emas: safe_eval faqat `__` li nomlarni
# bloklaydi (odoo/tools/safe_eval.py:210). Appning o'z cron'lari ham
# xuddi shunday `model._cron_notify_...()` ni chaqiradi.
#
# Appning O'Z hodisa xabarlari (SO/PO tasdiqlandi, faktura to'landi, lead
# biriktirildi, cron ogohlantirishlari) o'chirilgan: Settings dagi
# "Enable Telegram Notifications" (tnc.telegram_enabled) o'chiq. Lekin
# _telegram_send aynan shu bayroqni tekshiradi. Shuning uchun digest uni
# FAQAT o'z tranzaksiyasi ichida vaqtincha yoqadi va darhol qaytaradi: commit
# paytida qiymat o'zgarmagan bo'ladi, boshqa jarayonlar "yoqiq" holatni
# ko'rmaydi. _telegram_send barcha xatolarni o'zi ushlaydi (False qaytaradi),
# shuning uchun try/finally shart emas; boshqa xato bo'lsa butun tranzaksiya
# rollback bo'ladi va bayroq baribir o'zgarmay qoladi.
yuborildi = False
if 'telegram.notification.mixin' in env:
    icp = env['ir.config_parameter'].sudo()
    oldingi = icp.get_param('tnc.telegram_enabled')
    icp.set_param('tnc.telegram_enabled', 'True')
    yuborildi = env['telegram.notification.mixin']._telegram_send(matn)
    icp.set_param('tnc.telegram_enabled', oldingi or False)
    log('Telegram digest yuborildi: %s' % yuborildi, level='info')

if not yuborildi:
    # Transport hali yo'q: matn jurnalga va kompaniya chatteriga tushadi,
    # shunda hisob-kitob qismini modulsiz ham tekshirish mumkin.
    # Chatter HTML ni eskeyp qilgani uchun bu yerda teglarsiz variant.
    sof = matn.replace('<b>', '').replace('</b>', '')
    log("Telegram digest (transport yo'q):\n%s" % sof, level='info')
    kompaniya.message_post(
        body=sof.replace('\n', '<br/>'),
        subject='Kunlik digest — %s' % kecha.strftime('%d.%m.%Y'))
