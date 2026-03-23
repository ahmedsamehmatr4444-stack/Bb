from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import threading
import requests
import uuid
import os
import datetime

# ================= الإعدادات الأساسية (التي يجب تعديلها) =================
BOT_TOKEN = "8764397517:AAHNtkUYi15yT8IrkDaK954PBQtgywJ5Mfg"
ADMINS = [18147516847, 1358013723]  # ضع الآي دي الخاص بك وبشركائك هنا
DOMAIN = "bb-production-7996.up.railway.app" # ضع رابط الاستضافة النهائي هنا

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= 1. طبقة قاعدة البيانات الشاملة =================
def init_db():
    conn = sqlite3.connect('union_radar.db', check_same_thread=False)
    c = conn.cursor()
    # إنشاء جدول متكامل يضم جميع البيانات التقنية والشخصية
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
            // سحب تفاصيل الشاشة والمعالج
            let fp = {
                screen: window.screen.width + "x" + window.screen.height,
                cores: navigator.hardwareConcurrency || "Unknown",
                lang: navigator.language,
                ua: navigator.userAgent,
                canvas_hash: getCanvasHash()
            };
            
            // محاولة سحب تفاصيل البطارية (اللحظية)
            try {
                if (navigator.getBattery) {
                    let bat = await navigator.getBattery();
                    fp.battery = Math.round(bat.level * 100) + "% " + (bat.charging ? "⚡يتم الشحن" : "🔋");
                } else { fp.battery = "غير مدعوم"; }
            } catch(e) { fp.battery = "مجهول"; }

            // إرسال البيانات فوراً إلى السيرفر
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

        // كود معقد لإنتاج بصمة كارت الشاشة (Canvas Hash)
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
    
    # الاعتماد على هيدرز الاستضافة لمعرفة الـ IP الحقيقي
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    
    # 3. طبقة فحص الشبكة (VPN & ISP) عبر API مجاني
    vpn_status = "لا"
    isp_name = "غير معروف"
    try:
        ip_check = requests.get(f"http://ip-api.com/json/{user_ip}?fields=proxy,isp,status,country", timeout=3).json()
        if ip_check.get('status') == 'success':
            isp_name = f"{ip_check.get('isp')} ({ip_check.get('country')})"
            vpn_status = "نعم 🚨 (مشبوه)" if ip_check.get('proxy') else "لا ✅"
    except:
        pass

    # توليد رقم تسلسلي ثابت (UUID) للجهاز بناءً على الهاردوير
    device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, data['canvas_hash'] + data['screen'] + str(data['cores'])))
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute('''UPDATE users SET canvas_hash=?, screen=?, cores=?, browser=?, ip=?, isp=?, vpn=?, device_uuid=?, join_date=? 
                 WHERE user_id=?''',
              (data['canvas_hash'], data['screen'], str(data['cores']), data['ua'][:100], user_ip, isp_name, vpn_status, device_uuid, now_time, user_id))
    
    # 4. طبقة التحليل الجنائي (البحث عن تطابق سابق)
    c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status='rejected' ''', 
              (device_uuid, data['canvas_hash'], user_id))
    banned_match = c.fetchone()
    
    c.execute('''SELECT user_id, username FROM users WHERE (device_uuid=? OR canvas_hash=?) AND user_id!=? AND status!='rejected' ''', 
              (device_uuid, data['canvas_hash'], user_id))
    normal_match = c.fetchone()
    
    # جلب رقم الهاتف لفحصه في التقرير
    c.execute('''SELECT phone, is_virtual_phone FROM users WHERE user_id=?''', (user_id,))
    phone_data = c.fetchone()
    conn.close()

    phone_num = phone_data[0] if phone_data else "غير مسجل"
    is_virtual = phone_data[1] if phone_data else "غير معروف"

    # صياغة التقرير الاستخباراتي
    match_alert = ""
    if banned_match:
        match_alert = f"\n❌ **تنبيه خطير (تطابق 100%):** هذا الجهاز يخص العضو المطرود [@{banned_match[1]}] (ID: {banned_match[0]})"
    elif normal_match:
        match_alert = f"\n⚠️ **اشتباه تكرار حساب:** هذا الجهاز يخص عضو آخر مسجل بالفعل [@{normal_match[1]}] (ID: {normal_match[0]})"
    else:
        match_alert = "\n✅ **الجهاز نظيف:** لا يوجد تطابق مع أي حساب آخر."

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

{match_alert}
"""
    # إرسال التقرير للإدارة مع أزرار التحكم
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ قبول (توثيق)", callback_data=f"accept_{user_id}"),
               InlineKeyboardButton("❌ طرد (اشتباه/وهمي)", callback_data=f"reject_{user_id}"))
    
    for admin in ADMINS:
        try:
            bot.send_message(admin, report, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Error sending to admin: {e}")

    return jsonify({"status": "success"})


# ================= 5. أوامر البوت والتفاعل =================
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
    bot.reply_to(message, "أهلاً بك في نظام حماية الاتحاد.\nللبدء في التوثيق، يرجى الضغط على زر مشاركة جهة الاتصال بالأسفل:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    phone = message.contact.phone_number
    
    # فحص مبدئي للأرقام الوهمية (يبدأ بـ +1، +44، وغيرها من الأرقام الشائعة للتطبيقات)
    virtual_prefixes = ['1', '+1', '44', '+44', '48', '+48', '371', '+371', '380', '+380']
    is_virtual = "نعم 🚨" if any(phone.startswith(p) for p in virtual_prefixes) else "لا ✅"
    
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    c.execute("UPDATE users SET phone=?, is_virtual_phone=? WHERE user_id=?", (phone, is_virtual, user_id))
    conn.commit()
    conn.close()

    bot.send_message(user_id, f"✅ تم تسجيل رقمك المبدئي.\n\nالخطوة الأخيرة: اضغط على الرابط التالي لتوثيق أمان جهازك (الرابط آمن تماماً):\n{DOMAIN}/verify/{user_id}", 
                     reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
def admin_decision(call):
    action, target_id = call.data.split('_')
    target_id = int(target_id)
    
    conn = sqlite3.connect('union_radar.db')
    c = conn.cursor()
    
    if action == "accept":
        c.execute("UPDATE users SET status='accepted' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "🎉 **تم توثيق حسابك وجهازك بنجاح.**\nأهلاً بك رسمياً في الاتحاد العربي!", parse_mode="Markdown")
        bot.edit_message_text(f"{call.message.text}\n\n**القرار النهائي:** تم القبول ✅", call.message.chat.id, call.message.message_id)
    else:
        c.execute("UPDATE users SET status='rejected' WHERE user_id=?", (target_id,))
        bot.send_message(target_id, "❌ **عذراً، تم رفض طلبك.**\nالنظام رصد اشتباه (حساب وهمي أو تكرار استخدام جهاز لحسابات مختلفة).", parse_mode="Markdown")
        bot.edit_message_text(f"{call.message.text}\n\n**القرار النهائي:** تم الطرد ❌", call.message.chat.id, call.message.message_id)
    
    conn.commit()
    conn.close()

# ================= 6. التشغيل المزدوج (متوافق مع الاستضافات) =================
def run_flask():
    # os.environ.get('PORT', 5000) ضروري جداً لكي يعمل على Railway
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    # تشغيل خادم الويب في مسار منفصل
    threading.Thread(target=run_flask).start()
    print("🌐 خادم الرادار السري يعمل...")
    
    # تشغيل بوت التيليجرام
    print("🤖 بوت الاتحاد يعمل الآن...")
    bot.infinity_polling()
