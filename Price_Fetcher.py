import requests as rq
import logging
import telegram as tg
import asyncio
import datetime
import pymongo
import product_fetcher

from rtl import rtl
from persiantools.jdatetime import JalaliDate
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes,MessageHandler, filters, ConversationHandler,CallbackQueryHandler
from datetime import datetime

uri = "mongodb://localhost:27017/"
client = pymongo.MongoClient(uri)
database = client["TGbot"]
collection = database["Portfolio"]


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def time():
    months_fa = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر",
    5: "مرداد", 6: "شهریور", 7: "مهر", 8: "آبان",
    9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند",
    }

    weekdays_fa = {
    0: "شنبه", 1: "یکشنبه", 2: "دوشنبه",
    3: "سه‌شنبه", 4: "چهارشنبه",
    5: "پنجشنبه", 6: "جمعه",
    }

    jd = JalaliDate.today()

    result = f"{weekdays_fa[jd.weekday()]}، {jd.day} {months_fa[jd.month]} {jd.year}"
    now = datetime.now().strftime("%H:%M")
    return result + '' + '\n' + '⏳ ساعت ' + now

async def handle_user_link(update: tg.Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if not user_input:
        await update.message.reply_text("Please send a link or text first.")
        return "success"

    # Checking to see if command is given or some unknown input.
    if user_input.startswith('/'):
        await update.message.reply_text("دستور نامشخص یا نامعتبر دریافت شد.")
        return "success"

    loop = asyncio.get_running_loop()
    try:
        product_fetch_loop = await loop.run_in_executor(None, product_fetcher.get_main_site, user_input)

        full_product = f'{product_fetch_loop[0]}\n ' + product_fetch_loop[1]

    except Exception as e:
        logger.exception("Error in handle_user_link for input %s", user_input)
        await update.message.reply_text("متاسفانه نمیتوانم لینک را پردازش کنم. لطفاً دوباره امتحان کنید.")
        return "success"

    # Send the results to user.
    the_result = await update.message.reply_text(str(full_product))
    user_id = update.effective_user.id
    user = update.effective_user
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    username = user.username or ''
    full_name = ' '.join(filter(None, [getattr(user, 'first_name', ''), getattr(user, 'last_name', '')]))
    
    # Prepare saves to be made when user confirms.
    pending = {
        'user_id': int(user_id),
        'username': username or '',
        'full_name': full_name or '',
        'item_link': user_input or '',
        'price': product_fetch_loop[0] or '',
        'desc': product_fetch_loop[1] or '',
        'time': now
    }
    context.user_data['pending_save'] = pending

    # Build inline keyboard with Yes / No
    buttons = [[
        tg.InlineKeyboardButton("✅ بله", callback_data="SAVE_yes"),
        tg.InlineKeyboardButton("❌ خیر", callback_data="SAVE_no"),
    ]]
    reply_markup = tg.InlineKeyboardMarkup(buttons)
    await update.message.reply_text("ذخیره در پورتفولیو؟", reply_markup=reply_markup)
    return "question"

async def button(update: tg.Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('CL_'):
        try:
            idx = int(query.data.split('_',1)[1])
        except (IndexError, ValueError):
            await query.edit_message_text(text="OK!")
            return ConversationHandler.END
        await query.edit_message_text(text=f"Location set: sddd - sd\ndd")
        return ConversationHandler.END
    
    # New handlers for save confirmation
    if query.data == 'SAVE_yes':
        pending = context.user_data.get('pending_save', None)
        if not pending:
            await query.edit_message_text(text="هیچی.")
            return ConversationHandler.END
        await query.edit_message_text(text="لطفا یک اسم برای آیتم انتخاب کنید:")
        return "naming"

    if query.data == 'SAVE_no':
        # Clear pending save and inform user
        context.user_data.pop('pending_save', None)
        await query.edit_message_text(text="ذخیره نشد.")
        return ConversationHandler.END
    
    # --- previous price flow ---
    if query.data == 'PPRICE_yes':
        # user will type the price next
        await query.edit_message_text(text="قیمت اولیه یا خرید را وارد کنید:")
        return "pricing"

    if query.data == 'PPRICE_no':
        pending = context.user_data.pop('pending_save', None)
        if not pending:
            await query.edit_message_text(text="هیچی برای ذخیره پیدا نشد.")
            return ConversationHandler.END
        # save with zero price
        try:
            save_user(
                pending['user_id'],
                pending.get('username', ''),
                pending.get('full_name', ''),
                pending.get('item_link', ''),
                pending.get('time', ''),
                pending.get('price', ''),
                pending.get('desc',''),
                item_name=pending.get('item_name',''),
                prev_price=0,
            )
            await query.edit_message_text(text="✅ ذخیره شد بدون قیمت اولیه.")
        except Exception as e:
            logger.exception("Failed to save item with no price: %s", e)
            await query.edit_message_text(text="⚠️ ذخیره با خطا مواجه شد.")
        return ConversationHandler.END
    
    # -- Reset Button Workflow -- #
    if query.data == 'reset_yes':
        user_id = update.effective_user.id
        try:
            result = reset_portfolio(user_id)
            if result == 'success':
                await query.edit_message_text(text="✅ پورتفولیو شما با موفقیت پاک شد.")
            else:
                await query.edit_message_text(text="⚠️ پورتفولیویی برای پاک کردن پیدا نشد.")
        except Exception as e:
            logger.exception("Failed to reset portfolio: %s", e)
            await query.edit_message_text(text="⚠️ خطا در پاک کردن پورتفولیو.")
        return ConversationHandler.END
    
    if query.data == 'reset_no':
        await query.edit_message_text(text="❌ پاک کردن لغو شد.")
        return ConversationHandler.END

async def handle_prev_price(update: tg.Update, context: ContextTypes.DEFAULT_TYPE):
    # user has provided a numeric previous price
    prev_price_text = update.message.text.strip()
    pending = context.user_data.pop('pending_save', None)

    if not pending:
        await update.message.reply_text("هیچ موردی برای ذخیره یافت نشد. لطفا دوباره تلاش کنید.")
        return ConversationHandler.END

    try:
        # try to convert to integer
        prev_price_val = int(prev_price_text.replace(',', '')) 
    except ValueError:
        await update.message.reply_text("لطفا فقط عدد وارد کنید.")
        # keep same state to allow re-entry
        context.user_data['pending_save'] = pending
        return "pricing"

    try:
        save_user(
            pending['user_id'],
            pending.get('username', ''),
            pending.get('full_name', ''),
            pending.get('item_link', ''),
            pending.get('time', ''),
            pending.get('price', ''),
            pending.get('desc',''),
            item_name=pending.get('item_name',''),
            prev_price=prev_price_val
        )
        await update.message.reply_text(f"✅ ذخیره شد با قیمت اولیه {prev_price_val} تومان.")
    except Exception as e:
        logger.exception("Failed to save pending item with price: %s", e)
        await update.message.reply_text("⚠️ Failed to save. Please try again.")

    return ConversationHandler.END

async def handle_item_name(update: tg.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the item name input and then ask if a previous price should be recorded."""
    item_name = update.message.text.strip()
    if not item_name:
        await update.message.reply_text("Please provide a valid name.")
        return "naming"

    pending = context.user_data.get('pending_save', None)
    if not pending:
        await update.message.reply_text("Error: No item to save. Please start over.")
        return ConversationHandler.END

    
    pending['item_name'] = f'آیتم {item_name}'
    context.user_data['pending_save'] = pending

    # Ask user for buy price.
    buttons = [[
        tg.InlineKeyboardButton("✅ بله", callback_data="PPRICE_yes"),
        tg.InlineKeyboardButton("❌ خیر", callback_data="PPRICE_no"),
    ]]
    reply_markup = tg.InlineKeyboardMarkup(buttons)
    await update.message.reply_text("آیا قیمت اولیه یا خرید دارید؟", reply_markup=reply_markup)

    return "question"

async def handle_reset_button(update: tg.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the reset button - ask user for confirmation"""
    buttons = [[
        tg.InlineKeyboardButton("✅ بله، پاک کن", callback_data="reset_yes"),
        tg.InlineKeyboardButton("❌ خیر", callback_data="reset_no"),
    ]]
    reply_markup = tg.InlineKeyboardMarkup(buttons)
    await update.message.reply_text("آیا میخواهید کل پورتفولیو خود را پاک کنید؟ این عمل قابل بازگشت نیست.", reply_markup=reply_markup)
    return "question"

### Fetch Section
def fetch_currency_data():
    """Fetch currency data from API"""
    try:
        currency = rq.get("https://api-web.tabdeal.org/r/festival/get-asset-prices/?asset_type=currency")
        data = currency.json()
        return data
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None

def fetch_coin_data():
    """Fetch coin data from API """
    try:
        coin = rq.get("https://api-web.tabdeal.org/r/festival/get-asset-prices/?asset_type=coin")
        data_coin = coin.json()
        return data_coin
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None

def fetch_gold_data():
    """Fetch gold data from API """
    try:
        gold = rq.get("https://api-web.tabdeal.org/r/festival/get-asset-prices/?asset_type=gold")
        data_gold = gold.json()
        return data_gold
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None
### Fetch Section
def format_price_dict(price_dict: dict) -> str:
    lines = []
    for key, value in price_dict.items():
        k = str(key).lower()
        if "طلا" in k or "گرم" in k or "عیار" in k or "gold" in k:
            emoji = "🥇"
        elif "سکه" in k or "بهر" in k or "bahar" in k or "coin" in k:
            emoji = "🪙"
        else:
            emoji = "💵"

        try:
            formatted_value = f"{int(value):,d} تومان"
        except Exception:
            formatted_value = str(value)

        lines.append(f"{emoji} {key} {formatted_value}")

    return "\n".join(lines) 

def _format_section(title: str, data: dict, emoji: str) -> str:
    """Format a single titled section if data is present."""
    if not data:
        return ""
    lines = [f"{title}"]
    for key, value in data.items():
        try:
            formatted = f"{int(value):,d} تومان"
        except Exception:
            formatted = str(value)
        lines.append(f"{emoji} {key} {formatted}")
    return "\n".join(lines)

def format_sections(currency: dict, gold: dict, coin: dict) -> str:
    """Build a message with three separate sections: currency, gold, coin."""
    parts = []
    cur_part = _format_section("💵 ارزها:", currency, "💵")
    if cur_part:
        parts.append(cur_part)

    gold_part = _format_section("🥇 طلا:", gold, "🥇")
    if gold_part:
        parts.append(gold_part)

    coin_part = _format_section("🪙 سکه:", coin, "🪙")
    if coin_part:
        parts.append(coin_part)

    return "\n\n".join(parts) + f'\n 📅 {time()}'

def format_portfolio(portoflio: list):
    parts = []
    if portoflio:
        lines = ["💱 پورتفولیو:\n"]
        for key, info in portoflio.items():

            curr = info.get('current')
            prev = info.get('prev', 0) or 0
            try:
                fmt_curr = f"\n قیمت فعلی: {int(curr):,d} تومان"
            except Exception:
                fmt_curr = str(curr)
            try:
                fmt_prev = f"{int(prev):,d} تومان"
            except Exception:
                fmt_prev = str(prev)
            
            # Calculate profit/loss
            profit_loss = 0
            profit_loss_str = ""
            indicator = "➡️"
            
            try:
                curr_val = int(str(curr).replace(',', '')) if curr else 0
                prev_val = int(str(prev).replace(',', '')) if prev else 0
                
                if prev_val > 0:
                    profit_loss = curr_val - prev_val
                    profit_loss_str = f"{profit_loss:,d} تومان"
                    
                    # Calculate percentage change
                    percent_change = (profit_loss / prev_val) * 100
                    
                    if profit_loss > 0:
                        indicator = f"سود 📈 : (+){profit_loss_str} ({percent_change:+.1f}%)"
                    elif profit_loss < 0:
                        indicator = f"زیان 📉 : {profit_loss_str} ({percent_change:+.1f}%)"
                    else:
                        indicator = "➡️ بدون تغییر"
            except Exception:
                indicator = "➡️"
            
            if key.startswith("آیتم "):
                _, name = key.split(" ", 1)
                lines.append(f"🔗 آیتم {name} \n {fmt_curr}\n قیمت خرید: {fmt_prev}\n {indicator}\n")
            else:
                lines.append(f"\n🔗 {key} \n {fmt_curr}\n قیمت خرید: {fmt_prev}\n {indicator}\n")
        portoflio_part = "\n".join(lines)
        parts.append(portoflio_part)
    return "\n\n".join(parts) + f'\n 📅 {time()}'

def create_hourly_updater(chat_id):
    """Factory function to create an hourly price updater for a specific chat"""
    async def hourly_price_update(context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send hourly price update to chat"""
        currency = fetch_currency_data()
        gold_data = fetch_gold_data()
        coin_data = fetch_coin_data()
        if not currency:
            logger.warning("No data to send")
            return

        currency_dict = {}
        gold_dict = {}
        coin_dict = {}
        gold_data = gold_data or []
        coin_data = coin_data or []

        for i in currency:
            try:
                currency_dict[i['price_title']] = int(i['last_price'][:-1])
            except Exception:
                currency_dict[i['price_title']] = i.get('last_price', 'N/A')

        for i in coin_data:
            try:
                coin_dict[i['price_title']] = int(i['last_price'][:-1])
            except Exception:
                coin_dict[i['price_title']] = i.get('last_price', 'N/A')

        for i in gold_data:
            try:
                gold_dict[i['price_title']] = int(i['last_price'][:-1])
            except Exception:
                gold_dict[i['price_title']] = i.get('last_price', 'N/A')

        # Remove unwanted items safely
        currency_dict.pop('یورو', None)
        currency_dict.pop('پوند', None)
        gold_dict.pop('طلای ۲۴ عیار', None)

        # hourly updater doesn't include user portfolio
        message = format_sections(currency_dict, gold_dict, coin_dict)
        await context.bot.send_message(chat_id=chat_id, text=message)
    
    return hourly_price_update

def save_user(user_id,username,full_name,item_link,time,price=None,desc=None,item_name=None,prev_price=None):
    the_document = {
        'user_id': int(user_id),
        'username': username or '',
        'full_name': full_name or '',
        'item_link': item_link or '',
        'price':price or '',
        'desc':desc or '',
        'item_name': item_name or '',
        'prev_price': prev_price or 0,
        'time': time
    }
    collection.update_one({'user_id': the_document['user_id']}, {'$push': {'items': the_document}}, upsert=True)
    return 'success'

def reset_portfolio(user_id):
    coll = collection.find({'user_id':user_id})
    coll_to_list = coll.to_list()

    if coll_to_list != None:
        collection.delete_many({'user_id':int(user_id)})
        return 'success'
    else:
        return 'not success'

def get_user_portfolio(user_id):
    """Fetch user's saved portfolio items from MongoDB"""
    try:
        user_doc = collection.find_one({'user_id': int(user_id)})
        if user_doc:
            return user_doc.get('items', [])
        return []
    except Exception as e:
        logger.error(f"Failed to fetch portfolio for user {user_id}: {e}")
        return []

def set_user_interval(user_id, interval_minutes: int):
    """Store a custom update interval (in minutes) for the user."""
    try:
        collection.update_one(
            {'user_id': int(user_id)},
            {'$set': {'interval': int(interval_minutes)}},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"Failed to set interval for user {user_id}: {e}")

def get_user_interval(user_id, default_minutes: int = 20) -> int:
    """Retrieve the stored interval (in minutes) for the user, or default."""
    try:
        user_doc = collection.find_one({'user_id': int(user_id)})
        if user_doc and 'interval' in user_doc:
            return int(user_doc.get('interval', default_minutes))
    except Exception as e:
        logger.error(f"Failed to get interval for user {user_id}: {e}")
    return default_minutes

async def reschedule_for_user(chat_id: int, context: ContextTypes.DEFAULT_TYPE, interval_minutes: int):
    """Cancel existing jobs and schedule a new repeating job using the given interval."""
    jq = context.application.job_queue
    if jq is None:
        return
    name = str(chat_id)
    # remove existing jobs
    for job in jq.get_jobs_by_name(name):
        job.schedule_removal()
    # Schedule using new interval given by user.
    jq.run_repeating(
        create_hourly_updater(chat_id),
        interval=interval_minutes * 60,
        first=0,
        name=name,
    )

async def send_prices(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch price data and reply exactly as /start does (excluding scheduling).

    Replies via message or callback_query depending on the update type.
    """
    if update.callback_query:
        target: tg.Message = update.callback_query.message
    else:
        target: tg.Message = update.message

    data = fetch_currency_data()
    gold_data = fetch_gold_data()
    coin_data = fetch_coin_data()
    
    if data:
        currency_dict = {}
        gold_dict = {}
        coin_dict = {}
        gold_data = gold_data or []
        coin_data = coin_data or []

        for i in data:
            try:
                currency_dict[i['price_title']] = int(i['last_price'][:-1])
            except Exception:
                currency_dict[i['price_title']] = i.get('last_price', 'N/A')

        for i in coin_data:
            try:
                coin_dict[i['price_title']] = int(i['last_price'][:-1])
            except Exception:
                coin_dict[i['price_title']] = i.get('last_price', 'N/A')

        for i in gold_data:
            try:
                gold_dict[i['price_title']] = int(i['last_price'][:-1])
            except Exception:
                gold_dict[i['price_title']] = i.get('last_price', 'N/A')

        # Removing chosen unwanted items.
        # currency_dict.pop('یورو', None)
        # currency_dict.pop('پوند', None)
        # gold_dict.pop('طلای ۲۴ عیار', None)

        message = format_sections(currency_dict, gold_dict, coin_dict)

        try:
            await target.reply_text(message)
        except Exception as exc:  
            logger.warning("send_prices: failed to send price message: %s", exc)

            try:
                await asyncio.sleep(1)
                await target.reply_text(message)
            except Exception as exc2:
                logger.error("send_prices: retry also failed: %s", exc2)
        # Providing a button for setting the schedule
        sched_btn = tg.InlineKeyboardMarkup(
            [[tg.InlineKeyboardButton("🕒 Set Time", callback_data="SET_INTERVAL")]]
        )
        try:
            await target.reply_text("Use custom interval", reply_markup=sched_btn)
        except Exception as exc:
            logger.warning("send_prices: button message failed: %s", exc)
        return message

async def send_portfolio(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        target: tg.Message = update.callback_query.message
    else:
        target: tg.Message = update.message

    chat_id = update.effective_chat.id
     # build portfolio mapping: item_name -> {current: price, prev: prev_price}
    users_items = {}
    user_portfolio = get_user_portfolio(chat_id)
     # helper to fetch current price for a link
    def fetch_price(link):
        try:
            return product_fetcher.get_main_site(link)[0]
        except Exception:
            return None

    loop = asyncio.get_running_loop()
    for item in user_portfolio:
        name = item.get('item_name', '')
        prev = item.get('prev_price', 0) or 0
        link = item.get('item_link', '')

        # run blocking fetch in executor
        curr = None
        if link:
            try:
                curr = await loop.run_in_executor(None, fetch_price, link)
            except Exception:
                curr = None
        # convert strings to ints if possible
        try:
            curr_val = int(str(curr).replace(',', '')) if curr is not None else 0
        except Exception:
            curr_val = curr
        users_items[name] = {'current': curr_val, 'prev': prev}
    message1 = format_portfolio(users_items)
    try:
        await target.reply_text(message1)
    except Exception as exc:  # handle timeouts/network errors gracefully
        logger.warning("send_portfolio: failed to send price message: %s", exc)
     # retry once after short pause
        try:
            await asyncio.sleep(1)
            await target.reply_text(message1)
        except Exception as exc2:
            logger.error("send_portfolio: retry also failed: %s", exc2)
    return message1

async def start(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send currency price to user and start hourly updates"""
    #await send_prices(update, context) 
    # await send_portfolio(update,context)

    # Schedule price updates.
    chat_id = update.effective_chat.id
    job_queue = context.application.job_queue
    job_name = str(chat_id)
    
    if job_queue is not None:
        # clear any previous jobs for this chat
        for job in job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()

        # Read users given Schedule interval
        interval = get_user_interval(chat_id)
        # To seconds conversion
        job_queue.run_repeating(
            create_hourly_updater(chat_id),
            interval=interval * 60,
            first=0,
            name=job_name
        )

async def stop(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop hourly price updates"""
    chat_id = update.effective_chat.id

    jq = context.application.job_queue
    if jq is not None:
        current_jobs = jq.get_jobs_by_name(str(chat_id))
        for job in current_jobs:
            job.schedule_removal()
    await update.message.reply_text("❌ Updates stopped")

async def reset(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the reset confirmation flow"""
    await handle_reset_button(update, context)
    return "question"

async def ask_interval(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Entry point for /schedule command or SET_INTERVAL callback: prompt for interval choice.

    Works with both message and callback_query updates.  Also send current prices first.
    """
    #await send_prices(update, context)

    # Creating keyboard text.
    buttons = [
        [tg.InlineKeyboardButton("30 Minutes", callback_data="INT_30")],
        [tg.InlineKeyboardButton("1 Hour", callback_data="INT_60")],
        [tg.InlineKeyboardButton("3 Hours", callback_data="INT_180")],
        [tg.InlineKeyboardButton("Custom interval", callback_data="INT_CUSTOM")],
    ]
    reply_markup = tg.InlineKeyboardMarkup(buttons)

    if update.callback_query:
        query = update.callback_query
        await query.answer()

        await query.edit_message_text("Enter your desired update interval", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Enter your desired update interval", reply_markup=reply_markup)

    return "SCHED_CHOICE"

async def schedule_button(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle interval selection from inline keyboard."""
    query = update.callback_query
    await query.answer()
    data = query.data.split("_", 1)[1]
    user_id = update.effective_user.id
    if data == "CUSTOM":
        await query.edit_message_text("Enter your desired interval (in minutes): ")
        return "SCHED_CUSTOM"
    else:
        interval = int(data)
        set_user_interval(user_id, interval)
        await query.edit_message_text(f"Time interval is set to {interval} minutes.")
        # reschedule current job
        await reschedule_for_user(update.effective_chat.id, context, interval)
        return ConversationHandler.END

async def handle_custom_interval(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    text = update.message.text.strip()
    try:
        interval = int(text)
    except ValueError:
        await update.message.reply_text("Incorrect number, please try again: ")
        return "SCHED_CUSTOM"
    user_id = update.effective_user.id
    set_user_interval(user_id, interval)
    await update.message.reply_text(f"Time interval is set to {interval} minutes.")
    await reschedule_for_user(update.effective_chat.id, context, interval)
    return ConversationHandler.END

async def unknown_command(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for unhandled slash commands."""
    await update.message.reply_text("Unkown command,try again.")

if __name__ == '__main__':
    # Base_Url = 'https://tapi.bale.ai/bot'
    application = ApplicationBuilder().token('YOUR_TOKEN').build()
    
    # Add command handlers.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("reset", reset))
    #application.add_handler(CommandHandler("portfolio",send_portfolio))
    # Handle reset button callbacks.
    application.add_handler(CallbackQueryHandler(button, pattern="^reset_"))

    schedule_conv = ConversationHandler(
        entry_points=[
            CommandHandler("schedule", ask_interval),
            CallbackQueryHandler(ask_interval, pattern="^SET_INTERVAL$"),
        ],
        states={
            "SCHED_CHOICE": [CallbackQueryHandler(schedule_button, pattern="^INT_")],
            "SCHED_CUSTOM": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_interval)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
    )
    application.add_handler(schedule_conv)

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_link)],
        states={
            "success": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_link)],
            "question":[CallbackQueryHandler(button)],
            "naming": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_name)],
            "pricing": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prev_price)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    application.add_handler(conv_handler)
    
    # Catch all not handled commands.
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Start the bot.
    application.run_polling(allowed_updates=[])
