import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
from datetime import datetime

# تمكين التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# إنشاء قاعدة بيانات SQLite
DB_NAME = "halawan_bot.db"

# === إعدادات المشرف ===
# ضع معرفات المستخدمين للمشرفين (يمكنك إضافة أكثر من واحد)
ADMIN_USER_IDS = [7014934145]  # استبدل هذا بمعرفك الحقيقي على تيليجرام
# للحصول على معرفك: أرسل رسالة للبوت @userinfobot على تيليجرام


def init_db():
    """تهيئة قاعدة البيانات مع التحقق من الهيكل"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # إنشاء جدول القائمة الرئيسي إذا لم يكن موجوداً
    c.execute('''CREATE TABLE IF NOT EXISTS halawan_list
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  occasion TEXT NOT NULL,
                  added_by INTEGER,
                  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # إنشاء جدول للمحذوفات
    c.execute('''CREATE TABLE IF NOT EXISTS deleted_halawan
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  original_id INTEGER,
                  user_id TEXT NOT NULL,
                  occasion TEXT NOT NULL,
                  added_by INTEGER,
                  deleted_by INTEGER,
                  deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  added_at TIMESTAMP)''')
    
    # التحقق من وجود جميع الأعمدة في الجدول الرئيسي
    c.execute("PRAGMA table_info(halawan_list)")
    columns = [column[1] for column in c.fetchall()]
    
    # إضافة العمود added_by إذا كان مفقوداً
    if 'added_by' not in columns:
        try:
            c.execute("ALTER TABLE halawan_list ADD COLUMN added_by INTEGER")
            logging.info("تم إضافة عمود added_by إلى الجدول")
        except sqlite3.OperationalError as e:
            logging.error(f"خطأ في إضافة العمود: {e}")
    
    # إضافة العمود added_at إذا كان مفقوداً
    if 'added_at' not in columns:
        try:
            c.execute("ALTER TABLE halawan_list ADD COLUMN added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            logging.info("تم إضافة عمود added_at إلى الجدول")
        except sqlite3.OperationalError as e:
            logging.error(f"خطأ في إضافة العمود: {e}")
    
    conn.commit()
    conn.close()
    logging.info("تم تهيئة قاعدة البيانات")

# دالة للتحقق من صلاحيات المشرف
def is_admin(user_id: int) -> bool:
    """تحقق إذا كان المستخدم مشرفاً"""
    return user_id in ADMIN_USER_IDS

# الأمر: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        welcome_text = """
🎉 **مرحباً يا مشرف!** 🎉

**الأوامر المتاحة لك:**
➕ /add معرف_الشخص المناسبة - لإضافة شخص ومناسبة
📋 /list - عرض القائمة الحالية
🗑️ /remove رقم_السجل - حذف شخص من القائمة
📜 /deleted - عرض القائمة المحذوفة
🔄 /restore رقم_السجل - استعادة محذوف
🗑️ /clear_deleted - مسح جميع المحذوفات
🆔 /myid - عرض معرفك
👑 /admins - عرض المشرفين
ℹ️ /help - عرض المساعدة
"""
    else:
        welcome_text = """
🎉 **مرحباً!** 🎉

**بوت قائمة الحلوان**

📋 /list - لعرض قائمة الحلوان
🆔 /myid - لعرض معرفك
ℹ️ /help - لعرض التعليمات

**ملاحظة:** فقط المشرفون يمكنهم إضافة أو حذف من القائمة
"""
    
    await update.message.reply_text(welcome_text)

# الأمر: /myid
async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "لا يوجد"
    
    message = f"🆔 **معرفك:** `{user_id}`\n"
    message += f"👤 **اسم المستخدم:** @{username}\n"
    
    if is_admin(user_id):
        message += "👑 **صلاحياتك:** مشرف ✅"
    else:
        message += "👤 **صلاحياتك:** مستخدم عادي"
    
    await update.message.reply_text(message)

# الأمر: /add
async def add_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات المشرف
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ **غير مصرح لك!**\n"
            "فقط المشرفون يمكنهم إضافة أشخاص إلى القائمة."
        )
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ **صيغة خاطئة!**\n"
            "استخدم: /add معرف_الشخص المناسبة\n"
            "مثال: /add @username عيد ميلاد"
        )
        return
    
    user_to_add = context.args[0]
    occasion = ' '.join(context.args[1:])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO halawan_list (user_id, occasion, added_by) VALUES (?, ?, ?)", 
              (user_to_add, occasion, user_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **تمت الإضافة بنجاح!**\n\n"
        f"👤 **الشخص:** {user_to_add}\n"
        f"🎉 **المناسبة:** {occasion}"
    )

# الأمر: /list
async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM halawan_list ORDER BY id")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await update.message.reply_text("📭 **القائمة فارغة حالياً**")
        return
    
    message = "📋 **قائمة الحلوان الحالية**:\n\n"
    for row in rows:
        # row[0] = id, row[1] = user_id, row[2] = occasion, row[3] = added_by, row[4] = added_at
        message += f"🆔 **{row[0]}**: {row[1]} - {row[2]}\n"
    
    message += f"\n📊 **الإجمالي:** {len(rows)} شخص(اً)"
    await update.message.reply_text(message)

# الأمر: /remove
async def remove_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات المشرف
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ **غير مصرح لك!**\n"
            "فقط المشرفون يمكنهم حذف أشخاص من القائمة."
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ **يرجى تحديد رقم السجل!**\n"
            "استخدم: /remove رقم_السجل\n"
            "مثال: /remove 3\n"
            "لرؤية الأرقام استخدم /list"
        )
        return
    
    try:
        record_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ **المعرف يجب أن يكون رقماً!**")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # الحصول على البيانات قبل الحذف
    c.execute("SELECT * FROM halawan_list WHERE id = ?", (record_id,))
    row = c.fetchone()
    
    if not row:
        await update.message.reply_text("⚠️ **هذا السجل غير موجود!**")
        conn.close()
        return
    
    # حفظ البيانات في جدول المحذوفات أولاً
    c.execute("""INSERT INTO deleted_halawan 
                 (original_id, user_id, occasion, added_by, deleted_by, added_at) 
                 VALUES (?, ?, ?, ?, ?, ?)""", 
              (row[0], row[1], row[2], row[3], user_id, row[4]))
    
    # حذف السجل من الجدول الرئيسي
    c.execute("DELETE FROM halawan_list WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"🗑️ **تم الحذف بنجاح!**\n\n"
        f"✅ تم حذف السجل رقم **{record_id}**\n"
        f"👤 الشخص: {row[1]}\n"
        f"🎉 المناسبة: {row[2]}\n"
    )

# الأمر: /deleted - عرض القائمة المحذوفة
async def show_deleted_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات المشرف
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ **غير مصرح لك!**\n"
            "فقط المشرفون يمكنهم عرض القائمة المحذوفة."
        )
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جلب جميع المحذوفات مرتبة من الأحدث إلى الأقدم
    c.execute("SELECT * FROM deleted_halawan ORDER BY deleted_at DESC")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await update.message.reply_text("🗑️ **لا توجد سجلات محذوفة حالياً**")
        return
    
    message = "🗑️ **قائمة المحذوفات (من الأحدث إلى الأقدم)**:\n\n"
    
    for row in rows:
        # row[0] = id, row[1] = original_id, row[2] = user_id, row[3] = occasion, 
        # row[4] = added_by, row[5] = deleted_by, row[6] = deleted_at, row[7] = added_at
        
        deleted_date = row[6]
        if deleted_date:
            try:
                # تحويل التوقيت إلى تنسيق مقروء
                if isinstance(deleted_date, str):
                    date_obj = datetime.strptime(deleted_date, "%Y-%m-%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%Y/%m/%d %H:%M")
                else:
                    formatted_date = str(deleted_date)[:16].replace('-', '/')
            except:
                formatted_date = str(deleted_date)[:16]
        else:
            formatted_date = "غير معروف"
        
        added_date = row[7]
        if added_date:
            try:
                if isinstance(added_date, str):
                    date_obj = datetime.strptime(added_date, "%Y-%m-%d %H:%M:%S")
                    added_formatted = date_obj.strftime("%Y/%m/%d")
                else:
                    added_formatted = str(added_date)[:10].replace('-', '/')
            except:
                added_formatted = str(added_date)[:10]
        else:
            added_formatted = "غير معروف"
        
        message += f"🔹 **رقم الأرشيف:** {row[0]}\n"
        message += f"   📌 **الرقم الأصلي:** {row[1]}\n"
        message += f"   👤 **الشخص:** {row[2]}\n"
        message += f"   🎉 **المناسبة:** {row[3]}\n"
        message += f"   📅 **تاريخ الإضافة:** {added_formatted}\n"
        message += f"   ⏰ **تاريخ الحذف:** {formatted_date}\n"
        message += "   " + "─" * 18 + "\n"
    
    # تقسيم الرسالة إذا كانت طويلة
    if len(message) > 4000:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(message)

# الأمر: /restore - استعادة سجل محذوف
async def restore_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات المشرف
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ **غير مصرح لك!**\n"
            "فقط المشرفون يمكنهم استعادة السجلات المحذوفة."
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ **يرجى تحديد رقم الأرشيف!**\n"
            "استخدم: /restore رقم_الأرشيف\n"
            "مثال: /restore 1\n"
            "لرؤية الأرشيف استخدم /deleted"
        )
        return
    
    try:
        deleted_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ **رقم الأرشيف يجب أن يكون رقماً!**")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # البحث عن السجل في الأرشيف
    c.execute("SELECT * FROM deleted_halawan WHERE id = ?", (deleted_id,))
    deleted_row = c.fetchone()
    
    if not deleted_row:
        await update.message.reply_text("⚠️ **هذا السجل غير موجود في الأرشيف!**")
        conn.close()
        return
    
    # استعادة السجل إلى الجدول الرئيسي
    try:
        c.execute("""INSERT INTO halawan_list (user_id, occasion, added_by, added_at) 
                     VALUES (?, ?, ?, ?)""", 
                  (deleted_row[2], deleted_row[3], deleted_row[4], deleted_row[7]))
        
        # حذف السجل من الأرشيف
        c.execute("DELETE FROM deleted_halawan WHERE id = ?", (deleted_id,))
        
        conn.commit()
        
        await update.message.reply_text(
            f"🔄 **تم الاستعادة بنجاح!**\n\n"
            f"✅ تم استعادة السجل رقم **{deleted_id}** من الأرشيف\n"
            f"👤 الشخص: {deleted_row[2]}\n"
            f"🎉 المناسبة: {deleted_row[3]}\n"
            f"📝 تمت إضافته مرة أخرى إلى القائمة الرئيسية"
        )
        
    except sqlite3.Error as e:
        await update.message.reply_text(f"⚠️ **حدث خطأ أثناء الاستعادة:** {e}")
    
    finally:
        conn.close()

# الأمر: /clear_deleted - مسح جميع المحذوفات
async def clear_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات المشرف
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ **غير مصرح لك!**\n"
            "فقط المشرفون يمكنهم مسح الأرشيف."
        )
        return
    
    # طلب تأكيد
    if not context.args or context.args[0].lower() != "confirm":
        await update.message.reply_text(
            "⚠️ **تحذير!**\n\n"
            "أنت على وشك مسح **جميع السجلات المحذوفة** بشكل نهائي.\n"
            "هذا الإجراء لا يمكن التراجع عنه.\n\n"
            "لتأكيد المسح، استخدم:\n"
            "`/clear_deleted confirm`"
        )
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # حساب عدد السجلات قبل الحذف
    c.execute("SELECT COUNT(*) FROM deleted_halawan")
    count = c.fetchone()[0]
    
    if count == 0:
        await update.message.reply_text("🗑️ **الأرشيف فارغ بالفعل**")
        conn.close()
        return
    
    # حذف جميع السجلات
    c.execute("DELETE FROM deleted_halawan")
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"🗑️ **تم مسح الأرشيف بنجاح!**\n\n"
        f"✅ تم حذف **{count}** سجل(اً) نهائياً من الأرشيف\n"
        f"⚠️ لا يمكن استعادة هذه السجلات مرة أخرى"
    )

# الأمر: /admins
async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ **غير مصرح لك!**\n"
            "هذا الأمر للمشرفين فقط."
        )
        return
    
    message = "👑 **قائمة المشرفين:**\n\n"
    for admin_id in ADMIN_USER_IDS:
        message += f"🆔 `{admin_id}`\n"
    
    message += f"\n👥 **عدد المشرفين:** {len(ADMIN_USER_IDS)}"
    await update.message.reply_text(message)

# الأمر: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        help_text = """
🎉 **أوامر بوت قائمة الحلوان (المشرف)** 🎉

/start - بدء البوت
/add معرف_الشخص المناسبة - لإضافة شخص ومناسبة
مثال: `/add @ahmed تخرج`

/list - عرض جميع الأشخاص والمناسبات

/remove رقم_السجل - حذف شخص من القائمة
مثال: `/remove 3` (استخدم /list لرؤية الأرقام)

/deleted - عرض جميع السجلات المحذوفة
/restore رقم_الأرشيف - استعادة سجل محذوف
/clear_deleted confirm - مسح جميع المحذوفات نهائياً (بحذر!)

/myid - عرض معرفك
/admins - عرض قائمة المشرفين
/help - عرض هذه المساعدة
"""
    else:
        help_text = """
🎉 **أوامر بوت قائمة الحلوان** 🎉

/start - بدء البوت
/list - عرض جميع الأشخاص والمناسبات
/myid - عرض معرفك
/help - عرض هذه المساعدة

**ملاحظة:** فقط المشرفون يمكنهم إضافة أو حذف من القائمة
"""
    
    await update.message.reply_text(help_text)

def main():
    # تهيئة قاعدة البيانات
    init_db()
    
    # توكن البوت
    TOKEN = "8045809534:AAHZDIlDHg6Xgef4wvvPGtPwv5hdgLgYKS0"
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add", add_person))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("remove", remove_person))
    application.add_handler(CommandHandler("deleted", show_deleted_list))
    application.add_handler(CommandHandler("restore", restore_deleted))
    application.add_handler(CommandHandler("clear_deleted", clear_deleted))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("admins", admins_command))
    
    # بدء البوت
    print("جارٍ تشغيل البوت مع نظام الأرشيف...")
    application.run_polling()

if __name__ == '__main__':
    main()