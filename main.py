import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import uuid
import os
import datetime
import threading
import time
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)

# ================= الإعدادات الأساسية (مضمنة) =================
BOT_TOKEN = "8764397517:AAEKRxpwiWp_Ow2puiu_dPLqknJx1_Q2u9E"
ADMINS = [1358013723, 8147516847]          # معرفات المشرفين
DOMAIN = "https://bb-production-bd88.up.railway.app"   # الرابط الجديد

PORT = int(os.environ.get("PORT", 8080))

logging.info(f"DOMAIN: {DOMAIN}")
logging.info(f"PORT: {PORT}")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= قاعدة البيانات =================
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
    logging.info("Database initialized")

init_db()

# ================= قالب صفحة التوثيق =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>توثيق الاتحاد العربي | Arab Union</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            text-align: center; 
            background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%); 
            color: #f8fafc; 
            padding-top: 25%; 
            margin: 0; 
            overflow: hidden;
        }
        .loader-container {
            position: relative;
            width: 80px;
            height: 80px;
            margin: 0 auto 30px auto;
        }
        .loader { 
            border: 5px solid rgba(59, 130, 246, 0.1); 
            border-top: 5px solid #3b82f6; 
            border-radius: 50%; 
            width: 80px; 
            height: 80px; 
            animation: spin 1s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite; 
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
            margin: 0 auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        h2 { 
            font-size: 1.4rem; 
            font-weight: bold; 
            text-shadow: 0 2px 10px rgba(0,0,0,0.5);
            background: linear-gradient(to bottom, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        #sub-status { color: #64748b; font-size: 0.9rem; margin-top: 10px; }
        
        .success-mode h2 { 
            -webkit-text-fill-color: #22c55e; 
            text-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
        }
        .error-mode h2 {
            -webkit-text-fill-color: #ef4444;
            text-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
        }
    </style>
</head>
<body>
    <div class="loader-container">
        <div class="loader" id="spinner"></div>
    </div>
    <h2 id="status">⏳ جاري فحص أمان الجهاز وتوثيق الحساب...</h2>
    <p id="sub-status">يرجى عدم إغلاق هذه الصفحة لضمان اكتمال التوثيق</p>
    
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
            })
            .then(response => response.json())
            .then(data => {
                document.body.classList.add("success-mode");
                document.getElementById("spinner").style.display = "none";
                document.getElementById("status").innerHTML = "✅ تم التوثيق بنجاح!";
                document.getElementById("sub-status").innerHTML = "تم إرسال بياناتك للفحص، يمكنك العودة الآن.";
                setTimeout(() => { tg.close(); }, 2500);
            })
            .catch(error => {
                document.body.classList.add("error-mode");
                document.getElementById("spinner").style.display = "none";
                document.getElementById("status").innerHTML = "❌ حدث خطأ أثناء التوثيق";
                document.getElementById("sub-status").innerHTML = "يرجى المحاولة مرة أخرى لاحقاً.";
                setTimeout(() => { tg.close(); }, 3000);
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

# ================= مسارات Flask =================
@app.route('/')
def index():
    return "Bot is running!"

@app.route('/verify/<int:user_id>')
def verify_page(user_id):
    return render_template_string(HTML_TEMPLATE, user_id=user_id)

@app.route('/api/save_fingerprint', methods=['POST'])
def save_fingerprint():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id missing"}), 400
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "invalid user_id"}), 400

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
    conn.commit()
    conn.close()

    phone_num = phone_data[0] if phone_data else "غير مسجل"
    is_virtual = phone_data[1] if phone_data else "غير معروف"

    if banned_match:
        security_note = f"\n❌ **تنبيه خطير:** تطابق مع مطرود (ID: {banned_match[0]})"
    elif normal_match:
        security_note = f"\n⚠️ **اشتباه تكرار:** هذا الجهاز يخص عضو آخر (ID: {normal_match[0]})"
    else:
        security_note = "\n✅ **الجهاز نظيف**"

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
- **الشاشة | المعالج:** `{data['screen']} | {data['cores']} Cores`
- **البطارية لحظياً:** `{data.get('battery', 'N/A')}`

🌐 **بيانات الشبكة:**
- **الـ IP:** `{user_ip}`
- **مزود الخدمة:** `{isp_name}`
- **استخدام VPN:** `{vpn_status}`
{security_note}
"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
               InlineKeyboardButton("❌ طرد", callback_data=f"reject_{user_id}"))
    for admin in ADMINS:
        try:
            bot.send_message(admin, report, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            logging.error(f"Failed to send to admin {admin}: {e}")
    return jsonify({"status": "success"})

# ================= مسار webhook =================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

# ================= أوامر البوت =================
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
    bot.reply_to(message, "أهلاً بك في نظام حماية الاتحاد العربي.\nللبدء، يرجى مشاركة جهة الاتصال الخاصة بك:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    phone = message.contact.phone_number
    virtual_prefixes = ['1', '+1', '44', '+44', '48', '+48', '371', '+371', '380', '+380']
    is_virtual = "نعم 🚨" if any(phone.startswith(p) for p in virtual_prefixes) else "لا ✅"
    
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute("UPDATE users SET phone=?, is_virtual_phone=? WHERE user_id=?", (phone, is_virtual, user_id))
    conn.commit()
    conn.close()
    
    # إنشاء زر WebApp
    markup = InlineKeyboardMarkup()
    web_app_url = f"{DOMAIN}/verify/{user_id}"
    markup.add(InlineKeyboardButton("🔐 دخول بوابة التوثيق الآمن", web_app=WebAppInfo(url=web_app_url)))
    
    bot.send_message(user_id, "✅ تم تسجيل رقم الهاتف.\n\nالآن اضغط على الزر بالأسفل لتوثيق جهازك بالكامل داخل التليجرام:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
def admin_decision(call):
    action, target_id = call.data.split('_')
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    if action == "accept":
        c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "🎉 مبروك! تم قبول توثيقك في الاتحاد.")
        try:
            bot.edit_message_text(f"{call.message.text}\n\n**القرار:** تم القبول ✅", 
                                  call.message.chat.id, call.message.message_id)
        except:
            pass
    else:
        c.execute("UPDATE users SET status='rejected' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "❌ نعتذر، تم رفض طلب توثيقك.")
        try:
            bot.edit_message_text(f"{call.message.text}\n\n**القرار:** تم الطرد ❌", 
                                  call.message.chat.id, call.message.message_id)
        except:
            pass
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "تم تنفيذ القرار")

# ================= إعداد webhook (للإنتاج فقط) =================
def setup_webhook():
    time.sleep(3)  # انتظر قليلاً لضمان بدء الخادم
    webhook_url = f"{DOMAIN}/webhook"
    try:
        bot.delete_webhook()
        bot.set_webhook(url=webhook_url)
        logging.info(f"✅ Webhook set to {webhook_url}")
    except Exception as e:
        logging.error(f"❌ Failed to set webhook: {e}")

# ================= نقطة الدخول =================
# نكتشف البيئة: إذا كان الرابط ليس القيمة الافتراضية أو وجدنا RAILWAY_PUBLIC_DOMAIN
if DOMAIN != "https://your-app.up.railway.app" or os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    logging.info("Production mode detected, starting webhook setup...")
    threading.Thread(target=setup_webhook, daemon=True).start()
else:
    logging.info("Running locally with polling...")
    try:
        bot.delete_webhook()
    except:
        pass
    bot.infinity_polling(skip_pending=True)        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, phone TEXT, 
                      is_virtual_phone TEXT, canvas_hash TEXT, screen TEXT, cores TEXT, 
                      browser TEXT, ip TEXT, isp TEXT, vpn TEXT, device_uuid TEXT, 
                      join_date TEXT, status TEXT)''')
        conn.commit()
    logging.info("Database initialized")

init_db()

# ================= وظائف متقدمة =================
def parse_user_agent(ua):
    ua_lower = ua.lower()
    if 'android' in ua_lower:
        os_type = "🤖 Android"
        patterns = [r';\s([^;]+?)\s?(?:Build/|\))', r'Android\s[\d\.]+;\s([^;]+);', r'Android\s[\d\.]+;\s([^;]+)']
        device = "جهاز Android"
        for pattern in patterns:
            match = re.search(pattern, ua)
            if match:
                device = match.group(1).strip()
                break
        device = device.replace('_', ' ').replace('-', ' ')
    elif 'iphone' in ua_lower or 'ipad' in ua_lower:
        os_type = "🍎 iOS"
        match = re.search(r'(iPhone|iPad)(\d+,\d+)?', ua, re.IGNORECASE)
        device = match.group(0) if match else "iPhone/iPad"
    elif 'windows' in ua_lower:
        os_type = "🪟 Windows"
        if 'windows nt 10.0' in ua_lower:
            version = "10/11"
        elif 'windows nt 6.1' in ua_lower:
            version = "7"
        else:
            version = "قديم"
        device = f"كمبيوتر (Windows {version})"
    elif 'mac' in ua_lower:
        os_type = "🍏 macOS"
        device = "Mac"
    elif 'linux' in ua_lower:
        os_type = "🐧 Linux"
        device = "Linux"
    else:
        os_type = "❓ غير معروف"
        device = "غير معروف"
    return f"{os_type} | {device}"

def get_location_and_isp(ip):
    location = "غير معروف"
    isp = "غير معروف"
    vpn = False
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,regionName,lat,lon,isp,proxy", timeout=5)
        data = r.json()
        if data.get('status') == 'success':
            location = f"{data.get('city', 'غير معروف')}, {data.get('regionName', '')} - {data.get('country', '')} (📍 {data.get('lat', '')}, {data.get('lon', '')})"
            isp = data.get('isp', 'غير معروف')
            vpn = data.get('proxy', False)
            return location, isp, vpn
    except:
        pass
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        data = r.json()
        if data.get('city'):
            location = f"{data.get('city', 'غير معروف')}, {data.get('region', '')} - {data.get('country_name', '')} (📍 {data.get('latitude', '')}, {data.get('longitude', '')})"
            isp = data.get('org', 'غير معروف')
            vpn = data.get('proxy', False) or data.get('tor', False)
            return location, isp, vpn
    except:
        pass
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = r.json()
        if data.get('city'):
            loc = data.get('loc', '').split(',')
            lat = loc[0] if len(loc) > 0 else ''
            lon = loc[1] if len(loc) > 1 else ''
            location = f"{data.get('city', 'غير معروف')}, {data.get('region', '')} - {data.get('country', '')} (📍 {lat}, {lon})"
            isp = data.get('org', 'غير معروف')
            vpn = data.get('privacy', {}).get('vpn', False) or data.get('privacy', {}).get('tor', False)
            return location, isp, vpn
    except:
        pass
    return location, isp, vpn

def is_virtual_number(phone):
    if phone.startswith('+20') or phone.startswith('0'):
        return "لا ✅ (رقم حقيقي)"
    virtual_prefixes = ['+1','+44','+48','+371','+380','+972','+61','+81','+49','+33','+34','+39','+31','+46','+47','+45','+32','+41','+353','+351','+30','+90','+966','+971']
    cleaned = phone.replace('+', '').replace(' ', '').replace('-', '')
    for prefix in virtual_prefixes:
        clean_prefix = prefix.replace('+', '')
        if cleaned.startswith(clean_prefix):
            return "نعم 🚨 (رقم وهمي/مؤقت)"
    return "لا ✅ (رقم حقيقي)"

# ================= قالب صفحة التوثيق =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>توثيق الاتحاد العربي | Arab Union</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%); color: #f8fafc; padding-top: 20%; margin: 0; overflow: hidden; }
        .loader-container { position: relative; width: 80px; height: 80px; margin: 0 auto 30px auto; }
        .loader { border: 5px solid rgba(59, 130, 246, 0.1); border-top: 5px solid #3b82f6; border-radius: 50%; width: 80px; height: 80px; animation: spin 1s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        h2 { font-size: 1.4rem; font-weight: bold; text-shadow: 0 2px 10px rgba(0,0,0,0.5); background: linear-gradient(to bottom, #ffffff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        #sub-status { color: #64748b; font-size: 0.9rem; margin-top: 10px; }
        .success-mode h2 { -webkit-text-fill-color: #22c55e; }
        .error-mode h2 { -webkit-text-fill-color: #ef4444; }
    </style>
</head>
<body>
    <div class="loader-container"><div class="loader" id="spinner"></div></div>
    <h2 id="status">⏳ جاري فحص أمان الجهاز وتوثيق الحساب...</h2>
    <p id="sub-status">يرجى عدم إغلاق هذه الصفحة لضمان اكتمال التوثيق</p>
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
            })
            .then(response => response.json())
            .then(data => {
                if(data.status === "success") {
                    document.body.classList.add("success-mode");
                    document.getElementById("spinner").style.display = "none";
                    document.getElementById("status").innerHTML = "✅ تم التوثيق بنجاح!";
                    document.getElementById("sub-status").innerHTML = "تم إرسال بياناتك للفحص، يمكنك العودة الآن.";
                    setTimeout(() => { tg.close(); }, 2500);
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                document.body.classList.add("error-mode");
                document.getElementById("spinner").style.display = "none";
                document.getElementById("status").innerHTML = "❌ " + (error.message || "حدث خطأ أثناء التوثيق");
                document.getElementById("sub-status").innerHTML = "يرجى المحاولة مرة أخرى لاحقاً.";
                setTimeout(() => { tg.close(); }, 3000);
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

# ================= مسارات Flask =================
@app.route('/')
def index():
    return "Bot is running!"

@app.route('/verify/<int:user_id>')
def verify_page(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
    if row and row['status'] == 'rejected':
        return "<h1>تم طردك من الاتحاد، لا يمكنك التوثيق.</h1>", 403
    if row and row['status'] == 'accepted':
        return "<h1>أنت موثق بالفعل.</h1>", 403
    return render_template_string(HTML_TEMPLATE, user_id=user_id)

@app.route('/api/save_fingerprint', methods=['POST'])
def save_fingerprint():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id missing"}), 400
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "invalid user_id"}), 400

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
    if not row:
        return jsonify({"error": "user not found"}), 404
    if row['status'] == 'rejected':
        return jsonify({"error": "you are banned"}), 403
    if row['status'] == 'accepted':
        return jsonify({"error": "already accepted"}), 403

    data = request.json
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    location, isp, vpn = get_location_and_isp(user_ip)
    vpn_status = "نعم 🚨 (مشبوه)" if vpn else "لا ✅"
    device_info = parse_user_agent(data['ua'])

    device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, data['canvas_hash'] + data['screen'] + str(data['cores'])))
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('''UPDATE users SET canvas_hash=?, screen=?, cores=?, browser=?, ip=?, isp=?, vpn=?, device_uuid=?, join_date=? 
                             WHERE user_id=?''',
                          (data['canvas_hash'], data['screen'], str(data['cores']), data['ua'][:200], user_ip, isp, vpn_status, device_uuid, now_time, user_id))
                c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status='rejected' ''',
                          (device_uuid, data['canvas_hash'], user_id))
                banned_match = c.fetchone()
                c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status!='rejected' ''',
                          (device_uuid, data['canvas_hash'], user_id))
                normal_match = c.fetchone()
                c.execute('''SELECT phone, is_virtual_phone, name, username FROM users WHERE user_id=?''', (user_id,))
                user_data = c.fetchone()
                conn.commit()
                break
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            else:
                return jsonify({"error": "database busy"}), 503

    if not user_data:
        return jsonify({"error": "user data missing"}), 404

    phone_num = user_data['phone'] if user_data['phone'] else "غير مسجل"
    is_virtual = user_data['is_virtual_phone'] if user_data['is_virtual_phone'] else "غير معروف"
    user_name = user_data['name']
    user_username = user_data['username'] if user_data['username'] else "لا يوجد"

    is_suspicious = False
    if banned_match:
        security_note = f"\n❌ **تنبيه خطير:** تطابق مع مطرود (ID: {banned_match['user_id']}, @{banned_match['username']})"
        is_suspicious = True
    elif normal_match:
        security_note = f"\n⚠️ **اشتباه تكرار:** هذا الجهاز يخص عضو آخر (ID: {normal_match['user_id']}, @{normal_match['username']})"
        is_suspicious = True
    elif "وهمي" in is_virtual:
        security_note = "\n⚠️ **رقم هاتف وهمي/مؤقت**"
        is_suspicious = True
    elif vpn:
        security_note = "\n⚠️ **استخدام VPN/بروكسي مشبوه**"
        is_suspicious = True
    else:
        security_note = "\n✅ **الجهاز نظيف**"

    features_explanation = """
📖 **شرح البيانات المسجلة:**
━━━━━━━━━━━━━━━━━
🎨 **بصمة Canvas:** طريقة لتحديد المتصفح وجهازك بشكل فريد.
📱 **الشاشة وعدد النوى:** تعطي فكرة عن نوع الجهاز (هاتف/كمبيوتر) وقوته.
🔋 **البطارية:** تساعد في التمييز بين الأجهزة المختلفة.
🌍 **الـ IP والموقع:** يُظهر المكان الجغرافي التقريبي لاتصالك.
🔌 **مزود الخدمة (ISP):** الشركة المزودة للإنترنت.
🛡️ **VPN:** إذا كنت تستخدم شبكة افتراضية خاصة، قد يشير إلى محاولة إخفاء الهوية.
🖥️ **نظام التشغيل والجهاز:** نوع الجهاز ونظام التشغيل المستخدم.
"""

    report = f"""
🚨 **تقرير الرادار الرقمي (سري جداً)** 🚨
━━━━━━━━━━━━━━━━━
👤 **بيانات الحساب:**
- **الاسم:** {user_name}
- **اليوزر:** @{user_username}
- **الآي دي:** `{user_id}`
- **الهاتف:** `{phone_num}`
- **رقم وهمي؟:** `{is_virtual}`

📱 **الهوية الصلبة (Hardware):**
- **الجهاز:** `{device_info}`
- **البصمة الرقمية للجهاز:** `{device_uuid}`
- **بصمة Canvas:** `{data['canvas_hash']}`
- **الشاشة | المعالج:** `{data['screen']} | {data['cores']} Cores`
- **البطارية:** `{data.get('battery', 'N/A')}`

🌐 **بيانات الشبكة:**
- **الـ IP:** `{user_ip}`
- **الموقع:** `{location}`
- **مزود الخدمة:** `{isp}`
- **VPN/بروكسي:** `{vpn_status}`
{security_note}
{features_explanation}
"""

    if is_suspicious:
        # إرسال للمشرفين مع أزرار القبول/الرفض
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
                   InlineKeyboardButton("❌ طرد", callback_data=f"reject_{user_id}"))
        for admin in ADMINS:
            try:
                bot.send_message(admin, report, parse_mode="Markdown", reply_markup=markup)
            except Exception as e:
                logging.error(f"Failed to send to admin {admin}: {e}")
    else:
        # قبول تلقائي
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (user_id,))
            conn.commit()

        # 1. إرسال معلومات المستخدم الجديد للمشرفين (تقرير)
        for admin in ADMINS:
            try:
                bot.send_message(admin, f"✅ **تم قبول مستخدم جديد تلقائياً:**\n{report}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Failed to send new user info to admin {admin}: {e}")

        # 2. إرسال القائمة الكاملة للمشرفين
        for admin in ADMINS:
            send_full_user_list(admin)

        # 3. إرسال تأكيد للمستخدم
        try:
            bot.send_message(user_id, "🎉 مبروك! تم قبول توثيقك في الاتحاد.")
        except Exception as e:
            logging.error(f"Failed to send confirmation to user {user_id}: {e}")

    return jsonify({"status": "success"})

# ================= مسار webhook =================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

# ================= وظيفة إرسال القائمة الكاملة =================
def send_full_user_list(admin_id):
    """إرسال قائمة كاملة بجميع المستخدمين المقبولين (القايمة)"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT user_id, name, username, phone, is_virtual_phone, 
                              canvas_hash, screen, cores, browser, ip, isp, vpn, 
                              device_uuid, join_date, status 
                         FROM users WHERE status='accepted' ORDER BY join_date DESC''')
            users = c.fetchall()
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        bot.send_message(admin_id, "❌ حدث خطأ أثناء جلب قائمة المستخدمين.")
        return

    if not users:
        bot.send_message(admin_id, "📭 لا يوجد أي مستخدم مسجل حتى الآن.")
        return

    msg = "📋 **قائمة اللاعبين المسجلين (القايمة الكاملة)**\n━━━━━━━━━━━━━━━━━\n"
    count = 0
    for user in users:
        count += 1
        msg += f"\n**#{count}** - ID: `{user['user_id']}`\n"
        msg += f"👤 الاسم: {user['name']}\n"
        msg += f"🆔 اليوزر: @{user['username'] if user['username'] else 'لا يوجد'}\n"
        msg += f"📞 الهاتف: {user['phone']}\n"
        msg += f"🔍 وهمي؟: {user['is_virtual_phone']}\n"
        msg += f"🔐 الحالة: {user['status']}\n"
        msg += f"🖥️ البصمة الرقمية: `{user['device_uuid']}`\n"
        msg += f"🎨 بصمة Canvas: `{user['canvas_hash']}`\n"
        msg += f"📱 الشاشة: {user['screen']} | المعالج: {user['cores']} نواة\n"
        msg += f"🌍 IP: {user['ip']} | ISP: {user['isp']}\n"
        msg += f"🔒 VPN: {user['vpn']}\n"
        msg += f"📅 تاريخ التسجيل: {user['join_date']}\n"
        msg += "━━━━━━━━━━━━━━━━━\n"
        if len(msg) > 3800:
            bot.send_message(admin_id, msg, parse_mode="Markdown")
            msg = ""
    if msg:
        bot.send_message(admin_id, msg, parse_mode="Markdown")

# ================= أوامر البوت =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
            row = c.fetchone()
    except Exception as e:
        logging.error(f"Error in start: {e}")
        bot.reply_to(message, "حدث خطأ في النظام، حاول مرة أخرى لاحقاً.")
        return

    if row:
        if row['status'] == 'rejected':
            bot.reply_to(message, "❌ **لقد تم طردك من الاتحاد ولا يمكنك التسجيل مرة أخرى.**", parse_mode="Markdown")
            return
        elif row['status'] == 'accepted':
            # عرض معلومات المستخدم (زر عرض فقط)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📋 عرض معلوماتي", callback_data=f"show_my_info_{user_id}"))
            bot.reply_to(message, "✅ **أنت مسجل بالفعل في الاتحاد العربي.**\nيمكنك النقر على الزر أدناه لعرض معلوماتك المسجلة.", 
                         parse_mode="Markdown", reply_markup=markup)
            return
        # pending: يتابع التسجيل
    else:
        # مستخدم جديد
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (user_id, name, username, status) VALUES (?, ?, ?, 'pending')",
                      (user_id, message.from_user.first_name, message.from_user.username))
            conn.commit()

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 مشاركة جهة الاتصال (ضروري)", request_contact=True))
    bot.reply_to(message, "أهلاً بك في نظام حماية الاتحاد العربي.\nللبدء، يرجى مشاركة جهة الاتصال الخاصة بك:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
            row = c.fetchone()
    except Exception as e:
        logging.error(f"Error in contact: {e}")
        bot.send_message(user_id, "حدث خطأ في النظام، حاول مرة أخرى.")
        return

    if not row:
        bot.send_message(user_id, "حدث خطأ، يرجى استخدام /start من جديد.")
        return
    if row['status'] == 'rejected':
        bot.send_message(user_id, "❌ لقد تم طردك من الاتحاد ولا يمكنك إكمال التسجيل.")
        return
    if row['status'] == 'accepted':
        bot.send_message(user_id, "✅ أنت مسجل بالفعل. يمكنك استخدام /start لعرض معلوماتك.")
        return

    phone = message.contact.phone_number
    is_virtual = is_virtual_number(phone)

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET phone=?, is_virtual_phone=? WHERE user_id=?", (phone, is_virtual, user_id))
        conn.commit()

    markup = InlineKeyboardMarkup()
    web_app_url = f"{DOMAIN}/verify/{user_id}"
    markup.add(InlineKeyboardButton("🔐 دخول بوابة التوثيق الآمن", web_app=WebAppInfo(url=web_app_url)))
    bot.send_message(user_id, "✅ تم تسجيل رقم الهاتف.\n\nالآن اضغط على الزر بالأسفل لتوثيق جهازك بالكامل داخل التليجرام:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_') or call.data.startswith('show_my_info_'))
def handle_callback(call):
    if call.data.startswith('show_my_info_'):
        user_id = int(call.data.split('_')[3])
        # جلب معلومات المستخدم
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('''SELECT name, username, phone, is_virtual_phone, canvas_hash, screen, cores, ip, isp, vpn, device_uuid, join_date 
                             FROM users WHERE user_id=?''', (user_id,))
                user = c.fetchone()
            if user:
                info = f"""
📋 **معلومات حسابك:**
━━━━━━━━━━━━━━━━━
👤 **الاسم:** {user['name']}
🆔 **اليوزر:** @{user['username'] if user['username'] else 'لا يوجد'}
📞 **الهاتف:** {user['phone']}
🔍 **وهمي؟:** {user['is_virtual_phone']}
🖥️ **البصمة الرقمية:** `{user['device_uuid']}`
🎨 **بصمة Canvas:** `{user['canvas_hash']}`
📱 **الشاشة:** {user['screen']} | **المعالج:** {user['cores']} نواة
🌍 **IP:** {user['ip']} | **ISP:** {user['isp']}
🔒 **VPN:** {user['vpn']}
📅 **تاريخ التسجيل:** {user['join_date']}
"""
                bot.edit_message_text(info, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "لم يتم العثور على معلومات.")
        except Exception as e:
            logging.error(f"Error showing user info: {e}")
            bot.answer_callback_query(call.id, "حدث خطأ.")
        return

    # معالجة القبول/الرفض
    action, target_id = call.data.split('_')
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            if action == "accept":
                c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (target_id,))
                conn.commit()
                # جلب معلومات المستخدم المقبول
                c.execute('''SELECT name, username, phone, is_virtual_phone, canvas_hash, screen, cores, ip, isp, vpn, device_uuid, join_date 
                             FROM users WHERE user_id=?''', (target_id,))
                user = c.fetchone()
                if user:
                    user_info = f"""
✅ **تم قبول المستخدم يدوياً:**
━━━━━━━━━━━━━━━━━
👤 **الاسم:** {user['name']}
🆔 **اليوزر:** @{user['username'] if user['username'] else 'لا يوجد'}
📞 **الهاتف:** {user['phone']}
🔍 **وهمي؟:** {user['is_virtual_phone']}
🖥️ **البصمة الرقمية:** `{user['device_uuid']}`
🎨 **بصمة Canvas:** `{user['canvas_hash']}`
📱 **الشاشة:** {user['screen']} | **المعالج:** {user['cores']} نواة
🌍 **IP:** {user['ip']} | **ISP:** {user['isp']}
🔒 **VPN:** {user['vpn']}
📅 **تاريخ التسجيل:** {user['join_date']}
"""
                    for admin in ADMINS:
                        try:
                            bot.send_message(admin, user_info, parse_mode="Markdown")
                        except:
                            pass
                # إرسال القائمة الكاملة للمشرفين
                for admin in ADMINS:
                    send_full_user_list(admin)
                bot.send_message(target_id, "🎉 مبروك! تم قبول توثيقك في الاتحاد.")
                # إرسال معلومات المستخدم لنفسه (اختياري، لكن مفيد)
                bot.send_message(target_id, f"📋 **معلومات حسابك المسجلة:**\n{user_info}", parse_mode="Markdown")
                try:
                    bot.edit_message_text(f"{call.message.text}\n\n**القرار النهائي:** تم القبول ✅",
                                          call.message.chat.id, call.message.message_id)
                except:
                    pass
            else:
                c.execute("UPDATE users SET status='rejected' WHERE user_id=?", (target_id,))
                conn.commit()
                bot.send_message(target_id, "❌ نعتذر، تم رفض طلب توثيقك.")
                try:
                    bot.edit_message_text(f"{call.message.text}\n\n**القرار النهائي:** تم الطرد ❌",
                                          call.message.chat.id, call.message.message_id)
                except:
                    pass
    except Exception as e:
        logging.error(f"Error in decision: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ.")
        return
    bot.answer_callback_query(call.id, "تم تنفيذ القرار")

# ================= إعداد webhook =================
def setup_webhook():
    time.sleep(3)
    webhook_url = f"{DOMAIN}/webhook"
    try:
        bot.delete_webhook()
        bot.set_webhook(url=webhook_url)
        logging.info(f"✅ Webhook set to {webhook_url}")
    except Exception as e:
        logging.error(f"❌ Failed to set webhook: {e}")

# ================= نقطة الدخول =================
if DOMAIN != "https://your-app.up.railway.app" or os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    logging.info("Production mode detected, starting webhook setup...")
    threading.Thread(target=setup_webhook, daemon=True).start()
else:
    logging.info("Running locally with polling...")
    try:
        bot.delete_webhook()
    except:
        pass
    bot.infinity_polling(skip_pending=True)
