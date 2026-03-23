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
from contextlib import contextmanager

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

# ================= قفل قاعدة البيانات =================
db_lock = threading.Lock()
DB_PATH = 'union_radar.db'

@contextmanager
def get_db_connection():
    """مدير سياق لفتح وإغلاق اتصال قاعدة البيانات مع قفل"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

def init_db():
    """إنشاء الجداول إذا لم تكن موجودة"""
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

# ================= وظائف مساعدة للكشف عن الأرقام الوهمية =================
def is_virtual_number(phone):
    """تحديد ما إذا كان الرقم وهمياً بناءً على البادئات المعروفة"""
    virtual_prefixes = [
        '1', '+1', '44', '+44', '48', '+48', '371', '+371', '380', '+380',
        '2', '+2', '3', '+3', '4', '+4', '5', '+5', '6', '+6', '7', '+7', '8', '+8', '9', '+9',
        '0', '+0', '11', '22', '33', '44', '55', '66', '77', '88', '99',
        '111', '222', '333', '444', '555', '666', '777', '888', '999'
    ]
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

    # استخدام القفل وتكرار المحاولة في حالة القفل
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                # تحديث بيانات المستخدم
                c.execute('''UPDATE users SET canvas_hash=?, screen=?, cores=?, browser=?, ip=?, isp=?, vpn=?, device_uuid=?, join_date=? 
                             WHERE user_id=?''',
                          (data['canvas_hash'], data['screen'], str(data['cores']), data['ua'][:100], user_ip, isp_name, vpn_status, device_uuid, now_time, user_id))
                
                # البحث عن تطابقات
                c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status='rejected' ''', 
                          (device_uuid, data['canvas_hash'], user_id))
                banned_match = c.fetchone()
                
                c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status!='rejected' ''', 
                          (device_uuid, data['canvas_hash'], user_id))
                normal_match = c.fetchone()
                
                c.execute('''SELECT phone, is_virtual_phone FROM users WHERE user_id=?''', (user_id,))
                phone_data = c.fetchone()
                conn.commit()
                break  # نجحت العملية
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # تأخير متزايد
                continue
            else:
                logging.error(f"Database error after {attempt+1} attempts: {e}")
                return jsonify({"error": "database busy, try again"}), 503

    # بناء التقرير
    phone_num = phone_data['phone'] if phone_data else "غير مسجل"
    is_virtual = phone_data['is_virtual_phone'] if phone_data else "غير معروف"

    if banned_match:
        security_note = f"\n❌ **تنبيه خطير:** تطابق مع مطرود (ID: {banned_match['user_id']}, @{banned_match['username']})"
    elif normal_match:
        security_note = f"\n⚠️ **اشتباه تكرار:** هذا الجهاز يخص عضو آخر (ID: {normal_match['user_id']}, @{normal_match['username']})"
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

# ================= وظيفة لإرسال قائمة جميع المستخدمين =================
def send_full_user_list(admin_id):
    """إرسال قائمة كاملة بجميع المستخدمين المسجلين إلى المشرف"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT user_id, name, username, phone, is_virtual_phone, 
                              canvas_hash, screen, cores, browser, ip, isp, vpn, 
                              device_uuid, join_date, status 
                         FROM users ORDER BY join_date DESC''')
            users = c.fetchall()
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        bot.send_message(admin_id, "❌ حدث خطأ أثناء جلب قائمة المستخدمين.")
        return

    if not users:
        bot.send_message(admin_id, "📭 لا يوجد أي مستخدم مسجل حتى الآن.")
        return

    # تقسيم القائمة إلى أجزاء
    msg = "📋 **قائمة المستخدمين المسجلين (كامل التفاصيل)**\n━━━━━━━━━━━━━━━━━\n"
    count = 0
    for user in users:
        count += 1
        msg += f"\n**#{count}** - ID: `{user['user_id']}`\n"
        msg += f"👤 الاسم: {user['name']}\n"
        msg += f"🆔 اليوزر: @{user['username'] if user['username'] else 'لا يوجد'}\n"
        msg += f"📞 الهاتف: {user['phone']}\n"
        msg += f"🔍 وهمي؟: {user['is_virtual_phone']}\n"
        msg += f"🔐 الحالة: {user['status']}\n"
        msg += f"🖥️ الجهاز (UUID): `{user['device_uuid']}`\n"
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
    user = message.from_user
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, name, username, status) VALUES (?, ?, ?, 'pending')", 
                      (user.id, user.first_name, user.username))
            conn.commit()
    except Exception as e:
        logging.error(f"Error in start: {e}")
        bot.reply_to(message, "حدث خطأ في النظام، حاول مرة أخرى لاحقاً.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 مشاركة جهة الاتصال (ضروري)", request_contact=True))
    bot.reply_to(message, "أهلاً بك في نظام حماية الاتحاد العربي.\nللبدء، يرجى مشاركة جهة الاتصال الخاصة بك:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    phone = message.contact.phone_number
    is_virtual = is_virtual_number(phone)
    
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET phone=?, is_virtual_phone=? WHERE user_id=?", (phone, is_virtual, user_id))
            conn.commit()
    except Exception as e:
        logging.error(f"Error in contact: {e}")
        bot.send_message(user_id, "حدث خطأ في حفظ الرقم، حاول مرة أخرى.")
        return
    
    markup = InlineKeyboardMarkup()
    web_app_url = f"{DOMAIN}/verify/{user_id}"
    markup.add(InlineKeyboardButton("🔐 دخول بوابة التوثيق الآمن", web_app=WebAppInfo(url=web_app_url)))
    
    bot.send_message(user_id, "✅ تم تسجيل رقم الهاتف.\n\nالآن اضغط على الزر بالأسفل لتوثيق جهازك بالكامل داخل التليجرام:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
def admin_decision(call):
    action, target_id = call.data.split('_')
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            if action == "accept":
                c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (target_id,))
                conn.commit()
                bot.send_message(target_id, "🎉 مبروك! تم قبول توثيقك في الاتحاد.")
                for admin in ADMINS:
                    send_full_user_list(admin)
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
        bot.answer_callback_query(call.id, "حدث خطأ أثناء تنفيذ القرار.")
        return

    bot.answer_callback_query(call.id, "تم تنفيذ القرار")

# ================= إعداد webhook (للإنتاج فقط) =================
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
