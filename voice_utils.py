import io
import logging
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def send_audio_response(update: Update, text: str, language: str) -> None:
    """Converts text to speech and sends it as a voice message."""
    try:
        tts = gTTS(text=text, lang=language, slow=False)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        await update.message.reply_voice(audio_bytes)
        logger.info(f"Sent audio response: {text[:50]}...")
    except Exception as e:
        logger.error(f"Error sending audio response: {e}")
        # Fallback to text if audio fails
        await update.message.reply_text(text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE, user_languages: dict) -> None:
    """Handle voice messages and transcribe them using SpeechRecognition, then send to Gemini."""
    user_id = update.effective_user.id
    language = user_languages.get(user_id, "en") # Default to English if no language is set

    voice_file = await update.message.voice.get_file()
    voice_bytes = io.BytesIO()
    await voice_file.download_to_memory(voice_bytes)
    voice_bytes.seek(0) # Reset stream position

    logger.info(f"User {user_id} sent a voice message. (Language: {language})")

    try:
        await update.message.chat.send_action("typing") # Show "typing..." status

        # Convert OGG to WAV for SpeechRecognition
        audio = AudioSegment.from_file(voice_bytes, format="ogg")
        wav_bytes = io.BytesIO()
        audio.export(wav_bytes, format="wav")
        wav_bytes.seek(0)

        r = sr.Recognizer()
        with sr.AudioFile(wav_bytes) as source:
            audio_data = r.record(source)
            
        # Use Google Web Speech API for transcription
        transcribed_text = r.recognize_google(audio_data, language=language)
        logger.info(f"Transcribed text: {transcribed_text}")

        # Send transcribed text to Gemini (this part will be handled in main.py after transcription)
        context.user_data['transcribed_text'] = transcribed_text # Store for main.py to use
        context.user_data['language'] = language # Store language for main.py to use
        
        # This function will now return the transcribed text to be processed by main.py
        # For now, we'll just log and let main.py handle the Gemini interaction.
        # The actual Gemini interaction will be moved to main.py's echo or a new handler.
        # For now, just return the transcribed text.
        return transcribed_text

    except sr.UnknownValueError:
        await update.message.reply_text("Sorry, I could not understand the audio.")
        logger.warning(f"Speech Recognition could not understand audio from user {user_id}")
        return None
    except sr.RequestError as e:
        await update.message.reply_text(f"Could not request results from Google Speech Recognition service; {e}")
        logger.error(f"Speech Recognition service error for user {user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"An error occurred while processing voice: {e}")
        await update.message.reply_text("An error occurred while processing your voice message. Please try again later.")
        return None
