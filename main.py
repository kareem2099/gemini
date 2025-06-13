import google.generativeai as genai
import os
import logging
import io # Import io for handling image bytes
from dotenv import load_dotenv # Import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton # Import InlineKeyboardMarkup and InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler # Import CallbackQueryHandler

# Load environment variables from .env file
load_dotenv()

# Dictionary to store user language preferences (user_id: language_code)
user_languages = {}

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET/POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Configure the Gemini API with your API key
# It's recommended to store your API key securely, e.g., in an environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("Error: GEMINI_API_KEY environment variable not set.")
    logger.error("Please set the GEMINI_API_KEY environment variable with your Gemini API key.")
    # Removed exit(1) as load_dotenv handles this more gracefully

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
chat = model.start_chat(history=[])

# Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual Telegram Bot Token
# It's recommended to store your bot token securely, e.g., in an environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    logger.error("Please set the TELEGRAM_BOT_TOKEN environment variable with your Telegram Bot Token.")
    # Removed exit(1) as load_dotenv handles this more gracefully

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued, offering language choices."""
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("Русский (ru)", callback_data="lang_ru"),
            InlineKeyboardButton("English (en)", callback_data="lang_en"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        f"Hi {user.mention_html()}! Please choose your preferred language:",
        reply_markup=reply_markup,
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the user's language."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query

    language_code = query.data.replace("lang_", "")
    user_languages[query.from_user.id] = language_code
    logger.info(f"User {query.from_user.id} set language to {language_code}")

    await query.edit_message_text(text=f"Language set to: {language_code.upper()}. Now you can send me messages!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message using Gemini AI, considering the selected language."""
    user_message = update.message.text
    user_id = update.effective_user.id
    language = user_languages.get(user_id, "en") # Default to English if no language is set

    logger.info(f"User message: {user_message} (Language: {language})")

    try:
        # Construct a language-aware prompt
        prompt_prefix = f"Respond in {language.upper()}."
        
        # Check if the user is asking for code
        if any(keyword in user_message.lower() for keyword in ["code", "html", "css", "solve this code"]):
            prompt = f"{prompt_prefix} Please provide the response as a single, complete markdown code block. User message: {user_message}"
        else:
            prompt = f"{prompt_prefix} User message: {user_message}"
            
        response = chat.send_message(prompt)
        await update.message.reply_text(response.text)
        logger.info(f"Gemini response: {response.text}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        await update.message.reply_text("An error occurred while processing your request. Please try again later.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages and send them to Gemini."""
    user_id = update.effective_user.id
    language = user_languages.get(user_id, "en") # Default to English if no language is set

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = io.BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0) # Reset stream position to the beginning

    logger.info(f"User {user_id} sent a photo. (Language: {language})")

    try:
        await update.message.chat.send_action("typing") # Show "typing..." status
        
        # Prepare the image for Gemini
        image_part = {
            'mime_type': 'image/jpeg', # Assuming JPEG, adjust if needed
            'data': photo_bytes.getvalue()
        }
        
        # Get optional caption from the user
        caption = update.message.caption if update.message.caption else ""
        
        # Construct a language-aware prompt for multimodal input
        prompt_text = f"Respond in {language.upper()}. Analyze this image. {caption}"
        
        # Send both text and image to Gemini
        response = chat.send_message([prompt_text, image_part])
        await update.message.reply_text(response.text)
        logger.info(f"Gemini response to photo: {response.text}")

    except Exception as e:
        logger.error(f"An error occurred while processing photo: {e}")
        await update.message.reply_text("An error occurred while processing your image. Please try again later.")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # On callback queries (for language selection)
    application.add_handler(CallbackQueryHandler(button, pattern="^lang_"))

    # On non-command messages - echo the message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # On photo messages - handle photo
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot started. Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
