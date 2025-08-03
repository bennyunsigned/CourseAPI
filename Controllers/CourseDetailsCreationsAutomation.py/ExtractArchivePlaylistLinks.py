import requests
import os
import subprocess
import sys
from tqdm import tqdm
import mysql.connector
import re
import tempfile
import shutil
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import speech_recognition as sr
from dotenv import load_dotenv
import datetime

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000')
MAX_MODULE_ID_URL = f"{API_BASE_URL}/api/courseProgress/max-module-id/"
MAX_VIDEO_ID_URL = f"{API_BASE_URL}/api/courseProgress/max-video-id/"

MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'course_db')
}
TABLE_NAME = 'course_content_operations'
ITEM_IDENTIFIER = "1.-java-programming-bootcamp-zero-to-mastery-zero-to-mastery-academy-1920x-1080-4085-k"  # Replace as needed

STATEMENTS_DIR = r"c:\Course_Module_Video_Statements"
os.makedirs(STATEMENTS_DIR, exist_ok=True)
# statements_file will be defined after course_id is set

def get_video_urls_from_archive_org(identifier):
    metadata_url = f"https://archive.org/metadata/{identifier}"
    try:
        response = requests.get(metadata_url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    data = response.json()
    files = data.get("files", [])
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.ogv', '.flv'}

    video_files = []
    for file in files:
        name = file.get("name", "")
        if any(name.lower().endswith(ext) for ext in video_exts):
            video_url = f"https://archive.org/download/{identifier}/{name}"
            video_files.append({"name": name, "url": video_url})
    return video_files

def get_video_duration(filepath):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        duration = float(result.stdout.strip())
        return int(duration)
    except Exception:
        return 0

def download_video(url, dest):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception:
        return False

def get_chat_response(prompt, model="llama3"):
    import ollama
    try:
        stream = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], stream=True)
        message_chunks = []
        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                message_chunks.append(chunk["message"]["content"])
        message = "".join(message_chunks).strip()
        if "deepseek" in model.lower():
            message = re.sub(r"<think>.*?</think>", "", message, flags=re.DOTALL).strip()
        # Remove all special characters except basic punctuation and spaces
        message = re.sub(r'[^\w\s.,:;!?()-]', '', message)
        return message
    except Exception as e:
        return

def create_table_if_not_exists(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_id VARCHAR(255),
            sequence_no INT,
            video_url TEXT,
            video_name TEXT,
            video_description TEXT,
            duration INT
        )
    """)

def insert_video_row(cursor, course_id, sequence_no, video_url, video_name, video_description, duration):
    cursor.execute(
        f"INSERT INTO {TABLE_NAME} (course_id, sequence_no, video_url, video_name, video_description, duration) VALUES (%s, %s, %s, %s, %s, %s)",
        (course_id, sequence_no, video_url, video_name, video_description, duration)
    )

def transcribe_video(video_path, language='hi-IN'):
    if not os.path.exists(video_path):
        return ""
    try:
        temp_dir = tempfile.mkdtemp()
        video = VideoFileClip(video_path)
        full_audio_path = os.path.join(temp_dir, "full_audio.wav")
        video.audio.write_audiofile(full_audio_path)
        video.close()  # <-- Add this line to release the file handle
        recognizer = sr.Recognizer()
        chunk_length = 20  # seconds
        audio = AudioSegment.from_wav(full_audio_path)
        duration_ms = len(audio)
        transcriptions = []
        for i, start_time in enumerate(range(0, duration_ms, chunk_length * 1000)):
            chunk = audio[start_time:start_time + chunk_length * 1000]
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            with sr.AudioFile(chunk_path) as source:
                audio_chunk = recognizer.record(source)
            try:
                chunk_text = recognizer.recognize_google(audio_chunk, language=language)
                transcriptions.append(chunk_text)
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                pass
        final_transcription = " ".join(transcriptions).replace("*", "")
        return final_transcription
    except Exception:
        return ""
    finally:
        shutil.rmtree(temp_dir)

def append_sql_statements(statements_file, module_id, video_id, course_id, sequence_no, video_title, video_description, video_url, duration):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    module_sql = f"""INSERT INTO `vidyaroop`.`coursemodule`
(`ModuleId`,`CourseId`,`ModuleName`,`ModuleDescription`,`SequenceNo`,`CreatedBy`,`CreatedAt`,`UpdatedBy`,`UpdatedAt`,`Status`)
VALUES
('{module_id}','{course_id}','{video_title}','{video_description}','{sequence_no}','system','{now}','system','{now}','Active');
"""
    video_sql = f"""INSERT INTO `vidyaroop`.`modulevideo`
(`VideoId`,`CourseId`,`ModuleId`,`VideoTitle`,`VideoUrl`,`DurationInSeconds`,`SequenceNo`,`CreatedBy`,`CreatedAt`,`UpdatedBy`,`UpdatedAt`,`Status`)
VALUES
('{video_id}','{course_id}','{module_id}','{video_title}','{video_url}','{duration}','{sequence_no}','system','{now}','system','{now}','Active');
"""
    with open(statements_file, "a", encoding="utf-8") as f:
        f.write(module_sql)
        f.write(video_sql)
        f.write("\n")

def get_max_module_id():
    try:
        resp = requests.get(MAX_MODULE_ID_URL)
        resp.raise_for_status()
        return int(resp.json().get("max_module_id", 0))
    except Exception:
        return 0

def get_max_video_id():
    try:
        resp = requests.get(MAX_VIDEO_ID_URL)
        resp.raise_for_status()
        return int(resp.json().get("max_video_id", 0))
    except Exception:
        return 0

def get_single_line(text):
    # Remove newlines and excessive quotes for SQL safety
    return re.sub(r'[\r\n]+', ' ', text).replace("'", "''").strip()

def process_and_save_to_db(course_id):
    statements_file = os.path.join(STATEMENTS_DIR, f"{course_id}_statements.txt")
    videos = get_video_urls_from_archive_org(ITEM_IDENTIFIER)
    temp_dir = "temp_videos"
    os.makedirs(temp_dir, exist_ok=True)

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    create_table_if_not_exists(cursor)

    for video in tqdm(videos, desc="Processing videos", unit="video"):
        video_url = video["url"]
        video_name = video["name"]
        local_path = os.path.join(temp_dir, video_name)

        try:
            sequence_no = int(video_name.split('.', 1)[0])
        except (ValueError, IndexError):
            sequence_no = None

        try:
            if not download_video(video_url, local_path):
                continue

            duration = get_video_duration(local_path)
            transcript = transcribe_video(local_path, language='hi-IN')

            video_title_raw = get_chat_response(
                f"Based on the following transcript, provide ONE concise and clear video title in plain text (no lists, no markdown, no quotes):\n{transcript}"
            )
            video_description_raw = get_chat_response(
                f"Based on the following transcript, write ONE clear and detailed video description in plain text (no markdown, no lists, no quotes):\n{transcript}"
            )

            video_title = get_single_line(video_title_raw)
            video_description = get_single_line(video_description_raw)

            insert_video_row(cursor, course_id, sequence_no, video_url, video_title, video_description, duration)
            conn.commit()
        except Exception:
            pass
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    cursor.close()
    conn.close()

def insert_course_module_api(module_id, course_id, module_name, module_description, sequence_no, created_by, created_at, updated_by, updated_at, status):
    url = f"{API_BASE_URL}/api/courseProgress/course-module/"
    payload = {
        "ModuleId": module_id,
        "CourseId": course_id,
        "ModuleName": module_name,
        "ModuleDescription": module_description,
        "SequenceNo": sequence_no,
        "CreatedBy": created_by,
        "CreatedAt": created_at,
        "UpdatedBy": updated_by,
        "UpdatedAt": updated_at,
        "Status": status
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

def insert_module_video_api(video_id, course_id, module_id, video_title, video_url, duration_in_seconds, sequence_no, created_by, created_at, updated_by, updated_at, status):
    url = f"{API_BASE_URL}/api/courseProgress/module-video/"
    payload = {
        "VideoId": video_id,
        "CourseId": course_id,
        "ModuleId": module_id,
        "VideoTitle": video_title,
        "VideoUrl": video_url,
        "DurationInSeconds": duration_in_seconds,
        "SequenceNo": sequence_no,
        "CreatedBy": created_by,
        "CreatedAt": created_at,
        "UpdatedBy": updated_by,
        "UpdatedAt": updated_at,
        "Status": status
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

def push_to_prod_from_db(course_id):
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE course_id = %s ORDER BY sequence_no", (course_id,))
    rows = cursor.fetchall()

    # Get max IDs once
    module_id = get_max_module_id()
    video_id = get_max_video_id()

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for row in rows:
        module_id += 1
        video_id += 1

        # Insert into CourseModule via API
        insert_course_module_api(
            module_id=str(module_id),
            course_id=course_id,
            module_name=row['video_name'],
            module_description=row['video_description'],
            sequence_no=row['sequence_no'],
            created_by="system",
            created_at=now,
            updated_by="system",
            updated_at=now,
            status="Active"
        )

        # Insert into ModuleVideo via API
        insert_module_video_api(
            video_id=str(video_id),
            course_id=course_id,
            module_id=str(module_id),
            video_title=row['video_name'],
            video_url=row['video_url'],
            duration_in_seconds=row['duration'],
            sequence_no=row['sequence_no'],
            created_by="system",
            created_at=now,
            updated_by="system",
            updated_at=now,
            status="Active"
        )

    cursor.close()
    conn.close()

if __name__ == "__main__":
    course_id = input("Enter course ID: ").strip()
    print("Step 1: Processing videos and saving to DB...")
    process_and_save_to_db(course_id)
    print("Step 2: Inserting into prod DB via API...")
    push_to_prod_from_db(course_id)
    print("Done.")
