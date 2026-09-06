# 🛒 Market Platform

Telegram orqali ishlaydigan zamonaviy onlayn do'kon platformasi. Foydalanuvchilar Telegram bot orqali ro'yxatdan o'tib, mahsulotlarni ko'rish, savatcha tuzish va buyurtma berish imkoniyatiga ega.

---

## 🛠 Texnologiyalar

### Backend & Bot

![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram%20Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)

### Ma'lumotlar bazasi & To'plamlar

![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Jinja](https://img.shields.io/badge/jinja-white.svg?style=for-the-badge&logo=jinja&logoColor=black)

### Frontend (Telegram WebApp)

![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![Telegram WebApp](https://img.shields.io/badge/Telegram%20WebApp-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)

### Xalqarolashtirish (i18n)

![Flask-Babel](https://img.shields.io/badge/Flask--Babel-F1D43B?style=for-the-badge&logo=babel&logoColor=black)

---

## 📌 Asosiy Xususiyatlar

- 🤖 **Telegram Bot** — foydalanuvchi ro'yxatdan o'tishi, kontakt va manzil ulashishi, til tanlashi (O'z/Ru)
- 🛒 **Telegram WebApp** — toifalar, mahsulotlar, interaktiv savatcha (AJAX) va minimal buyurtma nazorati
- 🔐 **Admin Panel** — buyurtmalar holatini yangilash, mahsulotlar va toifalarni boshqarish, foydalanuvchilar ro'yxati
- 📣 **Admin Bildirishnomasi** — har bir yangi buyurtma va to'lov cheki darhol admin Telegramiga yuboriladi
- 🌍 **Ko'p tilli tizim** — O'zbekcha va Ruscha (Babel i18n)
- 📦 **Xavfsiz SQLite (WAL mode)** — tezkor va bloklanmaydigan ma'lumotlar bazasi
- 📸 **Xavfsiz fayl yuklash** — to'lov cheklari va mahsulot rasmlari unikal nom bilan saqlanadi

---

## 🚀 Ishga tushirish

```bash
# 1. Kerakli kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2. .env faylini sozlash (.env.example asosida)
cp .env.example .env
# .env faylini ochib bot token va boshqa ma'lumotlarni kiriting

# 3. Flask serverini ishga tushirish
python server.py

# 4. Telegram botni ishga tushirish (alohida terminalda)
python bot.py
```

---

## 📁 Loyiha Tuzilmasi

```
market-platform/
├── server.py        # Flask WebApp & Admin Panel backend
├── bot.py           # Telegram bot (ro'yxatdan o'tish va menyu)
├── bot_notify.py    # Yangi buyurtmalarni adminga Telegram orqali yuborish
├── db.py            # SQLite ma'lumotlar bazasi operatsiyalari (WAL mode)
├── templates/       # HTML shablonlar (WebApp & Admin)
│   ├── admin/       # Admin panel shablonlari
│   ├── index.html   # WebApp bosh sahifasi
│   ├── products.html# Mahsulotlar ro'yxati
│   ├── cart.html    # Savatcha sahifasi
│   ├── checkout.html# To'lov va chek yuklash
│   └── orders.html  # Buyurtmalar tarixi
├── static/          # CSS, JS va rasmlar
├── translations/    # Flask-Babel tarjimalar (uz, ru)
├── uploads/         # To'lov cheklari
├── .env.example     # Konfiguratsiya namunasi
├── .gitignore       # Git e'tiborsiz qoldiradigan fayllar
└── requirements.txt # Python bog'liqliklari
```
