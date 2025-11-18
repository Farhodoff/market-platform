# bot_notify.py
import requests

BOT_TOKEN = "8358580670:AAFcgvDfmkA4U6utmfFn9qgfOU0EA3gX17A"
ADMIN_IDS = [6756073816]  # adminlarning Telegram ID'lari

def notify_admin(order):
    """
    Adminlarga yangi buyurtma haqida xabar yuborish.
    order - dict yoki Row obyekti, quyidagi kalitlarga ega bo'lishi kerak:
    - id, name, phone, address, total_price, status
    """
    try:
        # Dict yoki Row obyektini dictga aylantirish
        if hasattr(order, 'keys'):
            order_dict = dict(order)
        else:
            order_dict = order
            
        text = f"""
🆕 Yangi buyurtma #{order_dict.get('id', 'N/A')}
👤 {order_dict.get('name', 'N/A')}
📞 {order_dict.get('phone', 'N/A')}
📍 {order_dict.get('address', 'N/A')}
💰 Jami: {order_dict.get('total_price', order_dict.get('total', 'N/A'))} so'm
📌 Status: {order_dict.get('status', 'N/A')}
"""
        for admin_id in ADMIN_IDS:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
                "chat_id": admin_id,
                "text": text
            }, timeout=5)
    except Exception as e:
        print(f"❌ Admin xabari yuborilmadi: {e}")