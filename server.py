from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory, abort, g
import sqlite3, os, requests, uuid, hmac, hashlib, urllib.parse, json
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime
import pytz
from dotenv import load_dotenv
from bot_notify import notify_admin
import db
from flask_babel import Babel, gettext as _
from db import get_all_orders_with_items, get_orders_by_user

load_dotenv()

app = Flask(__name__)

# 📂 Fayllar joylashuvi
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")   # foydalanuvchi chek
app.config["PRODUCT_FOLDER"] = os.path.join("static", "products")    # mahsulot rasmlari
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PRODUCT_FOLDER"], exist_ok=True)
app.config["BABEL_DEFAULT_LOCALE"] = "uz"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"

# Ruxsat etilgan fayl turlari
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# 🔑 Session uchun secret key (.env dan)
app.secret_key = os.getenv("SECRET_KEY", "market_platform_secret_2026_dev")

# 🔐 Admin login (.env dan)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", os.getenv("ADMIN_PASS", "220286"))

def check_admin_credentials(username, password):
    if username != ADMIN_USERNAME:
        return False
    if ADMIN_PASSWORD.startswith("pbkdf2:") or ADMIN_PASSWORD.startswith("scrypt:"):
        return check_password_hash(ADMIN_PASSWORD, password)
    return password == ADMIN_PASSWORD

# 🤖 Telegram bot sozlamalari (.env dan)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def verify_telegram_init_data(init_data: str) -> dict:
    """
    Telegram WebApp initData ni HMAC-SHA256 orqali tekshirish.
    Muvaffaqiyatli bo'lsa foydalanuvchi ma'lumotlari lug'atini, aks holda None qaytaradi.
    """
    if not init_data or not BOT_TOKEN:
        return None
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        hash_val = parsed_data.pop("hash", None)
        if not hash_val:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash == hash_val:
            user_json = parsed_data.get("user")
            if user_json:
                return json.loads(user_json)
            return parsed_data
        return None
    except Exception as e:
        print("initData tekshirishda xatolik:", e)
        return None

# 💳 To'lov karta sozlamalari (.env dan)
PAY_CARD_NUMBER = os.getenv("PAY_CARD_NUMBER", "9860 1201 4178 3197")
PAY_CARD_OWNER = os.getenv("PAY_CARD_OWNER", "Zuhriddin Yuldoshev")

# =====================
# 🔗 DB ulanish
# =====================
def get_db_connection():
    return db.get_connection()

# =====================
# 🌍 Babel (Flask-Babel v4) sozlamalari
# =====================
def select_locale():
    if "lang" in session:
        return session["lang"]

    tg_id = session.get("tg_id")
    if tg_id:
        conn = get_db_connection()
        user = conn.execute("SELECT lang FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        conn.close()
        if user and user["lang"]:
            return user["lang"]

    return request.accept_languages.best_match(["uz", "ru"]) or "uz"

babel = Babel(app, locale_selector=select_locale)

# ⚠️ MUHIM: before_request tartibi — avval tg_id, keyin locale
@app.before_request
def capture_tg_id():
    tg_id = request.args.get("tg_id")
    if tg_id:
        session["tg_id"] = str(tg_id)
    elif not session.get("tg_id") and (app.debug or request.host.startswith("localhost") or request.host.startswith("127.0.0.1")):
        default_tg_id = os.getenv("ADMIN_CHAT_ID", "6756073816")
        if default_tg_id:
            session["tg_id"] = str(default_tg_id)

@app.before_request
def set_global_locale():
    # templatelarda {{ g.locale }} deb foydalaning (funksiya emas, string!)
    g.locale = select_locale()

# (ixtiyoriy) templatelarga joriy til nomini qulay uzatish
@app.context_processor
def inject_current_lang():
    return {"current_lang": getattr(g, "locale", "uz")}

# =====================
# 🌍 Tilni o‘zgartirish
# =====================

# 1) Faqat sessiya uchun
@app.route("/set_lang/<lang>")
def set_language_session(lang):
    if lang not in ["uz", "ru"]:
        lang = "uz"
    session["lang"] = lang
    return redirect(request.referrer or url_for("index"))

# 2) Sessiya + foydalanuvchi DB dagi lang ni yangilash
@app.route("/set_language/<lang>")
def set_language_route(lang):
    if lang not in ["uz", "ru"]:
        return "❌ Til qo‘llab-quvvatlanmaydi", 400

    session["lang"] = lang
    tg_id = session.get("tg_id")
    if tg_id:
        conn = get_db_connection()
        conn.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, tg_id))
        conn.commit()
        conn.close()

    return redirect(request.referrer or url_for("index"))

# 🔐 Telegram WebApp initData orqali xavfsiz avtorizatsiya API
@app.route("/api/auth_telegram", methods=["POST"])
def auth_telegram():
    data = request.get_json() or {}
    init_data = data.get("initData")
    if not init_data:
        return jsonify({"status": "error", "message": "initData talab qilinadi"}), 400

    user_info = verify_telegram_init_data(init_data)
    if not user_info:
        return jsonify({"status": "error", "message": "Telegram imzosi haqiqiy emas"}), 403

    tg_id = str(user_info.get("id"))
    session["tg_id"] = tg_id
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or "Telegram Foydalanuvchi"
    user = db.get_user_by_tg_id(tg_id)
    if not user:
        db.add_user(tg_id, full_name, lang=user_info.get("language_code", "uz"))
    return jsonify({"status": "success", "tg_id": tg_id, "user": user_info})

# =====================
# 🔒 Admin login decorator
# =====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_logged_in" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# =====================
# 🏠 Foydalanuvchi sahifalari
# =====================
@app.route("/")
def index():
    conn = get_db_connection()
    categories = conn.execute("SELECT id, name_uz, name_ru FROM categories ORDER BY id ASC").fetchall()
    conn.close()

    # Foydalanuvchining tilini olish (agar login bo'lmagan bo'lsa default 'uz')
    tg_id = request.args.get("tg_id")
    user = None
    if tg_id:
        user = db.get_user_by_tg_id(tg_id)

    lang = user["lang"] if user and "lang" in user.keys() else "uz"

    # Tilga qarab to‘g‘ri nomni tanlash
    result = []
    for c in categories:
        name = c["name_uz"] if lang == "uz" else (c["name_ru"] or c["name_uz"])
        result.append({"id": c["id"], "name": name})

    return render_template("index.html", categories=result)

@app.route("/products/<int:category_id>")
def products(category_id):
    conn = get_db_connection()
    products_rows = conn.execute(
        "SELECT id, name, price, image, COALESCE(stock, 100) as stock, COALESCE(is_available, 1) as is_available FROM products WHERE category_id = ?",
        (category_id,)
    ).fetchall()
    category = conn.execute("SELECT id, name_uz, name_ru FROM categories WHERE id = ?", (category_id,)).fetchone()
    conn.close()
    return render_template("products.html", products=products_rows, category=category)

# 🛒 Savatchaga qo‘shish (AJAX)
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    data = request.get_json() or {}
    product_name = data.get("name")
    price = int(data.get("price", 0))

    if not product_name or price <= 0:
        return jsonify({"status": "error", "message": "Noto‘g‘ri mahsulot ma’lumoti"}), 400

    # Ombor qoldig'ini tekshirish
    conn = get_db_connection()
    prod = conn.execute(
        "SELECT stock, is_available FROM products WHERE name = ?", (product_name,)
    ).fetchone()
    conn.close()

    if prod and (prod["is_available"] == 0 or (prod["stock"] is not None and prod["stock"] <= 0)):
        return jsonify({"status": "error", "message": "Kechirasiz, ushbu mahsulot hozirda tugagan!"}), 400

    cart = session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            if prod and prod["stock"] is not None and item["quantity"] >= prod["stock"]:
                return jsonify({"status": "error", "message": f"Omborda faqat {prod['stock']} ta mahsulot mavjud!"}), 400
            item["quantity"] += 1
            break
    else:
        cart.append({"name": product_name, "price": price, "quantity": 1})

    session["cart"] = cart
    session.modified = True
    return jsonify({
        "status": "success",
        "message": f"{product_name} savatchaga qo‘shildi!",
        "items_count": sum(item["quantity"] for item in cart)
    })

# 🛒 Savatcha
@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    products_total = sum(item["price"] * item["quantity"] for item in cart)
    delivery_fee = 10000
    total = products_total + delivery_fee
    return render_template(
        "cart.html",
        cart=cart,
        products_total=products_total,
        delivery_fee=delivery_fee,
        total=total
    )

# 🔁 Miqdorni o‘zgartirish (➕/➖)
@app.route("/update_cart", methods=["POST"])
def update_cart():
    data = request.get_json() or {}
    name = data.get("name")
    change = int(data.get("change", 0))

    cart = session.get("cart", [])
    for item in cart:
        if item["name"] == name:
            item["quantity"] += change
            if item["quantity"] <= 0:
                cart.remove(item)
            break

    session["cart"] = cart
    session.modified = True
    products_total = sum(item["price"] * item["quantity"] for item in cart)
    delivery_fee = 10000 if cart else 0
    total = products_total + delivery_fee
    return jsonify({
        "status": "success",
        "cart": cart,
        "products_total": products_total,
        "delivery_fee": delivery_fee,
        "total": total,
        "items_count": sum(item["quantity"] for item in cart)
    })

# ❌ Savatchadan o‘chirish
@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    data = request.get_json() or {}
    product_name = data.get("name")
    cart = session.get("cart", [])
    cart = [item for item in cart if item["name"] != product_name]
    session["cart"] = cart
    session.modified = True
    products_total = sum(item["price"] * item["quantity"] for item in cart)
    delivery_fee = 10000 if cart else 0
    total = products_total + delivery_fee
    return jsonify({
        "status": "success",
        "message": f"{product_name} savatchadan olib tashlandi!",
        "cart": cart,
        "products_total": products_total,
        "delivery_fee": delivery_fee,
        "total": total,
        "items_count": sum(item["quantity"] for item in cart)
    })

# ✅ Buyurtma berish
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    tg_id = session.get("tg_id") or request.args.get("tg_id")
    if not tg_id and (app.debug or request.host.startswith("localhost") or request.host.startswith("127.0.0.1")):
        tg_id = os.getenv("ADMIN_CHAT_ID", "6756073816")
        if tg_id:
            session["tg_id"] = str(tg_id)

    cart = session.get("cart", [])
    if not cart:
        return redirect(url_for("cart"))

    products_total = sum(item["price"] * item["quantity"] for item in cart)
    delivery_fee = 10000
    total_price = products_total + delivery_fee

    if not tg_id:
        return render_template(
            "cart.html",
            cart=cart,
            products_total=products_total,
            delivery_fee=delivery_fee,
            total=total_price,
            error=_("⚠️ Buyurtma berish uchun avval Telegram botimizda ro‘yxatdan o‘tishingiz kerak!")
        )

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    if not user and (app.debug or request.host.startswith("localhost") or request.host.startswith("127.0.0.1")):
        # Lokal testda agar user topilmasa, test user yaratib olamiz
        db.add_user(tg_id, "Test Foydalanuvchi", phone="+998901234567", address="Toshkent shahri", lang="uz")
        user = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()

    if not user:
        conn.close()
        return render_template(
            "cart.html",
            cart=cart,
            products_total=products_total,
            delivery_fee=delivery_fee,
            total=total_price,
            error=_("⚠️ Foydalanuvchi ma'lumotlari topilmadi. Iltimos, Telegram botimizda /start bosing!")
        )

    if request.method == "POST":
        delivery_phone = request.form.get("phone", "").strip() or (user["phone"] if user else "")
        delivery_address = request.form.get("address", "").strip() or (user["address"] if user else "")

        if not delivery_phone or not delivery_address:
            conn.close()
            return render_template(
                "checkout.html",
                user=user,
                total=total_price,
                card_number=PAY_CARD_NUMBER,
                card_owner=PAY_CARD_OWNER,
                error=_("❌ Telefon raqami va yetkazib berish manzilini kiritish majburiy!")
            ), 400

        if products_total < 100000:
            conn.close()
            return render_template(
                "checkout.html",
                user=user,
                total=total_price,
                card_number=PAY_CARD_NUMBER,
                card_owner=PAY_CARD_OWNER,
                error=_("❌ Minimal buyurtma summasi 100 000 so‘m bo‘lishi kerak!")
            ), 400

        receipt_file = request.files.get("receipt")
        if not receipt_file or not receipt_file.filename:
            conn.close()
            return render_template(
                "checkout.html",
                user=user,
                total=total_price,
                card_number=PAY_CARD_NUMBER,
                card_owner=PAY_CARD_OWNER,
                error=_("❌ To‘lov chekini yuklash majburiy!")
            ), 400

        if not allowed_file(receipt_file.filename):
            conn.close()
            return render_template(
                "checkout.html",
                user=user,
                total=total_price,
                card_number=PAY_CARD_NUMBER,
                card_owner=PAY_CARD_OWNER,
                error=_("❌ Chek faqat rasm formatida bo‘lishi kerak (.jpg, .png, .webp)!")
            ), 400

        # Foydalanuvchi profilini yangilash (agar belgilangan bo'lsa)
        if request.form.get("save_address"):
            conn.execute("UPDATE users SET phone=?, address=? WHERE tg_id=?", (delivery_phone, delivery_address, tg_id))
            conn.commit()

        ext = receipt_file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"receipt_{uuid.uuid4().hex[:12]}.{ext}"
        receipt_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        receipt_file.save(receipt_path)

        # 1️⃣ Orders jadvaliga yozamiz
        order_id = db.add_order(
            tg_id=tg_id,
            name=user["name"],
            phone=delivery_phone,
            address=delivery_address,
            total_price=total_price,
            receipt=unique_filename,
            status="Kutilmoqda"
        )

        # 2️⃣ Har bir mahsulotni order_items ga yozamiz
        cur = conn.cursor()
        for item in cart:
            cur.execute("""
                INSERT INTO order_items (order_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, item["name"], item["quantity"], item["price"]))
        conn.commit()
        conn.close()

        # 🔔 Telegramga xabar (foydalanuvchi tiliga qarab)
        lang = user["lang"] if user and "lang" in user.keys() else "uz"

        if lang == "ru":
            message = (
                f"🛒 Уважаемый {user['name']}, ваш заказ принят!\n\n"
                f"📦 Общая сумма: {total_price} сум\n"
                f"📍 Адрес доставки: {delivery_address}\n"
                f"📞 Телефон: {delivery_phone}"
            )
        else:
            message = (
                f"🛒 Hurmatli {user['name']}, buyurtmangiz qabul qilindi!\n\n"
                f"📦 Jami summa: {total_price} so‘m\n"
                f"📍 Yetkazish manzili: {delivery_address}\n"
                f"📞 Telefon: {delivery_phone}"
            )

        try:
            requests.post(TELEGRAM_API, data={"chat_id": tg_id, "text": message}, timeout=5)
        except Exception as e:
            print("❌ Qabul xabari yuborilmadi:", e)

        # 📣 Adminlarga bildirishnoma yuborish
        order_info = {
            "id": order_id,
            "name": user["name"],
            "phone": delivery_phone,
            "address": delivery_address,
            "total_price": total_price,
            "status": "Kutilmoqda"
        }
        try:
            notify_admin(order_info, items=cart, receipt_path=receipt_path)
        except Exception as ex_admin:
            print("❌ Admin bildirishnomasida xatolik:", ex_admin)

        session.pop("cart", None)
        return redirect(url_for("orders"))

    conn.close()
    return render_template(
        "checkout.html",
        user=user,
        total=total_price,
        card_number=PAY_CARD_NUMBER,
        card_owner=PAY_CARD_OWNER
    )

# 📝 Buyurtmalar (faqat shu foydalanuvchiga)
@app.route("/orders")
def orders():
    tg_id = request.args.get("tg_id") or session.get("tg_id")
    if not tg_id and (app.debug or request.host.startswith("localhost") or request.host.startswith("127.0.0.1")):
        tg_id = os.getenv("ADMIN_CHAT_ID", "6756073816")
        if tg_id:
            session["tg_id"] = str(tg_id)

    if not tg_id:
        return redirect(url_for("index"))

    # 🔗 DB dan buyurtmalarni items bilan olish
    orders = get_orders_by_user(tg_id)

    return render_template("orders.html", orders=orders)
# =====================
# 🔑 Admin login/logout
# =====================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if check_admin_credentials(username, password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin/login.html", error=_("❌ Login yoki parol noto‘g‘ri"))
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# =====================
# ⚙️ Admin Panel
# =====================
@app.route("/admin")
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    conn = get_db_connection()

    # 1. Bugungi sana (Toshkent vaqti)
    tz = pytz.timezone("Asia/Tashkent")
    today_str = datetime.now(tz).strftime("%Y-%m-%d")

    # Bugungi buyurtmalar va tushum
    today_stat = conn.execute("""
        SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as total
        FROM orders
        WHERE created_at LIKE ? AND status != 'Bekor qilindi'
    """, (today_str + "%",)).fetchone()

    # Jami buyurtmalar va tushum
    all_stat = conn.execute("""
        SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as total
        FROM orders
        WHERE status != 'Bekor qilindi'
    """).fetchone()

    # Kutilayotgan buyurtmalar
    pending_stat = conn.execute("""
        SELECT COUNT(*) as count FROM orders WHERE status = 'Kutilmoqda'
    """).fetchone()

    # Jami mijozlar soni
    users_stat = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()

    # Jami mahsulotlar soni
    products_stat = conn.execute("SELECT COUNT(*) as count FROM products").fetchone()

    # Eng ko'p sotilgan mahsulotlar (Top 5)
    top_products = conn.execute("""
        SELECT product_name, SUM(quantity) as total_qty, SUM(quantity * price) as total_revenue
        FROM order_items
        GROUP BY product_name
        ORDER BY total_qty DESC
        LIMIT 5
    """).fetchall()

    # Oxirgi 5 ta buyurtma
    recent_orders = conn.execute("""
        SELECT id, name, phone, total_price, status, created_at
        FROM orders
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        today_stat=today_stat,
        all_stat=all_stat,
        pending_stat=pending_stat,
        users_count=users_stat["count"] if users_stat else 0,
        products_count=products_stat["count"] if products_stat else 0,
        top_products=top_products,
        recent_orders=recent_orders
    )

# 📂 Admin: buyurtmalar
@app.route("/admin/orders")
@login_required
def admin_orders():
    conn = get_db_connection()
    orders = conn.execute("""
        SELECT o.*,
               u.address AS user_address,
               u.lat AS user_lat,
               u.lon AS user_lon
        FROM orders o
        LEFT JOIN users u ON o.tg_id = u.tg_id
        ORDER BY o.id DESC
    """).fetchall()

    result = []
    for o in orders:
        # 🔗 order_items dan mahsulotlarni olish
        items = conn.execute(
            "SELECT product_name, quantity, price FROM order_items WHERE order_id=?",
            (o["id"],)
        ).fetchall()

        result.append({
            **dict(o),
            "items": [dict(i) for i in items]   # items qo‘shildi
        })

    conn.close()

    # 🕒 Sanani Toshkent vaqtiga o‘tkazish
    tz = pytz.timezone("Asia/Tashkent")
    for o in result:
        if o["created_at"]:
            try:
                dt = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
                o["created_at"] = dt.replace(tzinfo=pytz.UTC).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

    return render_template("admin/orders.html", orders=result)

@app.route("/admin/orders/update/<int:order_id>/<string:new_status>")
@login_required
def admin_update_order(order_id, new_status):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        conn.close()
        abort(404)

    conn.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()

    # Foydalanuvchining tilini olish
    user = conn.execute("SELECT lang FROM users WHERE tg_id=?", (order["tg_id"],)).fetchone()
    conn.close()

    lang = user["lang"] if user and "lang" in user.keys() else "uz"

    # Til bo‘yicha xabarlar
    MESSAGES = {
        "uz": {
            "approved": (
                f"✅ Hurmatli {order['name']}, #{order['id']} raqamli buyurtmangiz tasdiqlandi!\n\n"
                f"🚚 Tez orada yetkazib beriladi.\n"
                f"📦 Jami summa: {int(order['total_price']):,} so‘m".replace(",", " ")
            ),
            "delivered": (
                f"🚚 Hurmatli {order['name']}, #{order['id']} raqamli buyurtmangiz muvaffaqiyatli yetkazib berildi!\n\n"
                f"Xaridingiz uchun rahmat! 😊"
            ),
            "cancelled": (
                f"❌ Hurmatli {order['name']}, afsuski #{order['id']} raqamli buyurtmangiz bekor qilindi.\n\n"
                f"Savollaringiz bo‘lsa qo‘llab-quvvatlash xizmatiga murojaat qilishingiz mumkin."
            )
        },
        "ru": {
            "approved": (
                f"✅ Уважаемый {order['name']}, ваш заказ #{order['id']} подтвержден!\n\n"
                f"🚚 Скоро будет доставлен.\n"
                f"📦 Общая сумма: {int(order['total_price']):,} сум".replace(",", " ")
            ),
            "delivered": (
                f"🚚 Уважаемый {order['name']}, ваш заказ #{order['id']} успешно доставлен!\n\n"
                f"Спасибо за покупку! 😊"
            ),
            "cancelled": (
                f"❌ Уважаемый {order['name']}, к сожалению, ваш заказ #{order['id']} был отменен.\n\n"
                f"По всем вопросам обращайтесь в службу поддержки."
            )
        }
    }

    message = None
    lang_msgs = MESSAGES.get(lang, MESSAGES["uz"])
    if new_status == "Tasdiqlandi":
        message = lang_msgs["approved"]
    elif new_status == "Bajarildi":
        message = lang_msgs["delivered"]
    elif new_status == "Bekor qilindi":
        message = lang_msgs["cancelled"]

    if message and order["tg_id"]:
        try:
            requests.post(TELEGRAM_API, data={"chat_id": order["tg_id"], "text": message}, timeout=5)
        except Exception as e:
            print(f"❌ {new_status} xabari yuborilmadi:", e)

    redirect_target = request.args.get("next") or url_for("admin_orders")
    return redirect(redirect_target)

# 📂 Admin: chek ko‘rish
@app.route("/admin/receipt/<path:filename>")
@login_required
def admin_receipt(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# 📂 Admin: kategoriyalar
@app.route("/admin/categories")
@login_required
def admin_categories():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY id ASC").fetchall()
    conn.close()
    return render_template("admin/categories.html", categories=categories)

@app.route("/admin/categories/add", methods=["POST"])
@login_required
def admin_add_category():
    name_uz = request.form.get("name_uz", "").strip()
    name_ru = request.form.get("name_ru", "").strip() or None
    if not name_uz:
        return redirect(url_for("admin_categories"))
    conn = get_db_connection()
    conn.execute("INSERT INTO categories (name_uz, name_ru) VALUES (?, ?)", (name_uz, name_ru))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_categories"))

@app.route("/admin/categories/delete/<int:category_id>")
@login_required
def admin_delete_category(category_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE category_id=?", (category_id,))
    conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_categories"))

@app.route("/admin/categories/edit/<int:category_id>", methods=["GET", "POST"])
@login_required
def admin_edit_category(category_id):
    conn = get_db_connection()
    category = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    if not category:
        conn.close()
        abort(404)

    if request.method == "POST":
        name_uz = request.form.get("name_uz", "").strip()
        name_ru = request.form.get("name_ru", "").strip() or None
        if name_uz:
            conn.execute("UPDATE categories SET name_uz=?, name_ru=? WHERE id=?", (name_uz, name_ru, category_id))
            conn.commit()
        conn.close()
        return redirect(url_for("admin_categories"))

    conn.close()
    return render_template("admin/edit_category.html", category=category)

# 📂 Admin: mahsulot tahrirlash
@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def admin_edit_product(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    categories = conn.execute("SELECT * FROM categories ORDER BY id ASC").fetchall()

    if not product:
        conn.close()
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "0").strip()
        category_id = request.form.get("category_id")

        # 📸 Yangi rasm yuklansa
        image_file = request.files.get("image")
        if image_file and image_file.filename and allowed_file(image_file.filename):
            ext = image_file.filename.rsplit(".", 1)[1].lower()
            filename = f"prod_{uuid.uuid4().hex[:12]}.{ext}"
            save_path = os.path.join(app.config["PRODUCT_FOLDER"], filename)
            image_file.save(save_path)
            image_path = f"/static/products/{filename}"
        else:
            # eski rasm qoladi
            image_path = product["image"]

        conn.execute(
            "UPDATE products SET name=?, price=?, category_id=?, image=? WHERE id=?",
            (name, price, category_id, image_path, product_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_products"))

    conn.close()
    return render_template("admin/edit_product.html", product=product, categories=categories)

@app.route("/admin/products")
@login_required
def admin_products():
    conn = get_db_connection()

    # 🛒 Barcha mahsulotlar (ketma-ketlikda)
    products = conn.execute("""
        SELECT p.id, p.name, p.price, p.image, COALESCE(p.stock, 100) as stock,
               c.name_uz, c.name_ru
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id ASC
    """).fetchall()

    # 📂 Barcha kategoriyalarni olish (dropdown uchun)
    categories = conn.execute("SELECT id, name_uz, name_ru FROM categories ORDER BY id ASC").fetchall()

    conn.close()

    # 📝 Mahsulotlarni chiqarishda kategoriyani tanlash
    result = []
    for p in products:
        result.append({
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "image": p["image"],
            "stock": p["stock"],
            "category_name": p["name_uz"] or p["name_ru"] or "🚫"
        })

    return render_template("admin/products.html",
                           products=result,
                           categories=categories)

# 📂 Admin: mahsulot qo‘shish
@app.route("/admin/products/add", methods=["POST"])
@login_required
def admin_add_product():
    name = request.form.get("name", "").strip()
    price = request.form.get("price", "0").strip()
    category_id = request.form.get("category_id")
    stock_raw = request.form.get("stock", "100").strip()

    try:
        stock = int(stock_raw)
    except ValueError:
        stock = 100

    if not name or not price or not category_id:
        return redirect(url_for("admin_products"))

    # 📸 Rasmni yuklash
    image_file = request.files.get("image")
    image_path = None
    if image_file and image_file.filename and allowed_file(image_file.filename):
        ext = image_file.filename.rsplit(".", 1)[1].lower()
        filename = f"prod_{uuid.uuid4().hex[:12]}.{ext}"
        save_path = os.path.join(app.config["PRODUCT_FOLDER"], filename)
        image_file.save(save_path)
        # DB uchun faqat nisbiy yo‘lni saqlaymiz
        image_path = f"/static/products/{filename}"

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO products (name, price, image, category_id, stock, is_available) VALUES (?, ?, ?, ?, ?, ?)",
        (name, price, image_path, category_id, stock, 1 if stock > 0 else 0)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_products"))

@app.route("/admin/products/delete/<int:product_id>")
@login_required
def admin_delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_products"))

# 📂 Admin: foydalanuvchilar (ketma-ketlikda)
@app.route("/admin/users")
@login_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)

# 📂 Admin: foydalanuvchini o‘chirish
@app.route("/admin/users/delete/<int:user_id>")
@login_required
def admin_delete_user(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_users"))


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            requests.post(TELEGRAM_API, data={
                "chat_id": chat_id,
                "text": "👋 Salom! Xush kelibsiz!"
            })

    return jsonify({"ok": True})




# =====================
# RUN
# =====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)

