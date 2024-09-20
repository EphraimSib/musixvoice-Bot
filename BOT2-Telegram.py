import os
from spotipy import SpotifyClientCredentials
from spotipy import util
import spotipy
from telegram import Update, Bot, InputMediaPhoto
from telegram.ext import Updater, ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
import speech_recognition as sr
import logging
import requests
import aiohttp

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Set up your Spotify API credentials
client_id = 'f82b3bb5008e449b83832ba241b30ef7'
client_password = '0c87e84a36aa41079f0df8886bd9795b'

# Set up your Spotify client
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_password)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Set up your Telegram bot token
TOKEN = '7306844635:AAFCDEaQaowEHtUBGuyEbcgGUPmrAw8T-GA'

def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a music recognition bot! Send me a voice message, and I'll try to recognize the song.")

async def recognize_song(update: Update, context: CallbackContext):
    """Recognize the song in the voice message."""
    file_id = update.message.voice.file_id
    file = await context.bot.get_file(file_id)
    file_path = file.file_path
    async with aiohttp.ClientSession() as session:
        async with session.get(file_path) as response:
            with open('voice.ogg', 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)

    # Convert the ogg file to wav
    try:
        os.system('ffmpeg -i voice.ogg voice.wav')
    except Exception as e:
        logger.error(f"Error converting ogg to wav: {e}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="Error converting audio file.")
        return

    # Recognize the song using speech recognition
    r = sr.Recognizer()
    try:
        with sr.AudioFile('voice.wav') as source:
            audio = r.record(source)
            try:
                text = r.recognize_google(audio)
                logger.info(f"Recognized text: {text}")
            except sr.UnknownValueError:
                logger.error("Google Speech Recognition could not understand your audio")
                context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't understand the audio.")
                return
            except sr.RequestError as e:
                logger.error(f"Could not request results from Google Speech Recognition service; {e}")
                context.bot.send_message(chat_id=update.effective_chat.id, text="Error recognizing audio.")
                return
    except Exception as e:
        logger.error(f"Error recognizing song: {e}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="Error recognizing song.")
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
        lyrics = sp.track(track_id)['lyrics']['lyrics']['text']

        # Send album cover
        album_cover = requests.get(album_cover_url).content
        with open('album_cover.jpg', 'wb') as f:
            f.write(album_cover)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('album_cover.jpg', 'rb'), caption=f"Artist: {artist_name}\nTrack: {track_name}\nAlbum: {album_name}")

        # Send lyrics
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Lyrics:\n{lyrics}")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't find any songs matching your query.")

def search_song(update: Update, context: CallbackContext):
    """Search for a song on Spotify."""
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
        lyrics = sp.track(track_id)['lyrics']['lyrics']['text']

        # Send album cover
        album_cover = requests.get(album_cover_url).content
        with open('album_cover.jpg', 'wb') as f:
            f.write(album_cover)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('album_cover.jpg', 'rb'), caption=f"Artist: {artist_name}\nTrack: {track_name}\nAlbum: {album_name}")

        # Send lyrics
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Lyrics:\n{lyrics}")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't find any songs matching your query.")

def main():
    """Start the bot."""
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    recognize_song_handler = MessageHandler(filters.VOICE, recognize_song)
    search_song_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, search_song)

    application.add_handler(start_handler)
    application.add_handler(recognize_song_handler)
    application.add_handler(search_song_handler)

    application.run_polling()
    application.idle()

if __name__ == '__main__':
    main()
