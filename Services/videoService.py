import os
import uuid
import yt_dlp
from fastapi.responses import FileResponse
from fastapi import HTTPException

VIDEO_DIR = "temp_videos"
os.makedirs(VIDEO_DIR, exist_ok=True)
video_map = {}

def download_video(video_url: str) -> FileResponse:
    filename = f"{uuid.uuid4()}.mp4"
    file_path = os.path.join(VIDEO_DIR, filename)
    ydl_opts = {
        'outtmpl': file_path,
        'format': 'best[ext=mp4]/best',
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        video_map[filename] = file_path
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='video/mp4',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

def remove_video(filename: str) -> dict:
    file_path = video_map.get(filename)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        del video_map[filename]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")