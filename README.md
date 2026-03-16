# 🛒 Market Platform

Telegram orqali ishlaydigan onlayn do'kon platformasi. Foydalanuvchilar Telegram bot orqali ro'yxatdan o'tib, mahsulotlarni ko'rish, savatcha tuzish va buyurtma berish imkoniyatiga ega.

---

## 🛠 Texnologiyalar

### Backend & Bot

![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Telegram](https://img.shields.io/badge/Telegram%20Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Uvicorn](https://img.shields.io/badge/uvicorn-4051B5?style=for-the-badge&logo=gunicorn&logoColor=white)

### Ma'lumotlar bazasi & To'plamlar

![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Jinja](https://img.shields.io/badge/jinja-white.svg?style=for-the-badge&logo=jinja&logoColor=black)
![Pydantic](https://img.shields.io/badge/pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)

### Frontend (Telegram WebApp)

![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![Telegram WebApp](https://img.shields.io/badge/Telegram%20WebApp-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)

### Xalqarolashtirish (i18n)

![Flask-Babel](https://img.shields.io/badge/Flask--Babel-F1D43B?style=for-the-badge&logo=babel&logoColor=black)

---

## 📌 Asosiy Xususiyatlar

- 🤖 **Telegram Bot** — foydalanuvchi ro'yxatdan o'tishi, til tanlashi (O'z/Ru)
- 🛒 **Telegram WebApp** — toifalar, mahsulotlar, savatcha va buyurtma berish
- 🔐 **Admin Panel** (FastAPI) — buyurtmalar, mahsulotlar va foydalanuvchilarni boshqarish
- 🌍 **Ko'p tilli qo'llab-quvvatlash** — O'zbekcha va Ruscha
- 📦 **SQLite ma'lumotlar bazasi** — foydalanuvchilar, mahsulotlar, buyurtmalar
- 📸 **Rasm yuklash** — mahsulot va to'lov cheklari uchun

---

## 🚀 Ishga tushirish

```bash
# 1. Kerakli kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2. .env faylini sozlash
cp .env.example .env

# 3. Flask serverini ishga tushirish
python server.py

# 4. Telegram botni ishga tushirish
python bot.py
```

---

## 📁 Loyiha Tuzilmasi

```
market-platform/
├── server.py        # Flask web app (Telegram WebApp backend)
├── admin.py         # FastAPI admin panel
├── bot.py           # Telegram bot
├── db.py            # Ma'lumotlar bazasi bilan ishlash
├── templates/       # Jinja2 HTML shablonlar
├── static/          # CSS, JS va rasmlar
├── translations/    # Flask-Babel tarjimalar (uz, ru)
├── uploads/         # To'lov cheklari
└── requirements.txt
```
