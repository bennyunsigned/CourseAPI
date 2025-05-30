import yt_dlp
import time

url = 'https://www.youtube.com/watch?v=nwrSD4m9up8'
output_path = '.'

last_print_time = 0

def progress_hook(d):
    global last_print_time
    if d['status'] == 'downloading':
        now = time.time()
        if now - last_print_time >= 1:
            percent = d.get('_percent_str', '').strip()
            print(f"Percentage of download: {percent}")
            last_print_time = now

ydl_opts = {
    'outtmpl': f'{output_path}/%(title)s.%(ext)s',
    'format': 'bestvideo+bestaudio/best',
    'progress_hooks': [progress_hook],
    # 'cookiefile': '/path/to/cookies.txt',  # Uncomment if you need cookies
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
