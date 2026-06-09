# 🎤 Discord Voice Presence Tool

أداة لتثبيت حساب ديسكورد في روم صوتي 24/7 على منصة Render.

---

## 📋 المتطلبات

- حساب على [Render.com](https://render.com)
- توكن الحساب (DISCORD_TOKEN)
- معرف السيرفر (GUILD_ID)
- معرف الروم الصوتي (CHANNEL_ID)

---

## 🚀 خطوات التشغيل على Render

### ١. رفع المشروع على GitHub
```
Install_voice/
├── self-bot.py
├── requirements.txt
├── Procfile
├── .env.example
└── README.md
```
> ⚠️ لا ترفع `.env` على GitHub أبداً

### ٢. إنشاء Web Service على Render
1. اذهب إلى [render.com](https://render.com) وسجل دخول
2. اضغط **New → Web Service**
3. وصّل الـ GitHub repo
4. اضبط الإعدادات:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python self-bot.py`

### ٣. إضافة Environment Variables
في صفحة الـ Service اذهب إلى **Environment** وأضف:

| Key | Value |
|-----|-------|
| `DISCORD_TOKEN` | توكن الحساب |
| `GUILD_ID` | معرف السيرفر |
| `CHANNEL_ID` | معرف الروم الصوتي |
| `WEBHOOK_URL` | رابط ويب هوك (اختياري) |

### ٤. إعداد UptimeRobot
1. اذهب إلى [uptimerobot.com](https://uptimerobot.com)
2. أضف Monitor جديد:
   - **Type:** `HTTP(s)`
   - **URL:** `https://your-app.onrender.com/health`
   - **Interval:** `5 minutes`

---

## ✅ مميزات الأداة

- 🔄 **Reconnect تلقائي** — لو طاح من الفويس يرجع لوحده
- ⏳ **Retry عند البداية** — يحاول 5 مرات بانتظار تدريجي
- 🔔 **إشعارات Webhook** — يرسل في ديسكورد لو وقع أو رجع
- 📊 **Health Endpoint** — تشوف حالة الأداة من `/health`
- 📝 **Logging مفصل** — كل حدث مع الوقت في سجلات Render
- 🔐 **متغيرات بيئة** — التوكن محمي ما يظهر في الكود

---

## 🔍 تفاصيل تقنية

### DAVE Protocol
الأداة تستخدم `djs-selfbot-v13==3.7.28` التي تدعم بروتوكول DAVE
الإلزامي من مارس 2026. المكتبات القديمة تعطي خطأ `4017`.

### Health Endpoint
```json
GET /health
{
  "status": "alive",
  "in_voice": true,
  "channel": "General",
  "guild": "My Server",
  "reconnects": 0
}
```

---

## ⚠️ ملاحظة
الأداة مخصصة للاستخدام على الحسابات الشخصية فقط.
