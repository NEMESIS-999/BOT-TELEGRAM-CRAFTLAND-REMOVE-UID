#!/usr/bin/env python3
# uid_pattern_bot.py
# Telegram bot: يحذف أو يعيد إدراج UID من ملفات .bytes بنفس منطق موقع
#DEV NAME : N6/TELEGRAM : @O000000000000o_X_o000000000000O
#أتمنى ألا يكون حكرًا على أحد، بل أرجو أن يكون متاحًا للجميع ليستفيد منه الجميع.
#كما أتمنى أن تضيف رابطًا للمستودع في بوتك ليتمكن الجميع من استخدامه بأمان.

from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# -----------------------------------
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن بوتك هنا
MAX_FILE_SIZE = 25 * 1024 * 1024   # 25MB كحد أقصى
# -----------------------------------

# -----------------------------------
# منطق الحذف: 
def remove_uid_pattern(data: bytes) -> tuple[bytes, bool]:
    """
    يبحث من نهاية الملف عن النمط:
    byte[i] == 0x38 و byte[i+6] == 0x42
    ثم يحذف 4 بايت ويضع [0x38, 0x00, 0x42]
    """
    buffer = bytearray(data)
    index = -1
    for i in range(len(buffer) - 7, -1, -1):
        if buffer[i] == 0x38 and buffer[i + 6] == 0x42:
            index = i
            break
    if index == -1:
        return data, False

    # نفس منطق JS: حذف 4 بايت
    new_buf = bytearray(len(buffer) - 4)
    # قبل النمط
    new_buf[:index] = buffer[:index]
    # النمط الجديد
    new_buf[index:index + 3] = bytes([0x38, 0x00, 0x42])
    # بعد النمط
    new_buf[index + 3:] = buffer[index + 7:]
    return bytes(new_buf), True


# -----------------------------------
# منطق الإضافة (عكس الحذف)
def add_uid_pattern(data: bytes) -> tuple[bytes, bool]:
    """
    يبحث عن النمط [0x38, 0x00, 0x42]
    ويعيد إدراج 4 بايت افتراضية (0x11, 0x22, 0x33, 0x44)
    بين 0x38 و 0x42 لإرجاع الحالة الأصلية تقريبيًا.
    """
    buffer = bytearray(data)
    index = -1
    for i in range(len(buffer) - 2):
        if buffer[i] == 0x38 and buffer[i + 1] == 0x00 and buffer[i + 2] == 0x42:
            index = i
            break
    if index == -1:
        return data, False

    insert_bytes = bytes([0x11, 0x22, 0x33, 0x44])
    new_buf = bytearray(len(buffer) + 4)
    new_buf[:index + 1] = buffer[:index + 1]
    new_buf[index + 1:index + 5] = insert_bytes
    new_buf[index + 5:] = buffer[index + 1:]
    return bytes(new_buf), True


# -----------------------------------
# Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بوت حذف/إضافة UID للملفات .bytes\n\n"
        "أرسل ملفًا وسأحذف منه UID.\n"
        "أمر الإضافة: /adduid بعد إرسال ملف معدل لإرجاع UID رمزي."
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    doc = msg.document
    if not doc:
        await msg.reply_text("أرسل ملفًا من نوع .bytes فقط.")
        return

    if not doc.file_name.lower().endswith(".bytes"):
        await msg.reply_text("الملف غير صالح. يجب أن يكون بامتداد .bytes")
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await msg.reply_text("الملف أكبر من الحد المسموح (25MB).")
        return

    await msg.reply_text("جارٍ معالجة الملف...")
    file = await context.bot.get_file(doc.file_id)
    bio = BytesIO()
    await file.download_to_memory(out=bio)
    data = bio.getvalue()

    modified, ok = remove_uid_pattern(data)
    if not ok:
        await msg.reply_text("النمط 0x38......0x42 غير موجود. لم يتم أي تعديل.")
        return

    out = BytesIO(modified)
    out.name = f"modified_{doc.file_name}"
    out.seek(0)
    await msg.reply_document(out, filename=out.name, caption="تم حذف UID بنجاح ✅")


async def add_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("أرسل أولاً ملفًا معدّلًا (modified_...).")
        return

    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    bio = BytesIO()
    await file.download_to_memory(out=bio)
    data = bio.getvalue()

    restored, ok = add_uid_pattern(data)
    if not ok:
        await update.message.reply_text("لم يُعثر على النمط المناسب للإضافة (0x38 00 42).")
        return

    out = BytesIO(restored)
    out.name = f"uid_restored_{doc.file_name}"
    out.seek(0)
    await update.message.reply_document(
        document=out,
        filename=out.name,
        caption="تمت إعادة إدراج UID الرمزي بنجاح 🔄"
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل ملف .bytes أو استخدم الأوامر /start أو /adduid")


# -----------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduid", add_uid))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
