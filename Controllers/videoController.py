# video_router.py

import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import yt_dlp
import threading

video_router = APIRouter()

@video_router.get("/download")
async def download_video():
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()  # Capture the main event loop

    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes') or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if total > 0:
                percent = f"{int(downloaded / total * 100)}%"
            else:
                percent = "0%"
            asyncio.run_coroutine_threadsafe(queue.put(percent), loop)

    def download():
        url = 'https://www.youtube.com/watch?v=nwrSD4m9up8'
        output_path = '.'
        ydl_opts = {
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'format': 'bestvideo+bestaudio/best',
            'progress_hooks': [progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # Signal completion
        asyncio.run_coroutine_threadsafe(queue.put("done"), loop)

    # Start download in a separate thread
    threading.Thread(target=download, daemon=True).start()

    async def event_stream():
        while True:
            percent = await queue.get()
            if percent == "done":
                yield "data: done\n\n"
                break
            yield f"data: {percent}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
