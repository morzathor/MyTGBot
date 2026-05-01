# ...existing code...
import logging
import re
import telegram as tg
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
import weatherer
import saver
import Price_Fetcher
import datetime
import importlib.util
import os

# load Main-pass.py as a module so we can reuse its DB helpers
_THIS_DIR = os.path.dirname(__file__)
_PASS_PATH = os.path.join(_THIS_DIR, 'Main-pass.py')
spec = importlib.util.spec_from_file_location('main_pass', _PASS_PATH)
passmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(passmod)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Define menu buttons globally
MENU_BUTTONS = {
    "Current Weather", "Daily Forecast", "Hourly Forecast",
    "Set city", "Generate Password", "My Passwords",
    "Portfolio", "Prices"
}

async def start(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Try to load user's saved location from MongoDB
    
    user_id = update.effective_user.id
    saved_location = saver.get_user_location(user_id)
    
    if saved_location:
        # Set location in context from MongoDB
        context.user_data['location'] = saved_location
        weatherer.DEFAULT_PARAMETERS['latitude'] = str(saved_location['lat'])
        weatherer.DEFAULT_PARAMETERS['longitude'] = str(saved_location['lon'])
        # Prefer stored timezone if present, otherwise compute from coordinates
        if saved_location.get('timezone'):
            weatherer.DEFAULT_PARAMETERS['timezone'] = saved_location.get('timezone')
        else:
            timezone = weatherer.get_timezone_from_coordinates(saved_location['lat'], saved_location['lon'])
            weatherer.DEFAULT_PARAMETERS['timezone'] = timezone

    keyboard = [
        [
            tg.KeyboardButton("Current Weather"),
            tg.KeyboardButton("Daily Forecast"),
            tg.KeyboardButton("Hourly Forecast")
        ],
        [tg.KeyboardButton("Set city")],
        [tg.KeyboardButton("Generate Password"), tg.KeyboardButton("My Passwords")],
        [tg.KeyboardButton("Portfolio")],
        [tg.KeyboardButton("Prices")]
    ]
    reply_markup = tg.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    #await update.message.reply_text(f"{await Price_Fetcher.send_prices(update,context)}",reply_markup=reply_markup)

    await update.message.reply_text(f"Welcome to your own personal bot!!\n\nChoose an action to do ", reply_markup=reply_markup)

def format_forecast_with_bold_times(forecast_lines: list, prefix: str = "") -> tuple:
    """Format forecast lines with bold time and temperature entities. Returns (text, entities)."""
    text = prefix + "\n" + "\n".join(forecast_lines)
    entities = []
    
    # Calculate offset after the prefix and first newline
    offset = len(prefix) + 1  # +1 for the newline after prefix
    
    for line in forecast_lines:
        # Find HH:MM (time - exactly 5 characters like "00:00")
        time_match = re.search(r'\d{2}:\d{2}', line)
        if time_match:
            time_pos = time_match.start()
            time_length = time_match.end() - time_match.start()
            entities.append(tg.MessageEntity(offset=offset + time_pos, length=time_length, type=tg.MessageEntity.BOLD))
        
        # Find the last number in the line (temperature at the end)
        all_numbers = list(re.finditer(r'[\d.]+', line))
        if all_numbers:
            last_temp = all_numbers[-1]
            temp_pos = last_temp.start()
            temp_length = last_temp.end() - last_temp.start()
            entities.append(tg.MessageEntity(offset=offset + temp_pos, length=temp_length, type=tg.MessageEntity.BOLD))
        
        # Move offset to next line
        offset += len(line) + 1  # +1 for the newline
    
    return text, entities

async def send_start_menu(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the same start menu to the user, works for callback_query or normal messages."""
    keyboard = [
        [
            tg.KeyboardButton("Current Weather"),
            tg.KeyboardButton("Daily Forecast"),
            tg.KeyboardButton("Hourly Forecast")
        ],
        [tg.KeyboardButton("Set city")],
        [tg.KeyboardButton("Generate Password"), tg.KeyboardButton("My Passwords")],
        [tg.KeyboardButton("Portfolio")],
        [tg.KeyboardButton("Prices")]
    ]
    reply_markup = tg.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if getattr(update, "callback_query", None):
        # send as a new message in the same chat where the callback originated
        # Telegram rejects empty/whitespace-only texts, so send a small prompt
        await update.callback_query.message.reply_text("Choose an action to do", reply_markup=reply_markup)

async def handle_button_text(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Handle text button presses from ReplyKeyboardMarkup buttons."""
    text = update.message.text.strip()
    
    if text == "Daily Forecast":
        # Check if location is set, if not try to load from MongoDB
        if 'location' not in context.user_data:
            user_id = update.effective_user.id
            saved_location = saver.get_user_location(user_id)
            if saved_location:
                context.user_data['location'] = saved_location
                weatherer.DEFAULT_PARAMETERS['latitude'] = str(saved_location['lat'])
                weatherer.DEFAULT_PARAMETERS['longitude'] = str(saved_location['lon'])
                if saved_location.get('timezone'):
                    weatherer.DEFAULT_PARAMETERS['timezone'] = saved_location.get('timezone')
                else:
                    weatherer.DEFAULT_PARAMETERS['timezone'] = weatherer.get_timezone_from_coordinates(saved_location['lat'], saved_location['lon'])
        
        # If still no location, ask for city first
        if 'location' not in context.user_data:
            await update.message.reply_text("Location not set. Please set city first.")
            return "CITY_INPUT"
        
        await update.message.reply_text("How many days of forecast do you want? (1-16)")
        return "DAYS_INPUT"
    
    elif text == "Hourly Forecast":
        # Check if location is set, if not try to load from MongoDB
        if 'location' not in context.user_data:
            user_id = update.effective_user.id
            saved_location = saver.get_user_location(user_id)
            if saved_location:
                context.user_data['location'] = saved_location
                weatherer.DEFAULT_PARAMETERS['latitude'] = str(saved_location['lat'])
                weatherer.DEFAULT_PARAMETERS['longitude'] = str(saved_location['lon'])
                if saved_location.get('timezone'):
                    weatherer.DEFAULT_PARAMETERS['timezone'] = saved_location.get('timezone')
                else:
                    weatherer.DEFAULT_PARAMETERS['timezone'] = weatherer.get_timezone_from_coordinates(saved_location['lat'], saved_location['lon'])
        
        # If still no location, ask for city first
        if 'location' not in context.user_data:
            await update.message.reply_text("Location not set. Please set city first.")
            return "CITY_INPUT"
        
        await update.message.reply_text("How many hours of forecast do you want? ")
        return "HOURS_INPUT"
    
    elif text == "Set city":
        # ask user for city name, then handle in CITY_INPUT state
        await update.message.reply_text("Enter your city:")
        return "CITY_INPUT"
    
    elif text == "Current Weather":
        # Try to load from MongoDB if not in context
        if 'location' not in context.user_data:
            user_id = update.effective_user.id
            saved_location = saver.get_user_location(user_id)
            if saved_location:
                context.user_data['location'] = saved_location
                weatherer.DEFAULT_PARAMETERS['latitude'] = str(saved_location['lat'])
                weatherer.DEFAULT_PARAMETERS['longitude'] = str(saved_location['lon'])
        
        # If still no location, ask for city first
        if 'location' not in context.user_data:
            await update.message.reply_text("Location not set. Please set city first.")
            return "CITY_INPUT"
        
        # Prefer per-user saved location if available, then call weather
        user_loc = context.user_data.get('location')
        if user_loc:
            weatherer.DEFAULT_PARAMETERS['latitude'] = str(user_loc.get('lat', ''))
            weatherer.DEFAULT_PARAMETERS['longitude'] = str(user_loc.get('lon', ''))

        result = weatherer.current_forecast()
        await update.message.reply_text(result)
        # show start menu again
        await send_start_menu(update, context)
        return ConversationHandler.END
    
    elif text == "Generate Password":
        # start interactive password generation: ask for service name
        await update.message.reply_text("Enter service name for this password:")
        return "PASS_SERVICE"
    
    elif text == "My Passwords":
        # list passwords saved for this user via Main-pass helpers
        user = update.effective_user
        user_id = user.id
        try:
            docs = passmod.get_passwords_for_user(user_id, limit=20)
        except Exception as e:
            logger.exception("Failed to retrieve passwords: %s", e)
            await update.message.reply_text("Failed to retrieve passwords.")
            return ConversationHandler.END
        if not docs:
            await update.message.reply_text("You have no saved passwords.")
            await send_start_menu(update, context)
            return ConversationHandler.END
        lines = []
        for d in docs:
            svc = d.get('service', '')
            tm = d.get('time', '')
            pwd = d.get('password', '')
            lines.append(f"Service name: {svc}\n Generated Password: {pwd}\n Generation Time: ({tm})\n")
        result = '\n'.join(lines)
        await update.message.reply_text(result)
        await send_start_menu(update, context)
        return ConversationHandler.END
    elif text == "Portfolio":
        user = update.effective_user
        user_id = user.id
        try:
            await Price_Fetcher.send_portfolio(update,context)
            await send_start_menu(update,context)
            return ConversationHandler.END
        except TimeoutError:
            pass
    elif text == "Prices":
        user = update.effective_user
        user_id = user.id
        try:
            await Price_Fetcher.send_prices(update,context)
            await send_start_menu(update,context)
            return ConversationHandler.END
        except TimeoutError:
            pass
    return None

async def button(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Handle location selection (still uses callbacks temporarily)."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('LOC_'):
        # user selected one of the presented location candidates
        try:
            idx = int(query.data.split('_', 1)[1])
        except (IndexError, ValueError):
            await query.edit_message_text(text="Invalid selection.")
            return ConversationHandler.END

        candidates = context.user_data.get('loc_candidates') or []
        if idx < 0 or idx >= len(candidates):
            await query.edit_message_text(text="Selection out of range.")
            return ConversationHandler.END

        choice = candidates[idx]
        # set global parameters
        weatherer.DEFAULT_PARAMETERS['longitude'] = str(choice['lon'])
        weatherer.DEFAULT_PARAMETERS['latitude'] = str(choice['lat'])
        # Prefer the timezone computed when building candidates
        timezone = choice.get('timezone') or weatherer.get_timezone_from_coordinates(choice['lat'], choice['lon'])
        weatherer.DEFAULT_PARAMETERS['timezone'] = timezone

        # persist the user's final selection in their user_data
        # store the chosen candidate (lat, lon, display_name, state, country_code)
        context.user_data['location'] = {
            'lat': choice.get('lat'),
            'lon': choice.get('lon'),
            'display_name': choice.get('display_name'),
            'state': choice.get('state'),
            'country_code': choice.get('country_code'),
            'timezone': timezone
        }
        
        # Save location to MongoDB
        user_id = update.effective_user.id
        user = update.effective_user
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        username = user.username or ''
        full_name = ' '.join(filter(None, [getattr(user, 'first_name', ''), getattr(user, 'last_name', '')]))
        try:
            saver.save_user(user_id, username, full_name, choice.get('display_name', ''), choice.get('state', ''), choice.get('lon'), choice.get('lat'), now)
        except Exception as e:
            logger.exception("Failed to save user location: %s", e)
        
        await query.edit_message_text(text=f"Location set: {choice.get('state','')} - {choice.get('country_code','')}\n{choice.get('display_name','')}")
        # clear the stored candidates
        context.user_data.pop('loc_candidates', None)
        # show start menu again
        await send_start_menu(update, context)
        return ConversationHandler.END
    
    else:
        await query.edit_message_text(text=f"You selected: {query.data}")
        await send_start_menu(update, context)
        return ConversationHandler.END

async def handle_days_input(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    # Check if this is a menu button - if so, handle it as a menu button
    if text in MENU_BUTTONS:
        return await handle_button_text(update, context)
    
    try:
        days = int(text)
        if days < 1 or days > 16:
            await update.message.reply_text("Please enter a number between 1 and 16.")
            return "DAYS_INPUT"
        forecast_lines = weatherer.daily_forecast(days)
        prefix = f"Here's your {days}-day forecast"
        text, entities = format_forecast_with_bold_times(forecast_lines, prefix)
        await update.message.reply_text(text, entities=entities)
        # show start menu again
        await send_start_menu(update, context)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number between 1 and 16.")
        return "DAYS_INPUT"

async def handle_hours_input(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    # Check if this is a menu button - if so, handle it as a menu button
    if text in MENU_BUTTONS:
        return await handle_button_text(update, context)
    
    try:
        hours = int(text)
        forecast_lines = weatherer.hourly_forecast(hours)
        prefix = f"Here's your {hours}-hours forecast"
        text, entities = format_forecast_with_bold_times(forecast_lines, prefix)
        await update.message.reply_text(text, entities=entities)
        # show start menu again
        await send_start_menu(update, context)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return "HOURS_INPUT"

async def handle_city_input(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    

    if text in MENU_BUTTONS:
        return await handle_button_text(update, context)
    
    city = text
    await update.message.reply_text("Searching for city...")
    results = weatherer.get_reverse_location(city)
    if not results:
        await update.message.reply_text(f"No matching locations found for {city}. Try again.")
        return "CITY_INPUT"
    # store candidates in user_data for later selection
    context.user_data['loc_candidates'] = results

    # build inline keyboard: each button shows "State - COUNTRY_CODE"
    buttons = []
    for i, cand in enumerate(results):
        state = cand.get('state') or ''
        country = cand.get('country_code') or ''
        text = f"{state} - {country}" if state or country else cand.get('display_name','')
        buttons.append([tg.InlineKeyboardButton(text, callback_data=f"LOC_{i}")])
    reply_markup = tg.InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Multiple matches found — choose the correct one:", reply_markup=reply_markup)
    return "CITY_SELECT"

async def handle_pass_service(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    # Check if this is a menu button - if so, handle it as a menu button
    if text in MENU_BUTTONS:
        return await handle_button_text(update, context)
    
    service = text
    context.user_data['pass_service'] = service
    await update.message.reply_text("Enter desired length (4-128):")
    return "PASS_LENGTH"

async def handle_pass_length(update: tg.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    # Check if this is a menu button - if so, handle it as a menu button
    if text in MENU_BUTTONS:
        return await handle_button_text(update, context)
    
    try:
        length = int(text)
        if length < 4 or length > 128:
            await update.message.reply_text("Please enter a number between 4 and 128.")
            return "PASS_LENGTH"
        service = context.user_data.get('pass_service', 'telegram')
        user = update.effective_user
        user_id = user.id
        username = user.username or '' 
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # generate and save via Main-pass helpers
        pwd = passmod.generate_password(length)
        try:
            passmod.save_password_for_user(user_id, service, username, pwd, now)
        except Exception as e:
            logger.exception("Failed to save password: %s", e)
        await update.message.reply_text(f"Generated password: {pwd}")
        await send_start_menu(update, context)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return "PASS_LENGTH"

async def help_command(update: tg.Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to test this bot")


if __name__ == '__main__':
    #Base_Url = 'https://tapi.bale.ai/bot'
    application = ApplicationBuilder().token('YOUR_TOKEN').build()
    
    # Create a filter for main menu buttons
    def is_menu_button(message_text):
        buttons = [
            "Current Weather", "Daily Forecast", "Hourly Forecast",
            "Set city", "Generate Password", "My Passwords",
            "Portfolio", "Prices"
        ]
        return message_text in buttons
    
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_text),    
            CallbackQueryHandler(button)
        ],
        states={
            "DAYS_INPUT": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_days_input)],
            "HOURS_INPUT": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hours_input)],
            "CITY_INPUT": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_input)],
            "CITY_SELECT": [CallbackQueryHandler(button)],
            "PASS_SERVICE": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pass_service)],
            "PASS_LENGTH": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pass_length)],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_text)
        ]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("Help", help_command))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("Portfolio",Price_Fetcher.send_portfolio))
    application.add_handler(CommandHandler("Prices",Price_Fetcher.send_prices))

    application.run_polling(allowed_updates=tg.Update.ALL_TYPES)

