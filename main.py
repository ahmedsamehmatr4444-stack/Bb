import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import threading
import requests
import uuid
import os
import datetime

# ================= الإعدادات الأساسية =================
BOT_TOKEN = "8764397517:AAHNtkUYi15yT8IrkDaK954PBQtgywJ5Mfg"
ADMINS = [18147516847, 1358013723] 
DOMAIN = "https://bb-production-7996.up.railway.app" 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= 1. طبقة قاعدة البيانات الشاملة =================
def init_db():
    conn = sqlite3.connect('union_radar.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, phone TEXT, 
                  is_virtual_phone TEXT, canvas_hash TEXT, screen TEXT, cores TEXT, 
                  browser TEXT, ip TEXT, isp TEXT, vpn TEXT, device_uuid TEXT, 
                  join_date TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ================= 2. طبقة الموقع السري وسحب البصمات (JS & HTML) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>توثيق الاتحاد العربي | Arab Union</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: #0f172a; color: #f8fafc; padding-top: 20%; margin: 0; }
        .loader { border: 4px solid #1e293b; border-top: 4px solid #3b82f6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        #status { font-size: 1.2rem; font-weight: bold; }
    </style>
</head>
<body>
    <div class="loader" id="spinner"></div>
    <h2 id="status">⏳ جاري فحص أمان الجهاز وتوثيق الحساب...</h2>
    <p id="sub-status" style="color: #94a3b8; font-size: 0.9rem;">يرجى عدم إغلاق هذه الصفحة</p>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        async function getDeepFingerprint() {
            let fp = {
                screen: window.screen.width + "x" + window.screen.height,
                cores: navigator.hardwareConcurrency || "Unknown",
                lang: navigator.language,
                ua: navigator.userAgent,
                canvas_hash: getCanvasHash()
            };
            try {
                if (navigator.getBattery) {
                    let bat = await navigator.getBattery();
                    fp.battery = Math.round(bat.level * 100) + "% " + (bat.charging ? "⚡يتم الشحن" : "🔋");
                } else { fp.battery = "غير مدعوم"; }
            } catch(e) { fp.battery = "مجهول"; }

            fetch("/api/save_fingerprint?user_id={{user_id}}", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(fp)
            }).then(response => response.json())
              .then(data => {
                document.getElementById("spinner").style.display = "none";
                document.getElementById("status").innerHTML = "✅ تم التوثيق بنجاح!";
                document.getElementById("status").style.color = "#22c55e";
                document.getElementById("sub-status").innerHTML = "يمكنك إغلاق هذه النافذة والعودة للبوت الآن.";
                setTimeout(() => { tg.close(); }, 2000);
            });
        }

        function getCanvasHash() {
            let canvas = document.createElement("canvas");
            let ctx = canvas.getContext("2d");
            ctx.textBaseline = "top"; ctx.font = "16px 'Arial'"; ctx.fillStyle = "#f60";
            ctx.fillRect(125,1,62,20); ctx.fillStyle = "#069"; ctx.fillText("ArabUnion_Sec_2026", 2, 15);
            ctx.fillStyle = "rgba(102, 204, 0, 0.7)"; ctx.fillText("ArabUnion_Sec_2026", 4, 17);
            let data = canvas.toDataURL(); let hash = 0;
            for (let i = 0; i < data.length; i++) {
                hash = ((hash << 5) - hash) + data.charCodeAt(i); hash = hash & hash;
            }
            return Math.abs(hash).toString();
        }
        window.onload = getDeepFingerprint;
    </script>
</body>
</html>
"""

@app.route('/verify/<int:user_id>')
def verify_page(user_id):
    return render_template_string(HTML_TEMPLATE, user_id=user_id)

@app.route('/api/save_fingerprint', methods=['POST'])
def save_fingerprint():
    user_id = request.args.get('user_id')
    data = request.json
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    vpn_status = "لا"
    isp_name = "غير معروف"
    try:
        ip_check = requests.get(f"http://ip-api.com/json/{user_ip}?fields=proxy,isp,status,country", timeout=3).json()
        if ip_check.get('status') == 'success':
            isp_name = f"{ip_check.get('isp')} ({ip_check.get('country')})"
            vpn_status = "نعم 🚨 (مشبوه)" if ip_check.get('proxy') else "لا ✅"
    except:
        pass

    device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, data['canvas_hash'] + data['screen'] + str(data['cores'])))
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute('''UPDATE users SET canvas_hash=?, screen=?, cores=?, browser=?, ip=?, isp=?, vpn=?, device_uuid=?, join_date=? 
                 WHERE user_id=?''',
              (data['canvas_hash'], data['screen'], str(data['cores']), data['ua'][:100], user_ip, isp_name, vpn_status, device_uuid, now_time, user_id))
    c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status='rejected' ''', 
              (device_uuid, data['canvas_hash'], user_id))
    banned_match = c.fetchone()
    c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status!='rejected' ''', 
              (device_uuid, data['canvas_hash'], user_id))
    normal_match = c.fetchone()
    c.execute('''SELECT phone, is_virtual_phone FROM users WHERE user_id=?''', (user_id,))
    phone_data = c.fetchone()
    conn.close()

    phone_num = phone_data[0] if phone_data else "غير مسجل"
    is_virtual = phone_data[1] if phone_data else "غير معروف"

    report = f"""
🚨 **تقرير الرادار الرقمي (سري جداً)** 🚨
━━━━━━━━━━━━━━━━━
👤 **بيانات الحساب:**
- **الآي دي:** `{user_id}`
- **الهاتف:** `{phone_num}`
- **رقم وهمي؟:** `{is_virtual}`

📱 **الهوية الصلبة (Hardware):**
- **الرقم التسلسلي (UUID):** `{device_uuid}`
- **بصمة الـ Canvas:** `{data['canvas_hash']}`
- **الشاشة المعالج:** `{data['screen']} | {data['cores']} Cores`
- **البطارية لحظياً:** `{data.get('battery', 'N/A')}`

🌐 **بيانات الشبكة:**
- **الـ IP:** `{user_ip}`
- **مزود الخدمة:** `{isp_name}`
- **استخدام VPN:** `{vpn_status}`

{"\n❌ **تنبيه خطير:** تطابق مع مطرود" if banned_match else "\n⚠️ **اشتباه تكرار**" if normal_match else "\n✅ **الجهاز نظيف**"}
"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
               InlineKeyboardButton("❌ طرد", callback_data=f"reject_{user_id}"))
    for admin in ADMINS:
        try: bot.send_message(admin, report, parse_mode="Markdown", reply_markup=markup)
        except: pass
    return jsonify({"status": "success"})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name, username, status) VALUES (?, ?, ?, 'pending')", 
              (user.id, user.first_name, user.username))
    conn.commit()
    conn.close()
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 مشاركة جهة الاتصال (ضروري)", request_contact=True))
    bot.reply_to(message, "أهلاً بك في نظام حماية الاتحاد.\nللبدء، شارك جهة الاتصال:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    phone = message.contact.phone_number
    virtual_prefixes = ['1', '44', '48']
    is_virtual = "نعم 🚨" if any(phone.startswith(p) for p in virtual_prefixes) else "لا ✅"
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute("UPDATE users SET phone=?, is_virtual_phone=? WHERE user_id=?", (phone, is_virtual, user_id))
    conn.commit()
    conn.close()
    
    # تحويل الرابط إلى تطبيق داخلي (Web App)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔐 دخول بوابة التوثيق الآمن", web_app=WebAppInfo(url=f"{DOMAIN}/verify/{user_id}")))
    
    bot.send_message(user_id, "✅ تم تسجيل رقمك.\n\nالآن اضغط على الزر بالأسفل لتوثيق جهازك داخل التليجرام:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
def admin_decision(call):
    action, target_id = call.data.split('_')
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    if action == "accept":
        c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "🎉 تم توثيقك!")
    else:
        c.execute("UPDATE users SET status='rejected' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "❌ تم رفضك.")
    conn.commit()
    conn.close()

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>توثيق الاتحاد العربي | Arab Union</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: #0f172a; color: #f8fafc; padding-top: 20%; margin: 0; }
        .loader { border: 4px solid #1e293b; border-top: 4px solid #3b82f6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        #status { font-size: 1.2rem; font-weight: bold; }
    </style>
</head>
<body>
    <div class="loader" id="spinner"></div>
    <h2 id="status">⏳ جاري فحص أمان الجهاز وتوثيق الحساب...</h2>
    <p id="sub-status" style="color: #94a3b8; font-size: 0.9rem;">يرجى عدم إغلاق هذه الصفحة</p>
    
    <script>
        async function getDeepFingerprint() {
            let fp = {
                screen: window.screen.width + "x" + window.screen.height,
                cores: navigator.hardwareConcurrency || "Unknown",
                lang: navigator.language,
                ua: navigator.userAgent,
                canvas_hash: getCanvasHash()
            };
            try {
                if (navigator.getBattery) {
                    let bat = await navigator.getBattery();
                    fp.battery = Math.round(bat.level * 100) + "% " + (bat.charging ? "⚡يتم الشحن" : "🔋");
                } else { fp.battery = "غير مدعوم"; }
            } catch(e) { fp.battery = "مجهول"; }

            fetch("/api/save_fingerprint?user_id={{user_id}}", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(fp)
            }).then(response => response.json())
              .then(data => {
                document.getElementById("spinner").style.display = "none";
                document.getElementById("status").innerHTML = "✅ تم التوثيق بنجاح!";
                document.getElementById("status").style.color = "#22c55e";
                document.getElementById("sub-status").innerHTML = "يمكنك إغلاق هذه الصفحة والعودة للبوت الآن.";
            });
        }

        function getCanvasHash() {
            let canvas = document.createElement("canvas");
            let ctx = canvas.getContext("2d");
            ctx.textBaseline = "top"; ctx.font = "16px 'Arial'"; ctx.fillStyle = "#f60";
            ctx.fillRect(125,1,62,20); ctx.fillStyle = "#069"; ctx.fillText("ArabUnion_Sec_2026", 2, 15);
            ctx.fillStyle = "rgba(102, 204, 0, 0.7)"; ctx.fillText("ArabUnion_Sec_2026", 4, 17);
            let data = canvas.toDataURL(); let hash = 0;
            for (let i = 0; i < data.length; i++) {
                hash = ((hash << 5) - hash) + data.charCodeAt(i); hash = hash & hash;
            }
            return Math.abs(hash).toString();
        }
        window.onload = getDeepFingerprint;
    </script>
</body>
</html>
"""

@app.route('/verify/<int:user_id>')
def verify_page(user_id):
    return render_template_string(HTML_TEMPLATE, user_id=user_id)

@app.route('/api/save_fingerprint', methods=['POST'])
def save_fingerprint():
    user_id = request.args.get('user_id')
    data = request.json
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    vpn_status = "لا"
    isp_name = "غير معروف"
    try:
        ip_check = requests.get(f"http://ip-api.com/json/{user_ip}?fields=proxy,isp,status,country", timeout=3).json()
        if ip_check.get('status') == 'success':
            isp_name = f"{ip_check.get('isp')} ({ip_check.get('country')})"
            vpn_status = "نعم 🚨 (مشبوه)" if ip_check.get('proxy') else "لا ✅"
    except:
        pass

    device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, data['canvas_hash'] + data['screen'] + str(data['cores'])))
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute('''UPDATE users SET canvas_hash=?, screen=?, cores=?, browser=?, ip=?, isp=?, vpn=?, device_uuid=?, join_date=? 
                 WHERE user_id=?''',
              (data['canvas_hash'], data['screen'], str(data['cores']), data['ua'][:100], user_ip, isp_name, vpn_status, device_uuid, now_time, user_id))
    c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status='rejected' ''', 
              (device_uuid, data['canvas_hash'], user_id))
    banned_match = c.fetchone()
    c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status!='rejected' ''', 
              (device_uuid, data['canvas_hash'], user_id))
    normal_match = c.fetchone()
    c.execute('''SELECT phone, is_virtual_phone FROM users WHERE user_id=?''', (user_id,))
    phone_data = c.fetchone()
    conn.close()

    phone_num = phone_data[0] if phone_data else "غير مسجل"
    is_virtual = phone_data[1] if phone_data else "غير معروف"

    report = f"""
🚨 **تقرير الرادار الرقمي (سري جداً)** 🚨
━━━━━━━━━━━━━━━━━
👤 **بيانات الحساب:**
- **الآي دي:** `{user_id}`
- **الهاتف:** `{phone_num}`
- **رقم وهمي؟:** `{is_virtual}`

📱 **الهوية الصلبة (Hardware):**
- **الرقم التسلسلي (UUID):** `{device_uuid}`
- **بصمة الـ Canvas:** `{data['canvas_hash']}`
- **الشاشة المعالج:** `{data['screen']} | {data['cores']} Cores`
- **البطارية لحظياً:** `{data.get('battery', 'N/A')}`

🌐 **بيانات الشبكة:**
- **الـ IP:** `{user_ip}`
- **مزود الخدمة:** `{isp_name}`
- **استخدام VPN:** `{vpn_status}`

{"\n❌ **تنبيه خطير:** تطابق مع مطرود" if banned_match else "\n⚠️ **اشتباه تكرار**" if normal_match else "\n✅ **الجهاز نظيف**"}
"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
               InlineKeyboardButton("❌ طرد", callback_data=f"reject_{user_id}"))
    for admin in ADMINS:
        try: bot.send_message(admin, report, parse_mode="Markdown", reply_markup=markup)
        except: pass
    return jsonify({"status": "success"})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name, username, status) VALUES (?, ?, ?, 'pending')", 
              (user.id, user.first_name, user.username))
    conn.commit()
    conn.close()
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 مشاركة جهة الاتصال (ضروري)", request_contact=True))
    bot.reply_to(message, "أهلاً بك في نظام حماية الاتحاد.\nللبدء، شارك جهة الاتصال:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    phone = message.contact.phone_number
    virtual_prefixes = ['1', '44', '48']
    is_virtual = "نعم 🚨" if any(phone.startswith(p) for p in virtual_prefixes) else "لا ✅"
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute("UPDATE users SET phone=?, is_virtual_phone=? WHERE user_id=?", (phone, is_virtual, user_id))
    conn.commit()
    conn.close()
    bot.send_message(user_id, f"✅ تم تسجيل رقمك.\n\nاضغط هنا للتوثيق:\n{DOMAIN}/verify/{user_id}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
def admin_decision(call):
    action, target_id = call.data.split('_')
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    if action == "accept":
        c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "🎉 تم توثيقك!")
    else:
        c.execute("UPDATE users SET status='rejected' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "❌ تم رفضك.")
    conn.commit()
    conn.close()

def run_flask():
    # تعديل مهم جداً: Railway بيستخدم بورت متغير، لازم نسحبه من النظام
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
