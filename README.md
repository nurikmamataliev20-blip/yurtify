# Yurtify - Real Estate Marketplace

## Overview
Real estate marketplace for Kyrgyzstan built with Flutter + FastAPI.

## Tech Stack
- Backend: Python, FastAPI, MySQL, SQLAlchemy, Alembic, JWT
- Mobile: Flutter, Dart, Riverpod, Go Router, Dio
- Admin Panel: FastAPI + Jinja2

## Setup

### Backend
```bash
cd yurtify
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

### Flutter
```bash
cd yurtify_flutter
flutter pub get
flutter run
```

### Admin Panel
Open: http://localhost:8000/admin/login

## Demo Credentials
- Admin: admin@yurtify.com / admin123456
- User: seller@yurtify.com / seller123456

## Environment Variables
- DATABASE_URL=mysql+pymysql://user:password@localhost/yurtify
- SECRET_KEY=your-secret-key
- ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=30

## Features
- User registration and authentication
- Real estate listings with photos
- Search, filters, sorting, pagination
- Favorites
- Messaging with attachments
- Notifications
- Reports/moderation
- Payments (mock)
- Promotions/boosting
- RU/EN localization
- Admin panel

## Known Limitations
- Payment gateway is mocked
- No push notifications
