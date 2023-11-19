import discord
import os
import whisper
import asyncio
import pytube
import queue
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import random
import threading
from queue import Queue
import multiprocessing
from llama_cpp import Llama
from LLama_prompt_wrapper import make_chat_prompt
import queue
import time
from gtts import gTTS

from keywords import (
    keywords_stopmusic,
    keywords_skipmusic,
    keywords_playmusic,
    keywords_clearmusicqueue,
    keywords_shufflemusicqueue,
    keywords_weather,
    keywords_searchcommands,
    keywords_rickroll,
    keywords_playlist1,
    keywords_llm
)

from settings import (
    channel_connect_ID,
    user_discord_ID_white_list,
    youtube_search_log_channel_ID,
    commands_log_channel_ID,
    ytdl_format_options,
    ffmpeg_options,
    llm_model_path,
    whisper_model,
    n_ctx,
    n_gpu_layers,
    n_batch,
    n_threads,
    DISCORD_BOT_TOKEN
)

#load in models
model = whisper.load_model(whisper_model, device="cuda") #speech to text

llm = Llama(model_path = llm_model_path, 
                 n_ctx = n_ctx,
                 n_gpu_layers = n_gpu_layers,
                 n_batch = n_batch,
                 n_threads = n_threads) #text to speech


vc =  None
channel = None

async def queueTTS_checker(vc, tts_queue):
    while True:
        await asyncio.sleep(0.3)
        with tts_shared_lock:
            # Wait for some time before checking the queue again
            await asyncio.sleep(1)
            if not tts_queue.empty():
                if not vc.is_playing():
                    tts_text = tts_queue.get()
            else:
                continue
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
async def start_transcription(audio_queue, lock):
    while True:
        # Wait for some time before checking the queue again
        await asyncio.sleep(0.1)

        # Check if there is any data in the queue
        if audio_queue.qsize() > 0:
            if not lock.locked():
                with lock:
                    audio_data, user_ID_ = audio_queue.get()
                    # Transcribe the audio data
                filename = f"audio_{random.randint(0, 10000000)}.wav"
                with open(filename, "wb") as f:
                    f.write(audio_data)
                
                model_input_queue.put([filename, user_ID_])

async def start_transcription2(model_input_queue, lock2):
    while True:
        # Wait for some time before checking the queue again
        await asyncio.sleep(0.1)

        # Check if there is any data in the queue
        if model_input_queue.qsize() > 0:
            with lock2:
                filename, user_ID_ = model_input_queue.get()
                # Transcribe the audio data
                text_raw = model.transcribe(filename)["text"]
                os.remove(filename)

            # Put the transcribed text into the queue for the main thread to process
            text_queue.put([text_raw, user_ID_])

# Define a function for running the transcription in a separate thread
def run_transcription(audio_queue, lock):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_transcription(audio_queue, lock))

def run_transcription2(model_input_queue, lock2):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_transcription2(model_input_queue, lock2))

#text to commands processer
async def process_commands(vc):
    while True:

        # Get the next transcribed text from the queue
        # Wait for some time before checking the queue again
        await asyncio.sleep(1)

        # Check if there is any data in the queue
        if text_queue.qsize() > 0:
            text_raw, user_id = text_queue.get()
            print(f"Audio Transcribed of user: {user_id} | {text_raw}")
            text = text_raw.lower().replace(".", "").replace("!", "").replace(",", "").replace(" ","").replace("?", "").replace("'", "").replace("-", "")
            print(f"Processed: {text}")

            keywords = keywords_list_voice_commands
            matched_keywords = [keyword for keyword in keywords if keyword in text]
            
            if matched_keywords.__len__() > 0:
                text = matched_keywords[0]

                #youtube searhes
                if any(keyword in text for keyword in ["youtubesearch", "youtubessearch", "youshouldsearch"]):
                    search_command = text_raw.lower()
                    search_command = search_command.split("youtube search")
                    search_command = search_command[-1].split("youtube's search")
                    search_command = search_command[-1].split("you should search")
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
                                except:
                                    return None

                #youtube searhes
                if any(keyword in text for keyword in ["wikipediasearch"]):
                    search_command = text_raw.split("Wikipedia search")
                    if search_command[-1].lower().replace(".", "").replace(" ", ""). replace("!", "").replace(",","") not in [".", ",", "!", "wikipediasearch", "ed.", 'ed', "ed!", "ed,", "wikipediasearched", "."]:
                        search_term = search_command[-1]   
                        tts_text = wikipedia_search(search_term)[0:2000]      
                        #await bot.get_channel(channel_connect_ID).send(tts_text, tts=True)
                        tts_queue.put(tts_text)
                
                 #youtube searhes
                if any(keyword in text for keyword in keywords_llm):
                    search_command = text_raw
                    LLM_queue.put(text_raw)
                    
                
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

                elif text in keywords_clearmusicqueue:
                    await bot.get_channel(commands_log_channel_ID).send("!clearmusicqueue") 
                    video_urls_queue.queue.clear()

                elif text in keywords_shufflemusicqueue:
                    await bot.get_channel(commands_log_channel_ID).send("!shufflemusicqueue") 
                    video_urls_list = list(video_urls_queue.queue)
                    random.shuffle(video_urls_list)
                    video_urls_queue.queue.clear()
                    for url in video_urls_list:
                        video_urls_queue.put(url)

                elif text in keywords_dict_memes:
                    await bot.get_channel(commands_log_channel_ID).send(f"!{text}") 
                    if vc.is_playing():
                        vc.stop()
                    url = keywords_dict_memes[text]
                    video_urls_queue.queue.appendleft(url)

                elif text in keywords_dict_playlists:
                    await bot.get_channel(commands_log_channel_ID).send(f"!{text}") 
                    if vc.is_playing() or vc.is_paused():
                        vc.stop()
                    url_playlist1 = keywords_dict_playlists[text] 
                    playlist = pytube.Playlist(url_playlist1)
                    video_urls = list(playlist.video_urls)
                    random.shuffle(video_urls)
                    for video_url in video_urls:
                        video_urls_queue.queue.appendleft(video_url) 

#recording discord audio loop
async def start_recording_thread(vc,channel, audio_queue):
    for i in range(8000):
        if vc.is_connected() is True:
            print(i)
            await asyncio.sleep(1)
            vc.start_recording(discord.sinks.WaveSink(),  lambda *args: callback(*args, audio_queue))
            
            if vc.recording:
                print("Start recording")
                await asyncio.sleep(6) # # record for 6 seconds
                vc.stop_recording()
                print("Stopped recording")
        else: 
            print("not connected")
            vc = await channel.connect()

#logging functions
async def log_commands_discord(bot, user_id, text_raw, url, channel, bot_queue = False):
    if bot_queue is False:
        user_name = await bot.fetch_user(user_id)
    else:
        user_name = "Bot_queue_next"
        user_id = "Bot_queue_next"
        text_raw = "Next Song"
    await bot.get_channel(channel).send(f"User Name: {user_name} \nUser ID: {user_id} \nCommand: {text_raw} \nPlaying youtube search: {url}")

# create a dictionary with the keywords and URLs (Note that the link is added as last position of the the keywords)
def create_keywords_dict(keyword_lists):
    keywords_dict = {}
    for keyword_list in keyword_lists:
        for keyword in keyword_list:
            keywords_dict[keyword] = keyword_list[-1]
    return keywords_dict


keywords_dict_memes = create_keywords_dict([keywords_rickroll])
keywords_dict_playlists = create_keywords_dict([keywords_playlist1])

#add all keywords to one list
keywords_lists = [keywords_stopmusic, keywords_skipmusic, keywords_playmusic, keywords_clearmusicqueue, keywords_shufflemusicqueue, keywords_searchcommands, keywords_playlist1, keywords_weather, keywords_rickroll,keywords_llm]
keywords_list_voice_commands = []

for sublist in keywords_lists:
    keywords_list_voice_commands.extend(sublist)


#youtube music
# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

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
    global channel
    if text is not None or text is not '':
        language = "en"
        tts = gTTS(text=text, lang=language, tld="com.au", slow=False,)
        tts_filename = f"audio_tts_{random.randint(0, 1000)}.mp3"
        tts.save(tts_filename)

        if vc.is_connected() is False:
            if vc.is_connected() is not True:
                try:
                    vc = await channel.connect()
                except:
                    print('test')

        vc.play(discord.FFmpegPCMAudio(tts_filename))

        while vc.is_playing():
            await asyncio.sleep(1)
            if vc.is_connected() is not True:
                try:
                    vc = await channel.connect()
                except:
                    continue
        os.remove(tts_filename)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("$"),
    description='Relatively simple music bot example',
    intents=intents,)

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
                video_urls_queue.queue.appendleft(video_url)
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

@bot.command(name='clear', help='Clear the queue.')
async def show_queue(ctx):
    video_urls_queue.queue.clear()
    await ctx.send('The queue is cleared')

#LLM 
class LLM_speech:
    def __init__(self, llm, completion, LLM_queue,tts_queue, tts_shared_lock, speech_rate=120):
        global vc
        print("initiate LLM_speech object")
        self.llm = llm
        self.completion = completion
        self.token_buffer = []
        self.sentence_queue = queue.Queue()
        self.token_queue = queue.Queue()
        self.lock = threading.Lock()
        self.token_lock = threading.Lock()
        self.sentence_lock = threading.Lock()
        self.all_tokens_generated = False
        self._exit_flag = False
        self.discord_vc = vc

        self.LLM_queue = LLM_queue
        self.tts_queue = tts_queue
        self.tts_shared_lock = tts_shared_lock

        # Start a separate thread for token generation
        self.tokens_thread = threading.Thread(target=self.add_tokens)
        self.tokens_thread.start()

        # Start a separate thread for token generation
        self.sentence_thread = threading.Thread(target=self.tokens_to_sentence_thread)
        self.sentence_thread.start()

        # Start a separate thread for speech generation
        self.speech_thread = threading.Thread(target=self._speech_thread)
        self.speech_thread.start()

    def add_tokens(self):
        for token in self.completion:
            if token == self.llm.token_eos():
                break

            while not self.token_lock.acquire(timeout=1.0):
                # Wait for the lock to be acquired
                time.sleep(0.1)
                pass

            try:
                self.token_buffer.append(token)
            finally:
                self.token_lock.release()
        
        self.all_tokens_generated = True
        
    def tokens_to_sentence_thread(self):
        while True:
            with self.token_lock:
                if len(self.token_buffer) > 20 or self.all_tokens_generated == True:
                    # Detokenize and convert to text
                    sentence = self.llm.detokenize(self.token_buffer).decode("utf-8")

                    if sentence == "":
                        # Optionally, you can set a flag to signal the thread to exit
                        self._exit_flag = True
                        break  # Exit the loop and thread

                    # Add tokens to the sentence queue
                    with self.sentence_lock:
                        self.sentence_queue.put(sentence)

                    # Empty the token buffer
                    self.token_buffer.clear()
                else:
                    # Optional: You can add a sleep to avoid continuous checking and reduce CPU usage
                    time.sleep(0.1)  # Adjust the sleep duration as needed

    def _speech_thread(self): 
       
        while True:
            if self._exit_flag == True and self.sentence_queue.empty():
                break
            with self.lock:
                if not self.sentence_queue.empty():
                    sentence = self.sentence_queue.get()

                    if sentence is None or sentence is '':
                        self.close()

                    print(sentence)

                    with self.tts_shared_lock:
                        self.tts_queue.put(sentence)
                else:
                    # Optional: You can add a sleep to avoid continuous checking and reduce CPU usage
                    time.sleep(0.1)  # Adjust the sleep duration as needed

    def close(self):
        # Signal the token thread and speech thread to exit
        self.tokens_thread.join()
        self.sentence_thread.join()


#@bot.slash_command()
def llm_command(user_input, LLM_queue,tts_queue, tts_shared_lock):
    tokens = make_chat_prompt(
        llm,
        user_input,
    )

    completion = llm.generate(
        tokens=tokens,
    )

    # Example usage:
    # Create an instance of LLM_speech
    llm_speech = LLM_speech(llm=llm, completion=completion, LLM_queue=LLM_queue,tts_queue=tts_queue, tts_shared_lock=tts_shared_lock)

    # Close the instance when done
    llm_speech.close()

#run
@bot.event
async def on_ready():
    global vc, channel
    
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
    
def llm_process(LLM_queue, tts_queue, tts_shared_lock):
    while True:
        user_input = LLM_queue.get()
        if user_input is None:
            break  # Exit the loop if sentinel value is received
        llm_command(user_input=user_input, LLM_queue=LLM_queue,tts_queue=tts_queue, tts_shared_lock=tts_shared_lock)
        print(f"Running LLM process on: {user_input}")

def start_llm_process(LLM_queue,tts_queue, tts_shared_lock):
    llm_process(LLM_queue,tts_queue, tts_shared_lock)


if __name__ == "__main__":

    # Define the audio and text queues
    audio_queue = Queue()
    text_queue = Queue()
    model_input_queue = Queue()
    video_urls_queue = queue.Queue()

    # Create a lock (prefent the threads from accessing something at same time)
    lock = threading.Lock()
    lock2 = threading.Lock()


    with multiprocessing.Manager() as manager:

        LLM_queue = manager.Queue()
        
        tts_queue = manager.Queue()
        tts_shared_lock = manager.Lock()

        # main/first multiprocess
        num_threads = 8
        threads = [threading.Thread(target=run_transcription,  args=(audio_queue, lock)) for i in range(num_threads)]
        threads2 = [threading.Thread(target=run_transcription2,  args=(model_input_queue, lock2)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads2:
            thread.start()

        # Start the LLM process that gets triggered by the first one every time in the non-stop loop the queue gets added a string
        llm_process = multiprocessing.Process(target=start_llm_process, args=(LLM_queue, tts_queue, tts_shared_lock),)
        llm_process.start()

        LLM_queue.put("hello")

        bot.run(DISCORD_BOT_TOKEN)