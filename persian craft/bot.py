import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ===== تنظیمات =====
ADMIN_ID = 6905755356
CARD_NUMBER = "6219 8618 4765 9652"
SERVER_IP = "5.57.32.36"
PRODUCTS_FILE = "products.json"

# ===== بارگذاری یا ایجاد فایل محصولات =====
if not os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

def load_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

# ===== حافظه موقت سفارشات =====
user_orders = {}

# ===== شروع کاربر =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = load_products()
    if not products:
        await update.message.reply_text("📦 در حال حاضر محصولی ثبت نشده است.")
        return
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"{p['name']} - {p['price']} تومان", callback_data=f"buy_{p['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("سلام! لطفاً محصول مورد نظر را انتخاب کنید:", reply_markup=reply_markup)

# ===== پنل مدیریت =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما ادمین نیستید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="admin_add")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data="admin_delete")],
        [InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_edit_price")],
        [InlineKeyboardButton("📦 لیست محصولات", callback_data="admin_list")]
    ]
    await update.message.reply_text("📋 پنل مدیریت:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== کلیک دکمه‌ها =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # خرید محصول
    if query.data.startswith("buy_"):
        product_id = int(query.data.split("_")[1])
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        
        user_orders[query.from_user.id] = {
            "step": "waiting_for_name",
            "product": product
        }
        await query.message.reply_text(
            f"💰 قیمت: {product['price']} تومان\n"
            f"💳 شماره کارت: {CARD_NUMBER}\n\n"
            "لطفاً *نام اکانت ماینکرافت* خود را ارسال کنید:",
            parse_mode="Markdown"
        )

    # افزودن محصول
    elif query.data == "admin_add" and query.from_user.id == ADMIN_ID:
        user_orders[query.from_user.id] = {"step": "admin_add_name"}
        await query.message.reply_text("نام محصول را وارد کنید:")

    # حذف محصول
    elif query.data == "admin_delete" and query.from_user.id == ADMIN_ID:
        products = load_products()
        if not products:
            await query.message.reply_text("📦 هیچ محصولی ثبت نشده.")
            return
        keyboard = [[InlineKeyboardButton(p["name"], callback_data=f"delete_{p['id']}")] for p in products]
        await query.message.reply_text("محصولی را برای حذف انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("delete_") and query.from_user.id == ADMIN_ID:
        product_id = int(query.data.split("_")[1])
        products = load_products()
        products = [p for p in products if p["id"] != product_id]
        save_products(products)
        await query.message.reply_text("✅ محصول حذف شد.")

    # تغییر قیمت
    elif query.data == "admin_edit_price" and query.from_user.id == ADMIN_ID:
        products = load_products()
        if not products:
            await query.message.reply_text("📦 هیچ محصولی ثبت نشده.")
            return
        keyboard = [[InlineKeyboardButton(p["name"], callback_data=f"editprice_{p['id']}")] for p in products]
        await query.message.reply_text("محصولی را برای تغییر قیمت انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("editprice_") and query.from_user.id == ADMIN_ID:
        product_id = int(query.data.split("_")[1])
        user_orders[query.from_user.id] = {"step": "admin_edit_price", "product_id": product_id}
        await query.message.reply_text("💰 قیمت جدید را وارد کنید:")

    # لیست محصولات
    elif query.data == "admin_list" and query.from_user.id == ADMIN_ID:
        products = load_products()
        if not products:
            await query.message.reply_text("📦 لیست محصولات خالی است.")
            return
        text = "\n".join([f"{p['name']} - {p['price']} تومان" for p in products])
        await query.message.reply_text(f"📦 محصولات موجود:\n{text}")

# ===== دریافت پیام‌ها =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in user_orders:
        step = user_orders[user_id]["step"]

        # افزودن محصول
        if step == "admin_add_name" and user_id == ADMIN_ID:
            user_orders[user_id] = {"step": "admin_add_price", "name": update.message.text}
            await update.message.reply_text("💰 قیمت محصول را وارد کنید:")

        elif step == "admin_add_price" and user_id == ADMIN_ID:
            try:
                price = int(update.message.text)
            except:
                await update.message.reply_text("❌ قیمت باید عدد باشد.")
                return
            products = load_products()
            new_id = max([p["id"] for p in products], default=0) + 1
            products.append({"id": new_id, "name": user_orders[user_id]["name"], "price": price})
            save_products(products)
            del user_orders[user_id]
            await update.message.reply_text("✅ محصول با موفقیت اضافه شد.")

        # تغییر قیمت
        elif step == "admin_edit_price" and user_id == ADMIN_ID:
            try:
                price = int(update.message.text)
            except:
                await update.message.reply_text("❌ قیمت باید عدد باشد.")
                return
            products = load_products()
            for p in products:
                if p["id"] == user_orders[user_id]["product_id"]:
                    p["price"] = price
            save_products(products)
            del user_orders[user_id]
            await update.message.reply_text("✅ قیمت تغییر کرد.")

        # خرید محصول
        elif step == "waiting_for_name":
            user_orders[user_id]["name"] = update.message.text
            user_orders[user_id]["step"] = "waiting_for_receipt"
            await update.message.reply_text("✅ نام ثبت شد. حالا لطفاً تصویر فیش واریزی را ارسال کنید.")

        elif step == "waiting_for_receipt" and update.message.photo:
            receipt_file_id = update.message.photo[-1].file_id
            order = user_orders[user_id]
            order["receipt_file_id"] = receipt_file_id
            order["step"] = "done"

            # ارسال سفارش به ادمین
            keyboard = [[InlineKeyboardButton("✅ تایید سفارش", callback_data=f"approve_{user_id}")]]
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=receipt_file_id,
                caption=f"📦 سفارش جدید:\n\n"
                        f"محصول: {order['product']['name']}\n"
                        f"قیمت: {order['product']['price']} تومان\n"
                        f"نام ماینکرافت: {order['name']}\n"
                        f"یوزرنیم: @{update.message.from_user.username or 'ندارد'}\n"
                        f"آیدی عددی: {user_id}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await update.message.reply_text("✅ سفارش ثبت شد. بعد از تایید ادمین اطلاعات سرور ارسال می‌شود.")

# ===== تایید سفارش =====
async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.message.reply_text("❌ شما ادمین نیستید!")
        return
    user_id = int(update.callback_query.data.split("_")[1])
    await context.bot.send_message(chat_id=user_id, text=f"🎉 سفارش شما تایید شد!\n📡 آدرس سرور: {SERVER_IP}")
    await update.callback_query.message.reply_text("✅ سفارش تایید و برای کاربر ارسال شد.")

# ===== اجرای ربات =====
if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(approve_handler, pattern="^approve_\\d+$"))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, message_handler))

    print("🤖 Bot is running...")
    app.run_polling()
