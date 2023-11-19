#channel connect ID:
channel_connect_ID =  "YOUR_CHANNEL_ID"
#user_white_list
user_discord_ID_white_list = ["person1_ID", "person2..."]
#server: bot_logs Bot_teting_env 
youtube_search_log_channel_ID = "TEX_CHANNEL_ID"
commands_log_channel_ID = "TEX_CHANNEL_ID"


DISCORD_BOT_TOKEN = "YOUR_TOKEN"

#ytdl_format_options
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

#ffmpeg_options
ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

#Whisper model
whisper_model = "tiny.en"

#LLM_speech options
llm_model_path = "C:/Users/PC/Desktop/llm/llama-2-7b-chat.ggmlv3.q2_K.bin" #exmaple
n_ctx = 1024,
n_gpu_layers = 1024,
n_batch = 512,
n_threads = 3