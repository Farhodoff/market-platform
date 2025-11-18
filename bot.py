from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)
import db
import os

# States
ASK_LANG, ASK_NAME, ASK_PHONE, ASK_ADDRESS = range(4)

# 🔗 WebApp URL
WEBAPP_URL = os.getenv("WEBAPP_URL") or "https://maydonuz.uz"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or "https://maydonuz.uz/webhook"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🌐 Til matnlari
MESSAGES = {
    "uz": {
        "start": "👋 Assalomu alaykum! Tilni tanlang:",
        "ask_name": "👋 Ismingizni yuboring:",
        "ask_phone": "📞 Telefon raqamingizni ulashish tugmasini bosing yoki yozib yuboring:",
        "ask_address": "📍 Manzilingizni yuboring (location tugmasini bosing yoki yozib yuboring):",
        "registered": "✅ Ro‘yxatdan o‘tish muvaffaqiyatli!",
        "shop_btn": "🛒 Do‘kon",
        "support_btn": "📞 Yordam",
        "cancel": "❌ Ro‘yxatdan o‘tish bekor qilindi.",
        "welcome": "Assalomu alaykum, {name}! 👋\nQuyidagi menyudan tanlang 👇",
        "support": "📞 Murojaat uchun: @Olma_operr"
    },
    "ru": {
        "start": "👋 Здравствуйте! Выберите язык:",
        "ask_name": "👋 Отправьте ваше имя:",
        "ask_phone": "📞 Отправьте ваш номер телефона или поделитесь контактом:",
        "ask_address": "📍 Отправьте ваш адрес (локацию или текстом):",
        "registered": "✅ Регистрация успешна!",
        "shop_btn": "🛒 Магазин",
        "support_btn": "📞 Поддержка",
        "cancel": "❌ Регистрация отменена.",
        "welcome": "Привет, {name}! 👋\nВыберите действие ниже 👇",
        "support": "📞 Для связи: @Olma_operr"
    }
}

# 🚀 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user_by_tg_id(update.effective_user.id)
    tg_id = update.effective_user.id

    if user:
        user = dict(user)
        lang = user.get("lang", "uz")

        shop_btn = KeyboardButton(
            MESSAGES[lang]["shop_btn"],
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?tg_id={tg_id}")
        )
        support_btn = KeyboardButton(MESSAGES[lang]["support_btn"])

        await update.message.reply_text(
            MESSAGES[lang]["welcome"].format(name=user["name"]),
            reply_markup=ReplyKeyboardMarkup([[shop_btn], [support_btn]], resize_keyboard=True)
        )
        return ConversationHandler.END

    # ❌ Agar ro‘yxatdan o‘tmagan bo‘lsa → til tanlash
    lang_buttons = [[KeyboardButton("🇺🇿 O‘zbekcha"), KeyboardButton("🇷🇺 Русский")]]
    await update.message.reply_text(
        MESSAGES["uz"]["start"],
        reply_markup=ReplyKeyboardMarkup(lang_buttons, resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_LANG

# 🚀 Tilni olish
async def ask_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = "ru" if "Рус" in text else "uz"
    context.user_data["lang"] = lang

    await update.message.reply_text(MESSAGES[lang]["ask_name"])
    return ASK_NAME

# 🚀 Ismni olish
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    lang = context.user_data["lang"]

    contact_btn = KeyboardButton(
        "📱 " + ("Поделиться номером" if lang == "ru" else "Telefonni ulashish"),
        request_contact=True
    )
    await update.message.reply_text(
        MESSAGES[lang]["ask_phone"],
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
    )
    return ASK_PHONE

# 🚀 Telefonni olish
async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data["phone"] = phone

    loc_btn = KeyboardButton(
        "📍 " + ("Отправить локацию" if lang == "ru" else "Manzilni ulashish"),
        request_location=True
    )
    await update.message.reply_text(
        MESSAGES[lang]["ask_address"],
        reply_markup=ReplyKeyboardMarkup([[loc_btn]], resize_keyboard=True)
    )
    return ASK_ADDRESS

# 🚀 Manzilni olish
async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        address = f"{lat}, {lon}"
    else:
        lat, lon, address = None, None, update.message.text

    tg_id = update.effective_user.id
    name = context.user_data.get("name")
    phone = context.user_data.get("phone")

    db.add_user(tg_id, name, phone=phone, address=address, lat=lat, lon=lon, lang=lang)

    shop_btn = KeyboardButton(
        MESSAGES[lang]["shop_btn"],
        web_app=WebAppInfo(url=f"{WEBAPP_URL}?tg_id={tg_id}")
    )
    support_btn = KeyboardButton(MESSAGES[lang]["support_btn"])

    await update.message.reply_text(
        MESSAGES[lang]["registered"],
        reply_markup=ReplyKeyboardMarkup([[shop_btn], [support_btn]], resize_keyboard=True)
    )
    return ConversationHandler.END

# 🚀 Yordam tugmasi
async def handle_support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user_by_tg_id(update.effective_user.id)
    lang = user["lang"] if user else "uz"
    await update.message.reply_text(MESSAGES[lang]["support"])

# 🚀 Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "uz")
    await update.message.reply_text(MESSAGES[lang]["cancel"])
    return ConversationHandler.END

# 🚀 Asosiy
def main():
    db.init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_lang)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, ask_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)
            ],
            ASK_ADDRESS: [
                MessageHandler(filters.LOCATION, ask_address),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv)
    application.add_handler(MessageHandler(filters.Regex("^📞"), handle_support_button))

    # 🔄 Polling yoki Webhook
    if os.getenv("USE_POLLING") == "1":
        application.run_polling()
    else:
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )

if __name__ == "__main__":
    main()
