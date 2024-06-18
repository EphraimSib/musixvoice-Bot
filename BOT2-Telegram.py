import os
from spotipy import SpotifyClientCredentials
from spotipy import util
import spotipy
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, filters
import speech_recognition as sr


# Set up your Spotify API credentials
client_id = 'f82b3bb5008e449b83832ba241b30ef7'
client_password = '0c87e84a36aa41079f0df8886bd9795b'

# Set up your Spotify client
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_password)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Set up your Telegram bot token
TOKEN = '7306844635:AAFCDEaQaowEHtUBGuyEbcgGUPmrAw8T-GA'

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a music recognition bot! Send me a voice message, and I'll try to recognize the song.")

def recognize_song(update: Update, context: CallbackContext):
    file_id = update.message.voice.file_id
    file = context.bot.get_file(file_id)
    file.download('voice.ogg')

    # Convert the ogg file to wav
    os.system('ffmpeg -i voice.ogg voice.wav')

    # Recognize the song using speech recognition
    r = sr.Recognizer()
    with sr.AudioFile('voice.wav') as source:
        audio = r.record(source)
        try:
            text = r.recognize_google(audio)
            print(text)
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand your audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))

    # Search for the song on Spotify
    results = sp.search(q=text, type='track')
    if results['tracks']['total'] > 0:
        track = results['tracks']['items'][0]
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"I think the song is {track['name']} by {track['artists'][0]['name']}!")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="I couldn't recognize the song.")

def main():
    # Initialize the Bot with your bot token
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(filters.Voice, recognize_song))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()