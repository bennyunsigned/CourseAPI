import yt_dlp
import os
import sys

def download_shorts(channel_url, output_dir=None):
    """
    Downloads all shorts from the given YouTube channel URL.
    """
    # Define root directory (2 levels up from this script: Controllers/CourseDetailsCreationsAutomation.py/)
    if output_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(project_root, "shorts_downloader")

    # Ensure the URL points to the shorts tab if it's a channel URL
    # This helps yt-dlp focus on shorts
    if "/@ " in channel_url or "youtube.com/channel/" in channel_url or "youtube.com/c/" in channel_url or "youtube.com/user/" in channel_url:
        if not channel_url.endswith("/shorts"):
             channel_url = channel_url.rstrip("/") + "/shorts"
    
    print(f"🎯 Target URL: {channel_url}")
    print(f"Hs Output Directory: {os.path.abspath(output_dir)}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    import shutil
    
    # 1. Look for local ffmpeg (in current directory) or system ffmpeg
    local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
    if os.path.exists(local_ffmpeg):
        ffmpeg_location = os.path.dirname(os.path.abspath(__file__)) # Directory containing ffmpeg
        has_ffmpeg = True
        print(f"✅ Found local FFmpeg at: {local_ffmpeg}")
    else:
        ffmpeg_location = None
        has_ffmpeg = shutil.which('ffmpeg') is not None
    
    if not has_ffmpeg:
        print("⚠️  FFmpeg not found. Downloading best single file logic active.")
        # Fallback to 'b' (best video+audio in one container) or 'w' (worst, usually implies compatible)
        # But for shorts, simple 'best' often works if 'bestvideo+bestaudio' fails
        format_str = 'best[ext=mp4]/best'
    else:
        format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s [%(id)s].%(ext)s'),
        'format': format_str,
        'ignoreerrors': True,
        'no_warnings': False,
        # 'quiet': True,
        
        # KEY FIX: Use Android client to bypass 'nsig extraction failed' and 403s on web client
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        
        # Optimize for shorts
        'match_filter': yt_dlp.utils.match_filter_func("duration < 61"),
    }

    if ffmpeg_location:
         ydl_opts['ffmpeg_location'] = ffmpeg_location

    if has_ffmpeg:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("🚀 Starting download... this might take a while depending on the number of shorts.")
            ydl.download([channel_url])
        print("\n✅ Download complete!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    print("🎬 YouTube Shorts Downloader")
    print("----------------------------")
    
    default_url = input("Enter YouTube Channel URL (e.g., https://www.youtube.com/@ChannelName): ").strip()
    
    if default_url:
        download_shorts(default_url)
    else:
        print("❌ No URL provided. Exiting.")
