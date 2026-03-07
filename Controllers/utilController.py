import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
import yt_dlp
import threading
import asyncio
from datetime import datetime
import uuid
import re
import requests
import tempfile
from moviepy.editor import VideoFileClip
from urllib.parse import urlparse, unquote

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

@util_router.post("/uploadProductImage")
async def upload_product_image(file: UploadFile = File(...)):
    upload_dir = "Uploads/ProductImages"
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

@util_router.post("/getDailymotionDuration")
async def get_dailymotion_duration(payload: dict = Body(...)):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    # Extract video ID from the Dailymotion URL
    match = re.search(r'dailymotion\.com/video/([a-zA-Z0-9]+)', url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Dailymotion URL")
    video_id = match.group(1)
    api_url = f"https://api.dailymotion.com/video/{video_id}?fields=duration"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            duration = data.get("duration")
            if duration is None:
                raise HTTPException(status_code=404, detail="Duration not found")
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            return {"duration": duration_str}
        else:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch duration from Dailymotion API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch duration: {str(e)}")

def convert_to_download_url(details_url):
    try:
        parsed = urlparse(details_url)
        if "archive.org" not in parsed.netloc or not parsed.path.startswith("/details/"):
            return None
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 3:
            return None
        identifier = parts[1]
        filename = unquote(parts[2]).replace("+", " ")
        download_url = f"https://archive.org/download/{identifier}/{requests.utils.quote(filename)}"
        return download_url
    except Exception:
        return None

@util_router.post("/getArchiveOrgDuration")
async def get_archiveorg_duration(payload: dict = Body(...)):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    download_url = convert_to_download_url(url)
    if not download_url:
        raise HTTPException(status_code=400, detail="Invalid archive.org /details/ URL")

    def stream_progress():
        temp_video = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                resp = requests.get(download_url, stream=True)
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                if total == 0:
                    yield '{"progress": "indeterminate"}\n'
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    temp_video.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        percent = int(downloaded * 100 / total)
                        percent = min(percent, 100)  # Cap at 100%
                        yield f'{{"progress": {percent}}}\n'
                temp_video.flush()
            clip = VideoFileClip(temp_video.name)
            duration = int(clip.duration)
            clip.close()
            yield f'{{"duration": {duration}}}\n'
        except Exception as e:
            yield f'{{"error": "{str(e)}"}}\n'
        finally:
            if temp_video and os.path.exists(temp_video.name):
                os.remove(temp_video.name)

    return StreamingResponse(stream_progress(), media_type="application/json")

@util_router.get("/debug-payments")
async def debug_payments():
    from DB.db import get_db_connection
    connection = get_db_connection()
    if not connection:
        return {"error": "Failed to connect to database"}
    try:
        cursor = connection.cursor(dictionary=True)
        # Check last 10 payments
        cursor.execute("SELECT * FROM Payment ORDER BY id DESC LIMIT 10")
        payments = cursor.fetchall()
        
        # Check last 10 emails
        cursor.execute("SELECT * FROM EmailMaster ORDER BY EmailId DESC LIMIT 10")
        emails = cursor.fetchall()
        
        # Check logs
        cursor.execute("SHOW TABLES LIKE 'PaymentLog'")
        logs = []
        if cursor.fetchone():
            cursor.execute("SELECT * FROM PaymentLog ORDER BY id DESC LIMIT 10")
            logs = cursor.fetchall()
            
        return {
            "payments": payments,
            "emails": emails,
            "logs": logs
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()

@util_router.get("/debug-db")
async def debug_db():
    from DB.db import get_db_connection
    connection = get_db_connection()
    if not connection:
        return {"error": "Failed to connect to database"}
    try:
        cursor = connection.cursor(dictionary=True)
        # List tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        # Check columns for key tables
        schema = {}
        for table_dict in tables:
            table_name = list(table_dict.values())[0]
            if table_name in ("ProductMaster", "BundleMaster", "CourseMaster", "SubscriptionPlan", "EmailMaster", "Payment"):
                cursor.execute(f"DESCRIBE {table_name}")
                schema[table_name] = cursor.fetchall()
        
        return {
            "tables": tables,
            "schema": schema
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()