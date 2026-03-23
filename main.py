import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import uuid
import os
import datetime

# ================= الإعدادات الأساسية =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8764397517:AAHNtkUYi15yT8IrkDaK954PBQtgywJ5Mfg")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "18147516847,1358013723").split(",") if x.strip().isdigit()]
DOMAIN = os.environ.get("DOMAIN", "https://bb-production-7996.up.railway.app")
USE_WEBHOOK = os.environ.get("USE_WEBHOOK", "true").lower() == "true"  # استخدم webhook في الإنتاج

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= 1. قاعدة البيانات =================
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

# ================= 2. قالب صفحة الويب =================
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
            }).then(response => response.json())
              .then(data => {
                document.body.classList.add("success-mode");
                document.getElementById("spinner").style.display = "none";
                document.getElementById("status").innerHTML = "✅ تم التوثيق بنجاح!";
                document.getElementById("sub-status").innerHTML = "تم إرسال بياناتك للفحص، يمكنك العودة الآن.";
                setTimeout(() => { tg.close(); }, 2500);
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

# ================= 3. مسارات Flask =================
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
        security_note = "\n❌ **تنبيه خطير:** تطابق مع مطرود"
    elif normal_match:
        security_note = "\n⚠️ **اشتباه تكرار**"
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
            print(f"Failed to send to admin {admin}: {e}")
    return jsonify({"status": "success"})

# ================= 4. مسار webhook للبوت =================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

# ================= 5. إعداد webhook عند بدء التشغيل =================
def set_webhook():
    if USE_WEBHOOK:
        webhook_url = f"{DOMAIN}/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to {webhook_url}")
    else:
        # عند التشغيل المحلي باستخدام polling
        bot.remove_webhook()
        threading.Thread(target=bot.infinity_polling, kwargs={'skip_pending': True}, daemon=True).start()
        print("Polling started (local mode)")

# ================= 6. تشغيل التطبيق =================
if __name__ == '__main__':
    # للتشغيل المحلي (python app.py)
    port = int(os.environ.get('PORT', 5000))
    set_webhook()  # ستبدأ polling إذا كان USE_WEBHOOK=False
    app.run(host='0.0.0.0', port=port)
else:
    # عند التشغيل عبر gunicorn، نضبط webhook قبل بدء السيرفر
    set_webhook()
