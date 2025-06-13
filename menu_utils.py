import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from voice_utils import send_audio_response # Assuming send_audio_response is available

# Assuming user_languages is accessible or passed
# For now, we'll assume it's passed or imported if needed.
# If user_languages is truly global and needs to be shared,
# it might be better to pass it as an argument or use a shared context.
# For this example, we'll assume it's passed to the handler.

logger = logging.getLogger(__name__)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with inline buttons for a complex task."""
    keyboard = [
        [
            InlineKeyboardButton("Option A", callback_data="menu_option_a"),
            InlineKeyboardButton("Option B", callback_data="menu_option_b"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please choose an option from the menu:", reply_markup=reply_markup)
    logger.info(f"User {update.effective_user.id} requested menu.")

async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user_languages: dict) -> None:
    """Handles callback queries from the menu buttons."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query

    choice = query.data.replace("menu_", "")
    user_id = query.from_user.id
    language = user_languages.get(user_id, "en") # Get user's language

    response_text = ""
    if choice == "option_a":
        response_text = f"You chose Option A. I can now proceed with tasks related to Option A in {language.upper()}."
    elif choice == "option_b":
        response_text = f"You chose Option B. I can now proceed with tasks related to Option B in {language.upper()}."
    else:
        response_text = "Invalid option selected."

    await query.edit_message_text(text=response_text)
    # Optionally, you can send an audio response for menu choices too
    # Use query.message to reply to the message that contained the inline keyboard
    await send_audio_response(query.message, response_text, language)
    logger.info(f"User {user_id} chose menu option: {choice}")
