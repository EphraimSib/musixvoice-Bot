import os
import logging
import requests
import aiohttp
import speech_recognition as sr
from spotipy import SpotifyClientCredentials, Spotify
from telegram import Update, Bot, InputMediaPhoto
from telegram.ext import Updater, ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Set up your Spotify API credentials
client_id = 'f82b3bb5008e449b83832ba241b30ef7'
client_password = '0c87e84a36aa41079f0df8886bd9795b'

# Set up your Spotify client
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_password)
sp = Spotify(client_credentials_manager=client_credentials_manager)

# Set up your Telegram bot token
TOKEN = '7306844635:AAFCDEaQaowEHtUBGuyEbcgGUPmrAw8T-GA'

def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a music recognition bot! Send me a voice message, and I'll try to recognize the song. Or use /search <query> to search for a song by text.")

async def recognize_song(update: Update, context: CallbackContext):
    """Recognize the song in the voice message."""
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Recognizing the song...")
    file_id = update.message.voice.file_id
    file = await context.bot.get_file(file_id)
    file_path = file.file_path
    async with aiohttp.ClientSession() as session:
        async with session.get(file_path) as response:
            with open(f'voice_{update.message.message_id}.ogg', 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)

    # Convert the ogg file to wav
    try:
        os.system(f'ffmpeg -i voice_{update.message.message_id}.ogg voice_{update.message.message_id}.wav')
    except Exception as e:
        logger.error(f"Error converting ogg to wav: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error converting audio file.")
        return

    # Recognize the song using Google Cloud Speech-to-Text
    r = sr.Recognizer()
    try:
        with sr.AudioFile(f'voice_{update.message.message_id}.wav') as source:
            audio = r.record(source)
            try:
                text = r.recognize_google(audio)
                logger.info(f"Recognized text: {text}")
            except sr.UnknownValueError:
                logger.error("Google Speech Recognition could not understand your audio")
                await context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't understand the audio.")
                return
            except sr.RequestError as e:
                logger.error(f"Could not request results from Google Speech Recognition service; {e}")
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Error recognizing audio.")
                return
    except Exception as e:
        logger.error(f"Error recognizing song: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error recognizing song.")
        return

    # Search for the song on Spotify
    search_query = text
    results = sp.search(q=search_query, type='track')
    if results['tracks']['total'] > 0:
        track = results['tracks']['items'][0]
        track_id = track['id']
        track_info = sp.track(track_id)
        artist_name = track_info['artists'][0]['name']
        track_name = track_info['name']
        album_name = track_info['album']['name']
        album_cover_url = track_info['album']['images'][0]['url']

        # Send album cover
        album_cover = requests.get(album_cover_url).content
        with open(f'album_cover_{update.message.message_id}.jpg', 'wb') as f:
            f.write(album_cover)

        # Use the asynchronous send_photo method from telegram.ext
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(f'album_cover_{update.message.message_id}.jpg', 'rb'), caption=f"Artist: {artist_name}\nTrack: {track_name}\nAlbum: {album_name}")

        # Download the audio stream
        try:
            audio_url = track_info['preview_url']
            audio_stream = requests.get(audio_url, stream=True)
            # Set the filename to include artist name and track title
            mp3_filename = f"{artist_name} - {track_name}.mp3"
            with open(mp3_filename, 'wb') as f:
                for chunk in audio_stream.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            logger.error(f"Error downloading audio stream: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Error downloading audio stream.")
            return

        # Send the mp3 file
        await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(mp3_filename, 'rb'), caption=f"Artist: {artist_name}\nTrack: {track_name}\nAlbum: {album_name}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't find any songs matching your query.")

async def search_song(update: Update, context: CallbackContext):
    """Search for a song on Spotify."""

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Searching for the song...")
    search_query = update.message.text.split(' ', 1)[1]
    results = sp.search(q=search_query, type='track')
    if results['tracks']['total'] > 0:
        track = results['tracks']['items'][0]
        track_id = track['id']
        track_info = sp.track(track_id)
        artist_name = track_info['artists'][0]['name']
        track_name = track_info['name']
        album_name = track_info['album']['name']
        album_cover_url = track_info['album']['images'][0]['url']

        # Send album cover
        album_cover = requests.get(album_cover_url).content
        with open(f'album_cover_{update.message.message_id}.jpg', 'wb') as f:
            f.write(album_cover)

        # Use the asynchronous send_photo method from telegram.ext
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(f'album_cover_{update.message.message_id}.jpg', 'rb'), caption=f"Artist: {artist_name}\nTrack: {track_name}\nAlbum: {album_name}")

        # Download the audio stream
        try:
            audio_url = track_info['preview_url']
            audio_stream = requests.get(audio_url, stream=True)
            # Set the filename to include artist name and track title
            mp3_filename = f"{artist_name} - {track_name}.mp3"
            with open(mp3_filename, 'wb') as f:
                for chunk in audio_stream.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            logger.error(f"Error downloading audio stream: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Error downloading audio stream.")
            return

        # Send the mp3 file
        await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(mp3_filename, 'rb'), caption=f"Artist: {artist_name}\nTrack: {track_name}\nAlbum: {album_name}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't find any songs matching your query.")

def main():
    """Start the bot."""
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    recognize_song_handler = MessageHandler(filters.VOICE, recognize_song)
    search_song_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, search_song)
    search_command_handler = CommandHandler('search', search_song)

    application.add_handler(start_handler)
    application.add_handler(recognize_song_handler)
    application.add_handler(search_song_handler)
    application.add_handler(search_command_handler)

    # Register an error handler
    def error_handler(update: Update, context: CallbackContext):
        logger.error(f"Update {update} caused error {context.error}")

    application.add_error_handler(error_handler)

    application.run_polling()
    application.idle()

if __name__ == '__main__':
    main()
