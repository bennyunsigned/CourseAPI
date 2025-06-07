import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
import yt_dlp
import threading
import asyncio
from datetime import datetime
import uuid

util_router = APIRouter()

@util_router.post("/uploadCourseImage")
async def upload_image(file: UploadFile = File(...)):
    upload_dir = "Uploads/CourseImages"
    os.makedirs(upload_dir, exist_ok=True)
    # Generate filename in ddMMyyyyhhmmss format with original extension
    timestamp = datetime.now().strftime("%d%m%Y%H%M%S")
    ext = os.path.splitext(file.filename)[1]
    new_filename = f"{timestamp}_{uuid.uuid4().hex}{ext}"
    file_location = os.path.join(upload_dir, new_filename)
    try:
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)
        # Return the relative path for frontend use
        return JSONResponse(content={"path": f"/{file_location}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@util_router.post("/getYoutubeDuration")
async def get_youtube_duration(payload: dict = Body(...)):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if duration is None:
                raise HTTPException(status_code=404, detail="Duration not found")
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            return {"duration": duration_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch duration: {str(e)}")

# @video_router.get("/download")
# async def download_video():
#     queue = asyncio.Queue()
#     loop = asyncio.get_running_loop()  # Capture the main event loop

#     def progress_hook(d):
#         if d['status'] == 'downloading':
#             downloaded = d.get('downloaded_bytes') or 0
#             total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
#             if total > 0:
#                 percent = f"{int(downloaded / total * 100)}%"
#             else:
#                 percent = "0%"
#             asyncio.run_coroutine_threadsafe(queue.put(percent), loop)

#     def download():
#         url = 'https://www.youtube.com/watch?v=nwrSD4m9up8'
#         output_path = '.'
#         ydl_opts = {
#             'outtmpl': f'{output_path}/%(title)s.%(ext)s',
#             'format': 'bestvideo+bestaudio/best',
#             'progress_hooks': [progress_hook],
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#         # Signal completion
#         asyncio.run_coroutine_threadsafe(queue.put("done"), loop)

#     # Start download in a separate thread
#     threading.Thread(target=download, daemon=True).start()

#     async def event_stream():
#         while True:
#             percent = await queue.get()
#             if percent == "done":
#                 yield "data: done\n\n"
#                 break
#             yield f"data: {percent}\n\n"

#     return StreamingResponse(event_stream(), media_type="text/event-stream")
