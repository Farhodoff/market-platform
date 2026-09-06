# bot_notify.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

def get_admin_ids():
    admin_id_env = os.getenv("ADMIN_CHAT_ID", "")
    if not admin_id_env:
        return []
    ids = []
    for item in admin_id_env.split(","):
        item = item.strip()
        if item.isdigit():
            ids.append(int(item))
    return ids

def notify_admin(order, items=None, receipt_path=None):
    """
    Adminlarga yangi buyurtma haqida xabar yuborish.
    order - dict yoki Row obyekti: id, name, phone, address, total_price, status
    items - buyurtma qilingan mahsulotlar ro'yxati (ixtiyoriy)
    receipt_path - yuklangan to'lov cheki fayl yo'li (ixtiyoriy)
    """
    admin_ids = get_admin_ids()
    if not BOT_TOKEN or not admin_ids:
        print("⚠️ BOT_TOKEN yoki ADMIN_CHAT_ID sozlanmagan, admin xabari yuborilmadi.")
        return

    try:
        if hasattr(order, "keys"):
            order_dict = dict(order)
        else:
            order_dict = order or {}

        total_price = order_dict.get("total_price", order_dict.get("total", 0))
        try:
            formatted_total = f"{int(total_price):,}".replace(",", " ")
        except (ValueError, TypeError):
            formatted_total = str(total_price)

        items_text = ""
        order_items = items or order_dict.get("items") or []
        if order_items:
            items_list = []
            for it in order_items:
                p_name = it.get("name") or it.get("product_name", "Mahsulot")
                qty = it.get("quantity", 1)
                price = it.get("price", 0)
                try:
                    price_str = f"{int(price):,}".replace(",", " ")
                except (ValueError, TypeError):
                    price_str = str(price)
                items_list.append(f"  • {p_name} x {qty} ({price_str} so'm)")
            items_text = "\n📦 Mahsulotlar:\n" + "\n".join(items_list) + "\n"

        text = (
            f"🆕 <b>Yangi buyurtma #{order_dict.get('id', 'N/A')}</b>\n\n"
            f"👤 <b>Mijoz:</b> {order_dict.get('name', 'N/A')}\n"
            f"📞 <b>Telefon:</b> {order_dict.get('phone', 'N/A')}\n"
            f"📍 <b>Manzil:</b> {order_dict.get('address', 'N/A')}\n"
            f"{items_text}"
            f"💰 <b>Jami summa:</b> {formatted_total} so'm\n"
            f"📌 <b>Holat:</b> {order_dict.get('status', 'Kutilmoqda')}"
        )

        for admin_id in admin_ids:
            # Agar to'lov cheki mavjud bo'lsa, rasmni jo'natamiz
            if receipt_path and os.path.exists(receipt_path):
                try:
                    with open(receipt_path, "rb") as photo:
                        requests.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                            data={"chat_id": admin_id, "caption": text, "parse_mode": "HTML"},
                            files={"photo": photo},
                            timeout=10
                        )
                    continue
                except Exception as ex_photo:
                    print(f"⚠️ Chek rasmini yuborishda xatolik: {ex_photo}")

            # Agar rasm yo'q bo'lsa yoki xatolik bo'lsa, matn yuboramiz
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": admin_id, "text": text, "parse_mode": "HTML"},
                timeout=5
            )
    except Exception as e:
        print(f"❌ Admin xabari yuborilmadi: {e}")