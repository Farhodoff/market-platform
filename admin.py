from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import db
from bot_notify import notify_admin
import os

# FastAPI app
app = FastAPI()

# Static va templates ulash
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Root -> orders sahifasiga yo‘naltirish
@app.get("/")
def root():
    return RedirectResponse(url="/orders")


# 🛒 Orders page
@app.get("/orders")
def orders_page(request: Request):
    orders = db.get_orders()
    return templates.TemplateResponse("orders.html", {"request": request, "orders": orders})


# 📝 Checkout form (GET - sahifa ko‘rsatish)
@app.get("/checkout")
async def checkout_form(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request})


# 📨 Checkout submit (POST - formani DB ga yozish)
@app.post("/checkout")
async def checkout_submit(
    request: Request,
    tg_id: int = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    receipt: UploadFile = File(None)
):
    # Foydalanuvchini olish yoki yaratish
    user = db.get_user_by_tg_id(tg_id)
    if not user:
        db.add_user(tg_id, name, phone, address)
        user = db.get_user_by_tg_id(tg_id)

    if not user:
        return {"error": "Foydalanuvchi yaratilmadi yoki topilmadi."}

    user_id = user["id"]
    total = db.get_cart_total(user_id)

    # Minimal buyurtma summasi tekshiruv
    if total < 100000:
        return {"error": "Minimal buyurtma summasi 100 000 so‘m bo‘lishi kerak!"}

    # Check fayl (agar bo‘lsa)
    receipt_path = None
    if receipt:
        os.makedirs("uploads", exist_ok=True)
        receipt_path = f"uploads/{receipt.filename}"
        with open(receipt_path, "wb") as f:
            f.write(await receipt.read())

    # Buyurtmani qo‘shish
    order_id = db.add_order(name, phone, address, receipt_path)
    db.update_order_total(order_id, total)
    db.clear_cart(user_id)

    # Adminni xabardor qilish
    order = db.get_order(order_id)
    notify_admin(order)

    # Orders sahifasiga qaytarish
    return RedirectResponse("/orders", status_code=303)