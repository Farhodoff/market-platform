from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory, abort, g
import sqlite3, os, requests
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import pytz
import db
from flask_babel import Babel, gettext as _
from db import get_all_orders_with_items
from db import get_orders_by_user
app = Flask(__name__)

# 📂 Fayllar joylashuvi
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")   # foydalanuvchi chek
app.config["PRODUCT_FOLDER"] = os.path.join("static", "products")    # mahsulot rasmlari
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PRODUCT_FOLDER"], exist_ok=True)
app.config["BABEL_DEFAULT_LOCALE"] = "uz"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"


# 🔑 Session uchun secret key
app.secret_key = "supersecretkey123"

# 🔐 Admin login
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "220286"

# 🤖 Telegram bot sozlamalari
BOT_TOKEN = "8358580670:AAFcgvDfmkA4U6utmfFn9qgfOU0EA3gX17A"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# =====================
# 🔗 DB ulanish
# =====================
def get_db_connection():
    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row
    return conn

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
        session["tg_id"] = tg_id

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
    categories = conn.execute("SELECT id, name_uz, name_ru FROM categories").fetchall()
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
    products = conn.execute(
        "SELECT id, name, price, image FROM products WHERE category_id = ?",
        (category_id,)
    ).fetchall()
    conn.close()
    return render_template("products.html", products=products)

# 🛒 Savatchaga qo‘shish (AJAX)
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    data = request.get_json() or {}
    product_name = data.get("name")
    price = int(data.get("price", 0))

    if not product_name or price <= 0:
        return jsonify({"status": "error", "message": "Noto‘g‘ri mahsulot ma’lumoti"}), 400

    cart = session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            break
    else:
        cart.append({"name": product_name, "price": price, "quantity": 1})

    session["cart"] = cart
    session.modified = True
    return jsonify({"status": "success", "message": f"{product_name} savatchaga qo‘shildi!"})

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
    return jsonify({"status": "success"})

# ❌ Savatchadan o‘chirish
@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    data = request.get_json() or {}
    product_name = data.get("name")
    cart = session.get("cart", [])
    cart = [item for item in cart if item["name"] != product_name]
    session["cart"] = cart
    session.modified = True
    return jsonify({"status": "success", "message": f"{product_name} savatchadan olib tashlandi!"})

# ✅ Buyurtma berish
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    tg_id = session.get("tg_id")
    if not tg_id:
        return redirect(url_for("index"))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()

    cart = session.get("cart", [])
    products_total = sum(item["price"] * item["quantity"] for item in cart)
    delivery_fee = 10000
    total_price = products_total + delivery_fee

    if request.method == "POST":
        receipt_file = request.files.get("receipt")
        if not receipt_file or not receipt_file.filename:
            conn.close()
            return render_template("checkout.html", total=total_price, error=_("❌ To‘lov chekini yuklash majburiy!")), 400

        filename = secure_filename(receipt_file.filename)
        receipt_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        receipt_file.save(receipt_path)

        # 1️⃣ Orders jadvaliga yozamiz
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders (tg_id, name, phone, address, total_price, receipt, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Kutilmoqda', datetime('now'))
        """, (tg_id, user["name"], user["phone"], user["address"], total_price, filename))
        order_id = cur.lastrowid   # oxirgi qo‘shilgan order_id
        conn.commit()

        # 2️⃣ Har bir mahsulotni order_items ga yozamiz
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
                f"📍 Адрес: {user['address']}"
            )
        else:
            message = (
                f"🛒 Hurmatli {user['name']}, buyurtmangiz qabul qilindi!\n\n"
                f"📦 Jami summa: {total_price} so‘m\n"
                f"📍 Manzil: {user['address']}"
            )

        try:
            requests.post(TELEGRAM_API, data={"chat_id": tg_id, "text": message})
        except Exception as e:
            print("❌ Qabul xabari yuborilmadi:", e)

        session.pop("cart", None)
        return redirect(url_for("orders"))

    conn.close()
    return render_template("checkout.html", total=total_price)

# 📝 Buyurtmalar (faqat shu foydalanuvchiga)
@app.route("/orders")
def orders():
    tg_id = request.args.get("tg_id") or session.get("tg_id")
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
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
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
@login_required
def admin_dashboard():
    return redirect(url_for("admin_orders"))

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
                f"✅ Hurmatli {order['name']}, buyurtmangiz tasdiqlandi!\n\n"
                f"🚚 Tez orada yetkazib beriladi.\n"
                f"📦 Jami summa: {order['total_price']} so‘m"
            )
        },
        "ru": {
            "approved": (
                f"✅ Уважаемый {order['name']}, ваш заказ подтвержден!\n\n"
                f"🚚 Скоро будет доставлен.\n"
                f"📦 Общая сумма: {order['total_price']} сум"
            )
        }
    }

    # Faqat "Tasdiqlandi" bo‘lsa xabar yuboramiz
    if new_status == "Tasdiqlandi" and order["tg_id"]:
        message = MESSAGES.get(lang, MESSAGES["uz"])["approved"]

        try:
            requests.post(TELEGRAM_API, data={"chat_id": order["tg_id"], "text": message})
        except Exception as e:
            print("❌ Tasdiqlash xabari yuborilmadi:", e)

    return redirect(url_for("admin_orders"))

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
    name = request.form.get("name")
    if not name:
        return redirect(url_for("admin_categories"))
    conn = get_db_connection()
    conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_categories"))

@app.route("/admin/categories/delete/<int:category_id>")
@login_required
def admin_delete_category(category_id):
    conn = get_db_connection()
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
        new_name = request.form.get("name")
        if new_name:
            conn.execute("UPDATE categories SET name=? WHERE id=?", (new_name, category_id))
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
        name = request.form.get("name")
        price = request.form.get("price")
        category_id = request.form.get("category_id")

        # 📸 Yangi rasm yuklansa
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
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

    # 🛒 Barcha mahsulotlar
    products = conn.execute("""
        SELECT p.id, p.name, p.price, p.image,
               c.name_uz, c.name_ru
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id DESC
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
            "category_name": p["name_uz"] or p["name_ru"] or "🚫"
        })

    return render_template("admin/products.html",
                           products=result,
                           categories=categories)

# 📂 Admin: mahsulot qo‘shish
@app.route("/admin/products/add", methods=["POST"])
@login_required
def admin_add_product():
    name = request.form.get("name")
    price = request.form.get("price")
    category_id = request.form.get("category_id")

    if not name or not price or not category_id:
        return redirect(url_for("admin_products"))

    # 📸 Rasmni yuklash
    image_file = request.files.get("image")
    image_path = None
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(app.config["PRODUCT_FOLDER"], filename)
        image_file.save(save_path)
        # DB uchun faqat nisbiy yo‘lni saqlaymiz
        image_path = f"/static/products/{filename}"

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO products (name, price, image, category_id) VALUES (?, ?, ?, ?)",
        (name, price, image_path, category_id)
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

# 📂 Admin: foydalanuvchilar
@app.route("/admin/users")
@login_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)


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

