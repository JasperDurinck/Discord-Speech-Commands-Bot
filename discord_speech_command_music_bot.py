import discord
import os
import whisper
import asyncio
import pytube
import queue
from discord.ext import commands
import yt_dlp as youtube_dl
import random
import threading
from queue import Queue
from wikipedia_api import wikipedia_search
from weather_API import get_weather_info
from gtts import gTTS



# Define the audio and text queues
audio_queue = Queue()
text_queue = Queue()
video_urls_queue = queue.Queue()
tts_queue = queue.Queue()

async def queueTTS_checker(vc, tts_queue):
    while True:
        # Wait for some time before checking the queue again
        await asyncio.sleep(1)
        
        if not tts_queue.empty():
            if not vc.is_playing():
                tts_text = tts_queue.get()
                await tts_gtts(vc, tts_text)

async def queue_checker(vc, video_urls_queue):
    while True:
        # Wait for some time before checking the queue again
        await asyncio.sleep(0.3)

        if not video_urls_queue.empty():
            if vc.is_playing() is False and vc.is_paused() is False:
                url = video_urls_queue.get()
                await log_commands_discord(bot, "Bot_queue", "Next song", url, youtube_search_log_channel_ID, bot_queue = True)
                await play_song(url, vc)

async def callback(sink: discord.sinks, audio_queue):

    for user_id, audio in sink.audio_data.items():
        if user_id in user_discord_ID_white_list:
            audio: discord.sinks.core.AudioData = audio
            audio_queue.put([audio.file.getvalue(), user_id])

#audio to text by whisper model with additional threads if text queue is not empty
async def start_transcription(audio_queue, text_queue):
    while True:
        # Wait for some time before checking the queue again
        await asyncio.sleep(0.1)

        # Check if there is any data in the queue
        if audio_queue.qsize() > 0:
            # Get the next audio data from the queue
            audio_data, user_ID_ = audio_queue.get()
            
            # Transcribe the audio data
            filename = f"audio_{random.randint(0, 1000)}.wav"
            with open(filename, "wb") as f:
                f.write(audio_data)
            #text_raw = model.transcribe(filename)["text"]
            text_raw = model.transcribe(filename)["text"]
            os.remove(filename)

            # Put the transcribed text into the queue for the main thread to process
            text_queue.put([text_raw, user_ID_])

# Define a function for running the transcription in a separate thread
def run_transcription():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_transcription(audio_queue, text_queue))

# Start multiple threads for running the transcription
num_threads = 8
threads = [threading.Thread(target=run_transcription) for i in range(num_threads)]
for thread in threads:
    thread.start()



#text to commands processer
async def process_commands(vc):
    while True:

        # Get the next transcribed text from the queue
        # Wait for some time before checking the queue again
        await asyncio.sleep(0.1)

        # Check if there is any data in the queue
        if text_queue.qsize() > 0:
            text_raw, user_id = text_queue.get()
            print(text_raw)
            text = text_raw.lower().replace(".", "").replace("!", "").replace(",", "").replace(" ","").replace("?", "").replace("'", "").replace("-", "")
            print(text)
            keywords = keywords_list_voice_commands
            matched_keywords = [keyword for keyword in keywords if keyword in text]
            

            if matched_keywords.__len__() > 0:
                text = matched_keywords[0]

                #youtube searhes
                if "youtubesearch" in text or "youtubessearch" in text or  "youshouldsearch" in text:
                    search_command = text_raw.split("youtube search")
                    if search_command[-1].lower().replace(".", "").replace(" ", ""). replace("!", "").replace(",","") not in [".", ",", "!", "youtubesearch", "ed.", 'ed', "ed!", "ed,", "youtubesearched", "youtubesearch."]:
                        search_term = search_command[-1]
                        with ytdl as ydl:
                                try:
                                    result = ydl.extract_info(f"ytsearch:{search_term} category:music", download=False)['entries'][0]
                                    search_url = result['webpage_url']

                                    if vc.is_playing() or vc.is_paused():
                                        vc.stop()

                                    url = search_url
                                    video_urls_queue.queue.appendleft(url)
                                    #await log_commands_discord(bot, user_id, text_raw, url, channel = youtube_search_log_channel_ID)
                                except:
                                    return None

                #youtube searhes
                if "wikipediasearch" in text:
                    search_command = text_raw.split("Wikipedia search")
                    if search_command[-1].lower().replace(".", "").replace(" ", ""). replace("!", "").replace(",","") not in [".", ",", "!", "wikipediasearch", "ed.", 'ed', "ed!", "ed,", "wikipediasearched", "."]:
                        search_term = search_command[-1]   
                        tts_text = wikipedia_search(search_term)[0:1000]      
                        #await bot.get_channel(channel_connect_ID).send(tts_text, tts=True)
                        tts_queue.put(tts_text)
                
                #youtube searhes
                if text in keywords_weather:  
                        tts_text = get_weather_info()
                        tts_queue.put(tts_text)

                #voice commands
                if  text in keywords_playmusic:
                    await bot.get_channel(commands_log_channel_ID).send("!play music")
                    if vc.is_paused():
                        vc.resume()
                    elif video_urls_queue.empty():
                        await bot.get_channel(commands_log_channel_ID).send("Queue empty!!!")    

                elif text in keywords_skipmusic:
                    await bot.get_channel(commands_log_channel_ID).send("!skip")
                    if vc.is_playing():
                        vc.stop()

                elif text in keywords_stopmusic:
                    await bot.get_channel(commands_log_channel_ID).send("!stop") 
                    if vc.is_playing():
                        vc.pause()

#recording discord audio loop
async def start_recording_thread(vc,channel, audio_queue):
    i = 0 
    while i <= 10000:
        if vc.is_connected() is True:
            print(i)
            await asyncio.sleep(0.1)
            vc.start_recording(discord.sinks.WaveSink(),  lambda *args: callback(*args, audio_queue))
            
            if vc.recording:
                print("Start recording")
                await asyncio.sleep(6) # # record for 12 seconds
                vc.stop_recording()
                print("Stopped recording")
        else: 
            print("not connected")
            vc = await channel.connect()
        i += 1


#logging functions
async def log_commands_discord(bot, user_id, text_raw, url, channel, bot_queue = False):
    if bot_queue is False:
        user_name = await bot.fetch_user(user_id)
    else:
        user_name = "Bot_queue_next"
        user_id = "Bot_queue_next"
        text_raw = "Next Song"
    await bot.get_channel(channel).send(f"User Name: {user_name} \nUser ID: {user_id} \nCommand: {text_raw} \nPlaying youtube search: {url}")

#channel connect ID:
channel_connect_ID =  "VOICE_CHANNEL_ID"

#user_white_list
user_discord_ID_white_list = [] #

#server: bot_logs Bot_teting_env 
youtube_search_log_channel_ID =  "LOG_CHANNEL_ID"
commands_log_channel_ID = "LOG_CHANNEL_ID"

#keywords for commands:
keywords_stopmusic = ["stoppedthemusic", "stopmusic", "stopthemusic",  "stopitplaying", "stopplaying", "stopitplay", "stopplaying", "stoptheplaying"]
keywords_skipmusic = ["Script music","scriptamusic","skipthesong", "skippingthemusic", "skiptomusic", "skipmusic", "skipthemusic", "skipsomeone", "nextmusic", "Skeptomusic"]
keywords_playmusic = ["playedinmusic", "playamusic", "latemusic", "playitmusic", "startsthemusic", "letsplaymusic", "playedmusic", "startthemusic", "startmusic", "Play to music","playingmusic", "playmusic", "playthemusic", "laymusic", "laythemusic", "lateinmusic", "playedamusic", "lakemusic", "ladymusic", "latermusic", "lateatmusic", "playthenews", "playtheabuse", "latetomusic", "claythemusic"]
keywords_weather = ["whatdoestheweather", "whatistheweather", "givemetheweather", "givemethecurrentweather", "searchweather", "isitraining", "whatisthetemprature", "doesthesunshine"]

#keywords search commands
keywords_searchcommands = ["youtubesearch","youtubessearch", "wikipediasearch"]

#add all keywords to one list
keywords_lists = [keywords_stopmusic, keywords_skipmusic, keywords_playmusic, keywords_searchcommands, keywords_weather]
keywords_list_voice_commands = []

for sublist in keywords_lists:
    keywords_list_voice_commands.extend(sublist)


#youtube music

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    'default_search': 'ytsearch10:music', # Only search for music

}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

#speech bot
#bot = discord.Client()
model = whisper.load_model("tiny.en", device="cuda")


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='Relatively simple music bot example',
    intents=intents,)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

async def play_song(url, vc):
    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    vc.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await bot.get_channel(youtube_search_log_channel_ID).send(f'Now playing: {player.title}')
    while vc.is_playing():
        await asyncio.sleep(1)

async def tts_gtts(vc, text):
    language = "en"
    tts = gTTS(text=text, lang=language, tld="com", slow=False,)
    tts_filename = f"audio_tts_{random.randint(0, 1000)}.mp3"
    tts.save(tts_filename)
    vc.play(discord.FFmpegPCMAudio(tts_filename))
    while vc.is_playing():
        await asyncio.sleep(1)
    os.remove(tts_filename)

@bot.command(name='play', help='Add a YouTube video or playlist to the queue.')
async def play(ctx, url):
    # Check if the URL is a valid YouTube video or playlist URL
    if 'youtube.com/watch?v=' in url or 'youtube.com/playlist?list=' in url:
        # Add the video URL(s) to the queue
        if 'youtube.com/watch?v=' in url:
            video_urls_queue.put(url)
            await ctx.send(f'{url} added to the queue!')
        elif 'youtube.com/playlist?list=' in url:
            playlist = pytube.Playlist(url)
            for video_url in playlist.video_urls:
                video_urls_queue.put(video_url)
            #await ctx.send(f'{playlist.title} ({playlist.video_count} videos) added to the queue!')
        global current_url
        current_url = url
    else:
        await ctx.send('Invalid YouTube video or playlist URL.')

@bot.command(name='queue', help='Show some of the songs currently in the queue.')
async def show_queue(ctx, num_songs=5):
    song_list = []
    for i in range(min(num_songs, video_urls_queue.qsize())):
        song_url = video_urls_queue.queue[i]
        video = pytube.YouTube(song_url)
        song_list.append(video.title)
    await ctx.send('Currently in queue:\n' + '\n'.join(song_list))

#run
@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')
    channel = bot.get_channel(channel_connect_ID)
    vc = await channel.connect()
    # Create event loop
    loop = asyncio.get_event_loop()

    # Create tasks for transcription and command processing
    start_recording_thread_task = loop.create_task(start_recording_thread(vc,channel, audio_queue))
    process_commands_task = loop.create_task(process_commands(vc))
    queue_checker_task = loop.create_task(queue_checker(vc, video_urls_queue))
    queueTTS_checker_task = loop.create_task(queueTTS_checker(vc, tts_queue))


    # Run tasks concurrently
    await asyncio.gather(start_recording_thread_task, process_commands_task, queue_checker_task, queueTTS_checker_task)
    


bot.run("TOKEN_DISCORD_BOT")