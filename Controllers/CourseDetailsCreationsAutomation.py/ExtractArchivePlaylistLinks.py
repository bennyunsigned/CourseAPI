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
#API_BASE_URL = os.environ.get('API_BASE_URL', 'https://api.vidyaroop.com')
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
ITEM_IDENTIFIER = "001-introduction_202507"  # Replace as needed

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
            
            # Get the total file size from headers
            total_size = int(r.headers.get('content-length', 0))
            
            # Extract filename from destination path for display
            filename = os.path.basename(dest)
            
            with open(dest, 'wb') as f:
                if total_size == 0:
                    # If no content-length header, download without progress bar
                    print(f"Downloading {filename}... (size unknown)")
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                    print(f"✅ Downloaded {filename}")
                else:
                    # Download with progress bar
                    with tqdm(
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"📥 {filename[:30]}{'...' if len(filename) > 30 else ''}",
                        ncols=100
                    ) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
        return True
    except Exception as e:
        print(f"❌ Failed to download {os.path.basename(dest)}: {str(e)}")
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

def test_api_connectivity():
    """Test API connectivity before starting the main process"""
    print("🔍 Testing API connectivity...")
    print("-" * 40)
    
    # Test max module ID endpoint
    try:
        print(f"🧪 Testing: {MAX_MODULE_ID_URL}")
        resp = requests.get(MAX_MODULE_ID_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Max Module ID API: Working (Response: {data})")
    except Exception as e:
        print(f"❌ Max Module ID API: Failed - {str(e)}")
        return False
    
    # Test max video ID endpoint
    try:
        print(f"🧪 Testing: {MAX_VIDEO_ID_URL}")
        resp = requests.get(MAX_VIDEO_ID_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Max Video ID API: Working (Response: {data})")
    except Exception as e:
        print(f"❌ Max Video ID API: Failed - {str(e)}")
        return False
    
    print("✅ All API endpoints are working!")
    return True

def get_max_module_id_from_db():
    """Fallback method to get max module ID directly from database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Try to get max ID from the actual coursemodule table
        cursor.execute("SELECT MAX(CAST(ModuleId AS UNSIGNED)) FROM coursemodule")
        result = cursor.fetchone()
        max_id = result[0] if result[0] is not None else 0
        
        cursor.close()
        conn.close()
        
        print(f"🔍 Database query result - Max Module ID: {max_id}")
        return max_id
    except Exception as e:
        print(f"❌ Database query failed: {str(e)}")
        return 0

def get_max_video_id_from_db():
    """Fallback method to get max video ID directly from database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Try to get max ID from the actual modulevideo table
        cursor.execute("SELECT MAX(CAST(VideoId AS UNSIGNED)) FROM modulevideo")
        result = cursor.fetchone()
        max_id = result[0] if result[0] is not None else 0
        
        cursor.close()
        conn.close()
        
        print(f"🔍 Database query result - Max Video ID: {max_id}")
        return max_id
    except Exception as e:
        print(f"❌ Database query failed: {str(e)}")
        return 0

def get_max_module_id():
    print(f"🔍 Fetching max module ID from: {MAX_MODULE_ID_URL}")
    
    # First try the API
    try:
        resp = requests.get(MAX_MODULE_ID_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"📊 API Response: {data}")
        
        max_id = int(data.get("MaxModuleId", 0))
        print(f"✅ API returned max module ID: {max_id}")
        
        # If API returns 0, try database fallback
        if max_id == 0:
            print("⚠️  API returned 0, trying database fallback...")
            max_id = get_max_module_id_from_db()
        
        return max_id
        
    except Exception as e:
        print(f"❌ API request failed: {str(e)}")
        print("🔄 Falling back to database query...")
        return get_max_module_id_from_db()

def get_max_video_id():
    print(f"🔍 Fetching max video ID from: {MAX_VIDEO_ID_URL}")
    
    # First try the API
    try:
        resp = requests.get(MAX_VIDEO_ID_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"📊 API Response: {data}")
        
        max_id = int(data.get("MaxVideoId", 0))
        print(f"✅ API returned max video ID: {max_id}")
        
        # If API returns 0, try database fallback
        if max_id == 0:
            print("⚠️  API returned 0, trying database fallback...")
            max_id = get_max_video_id_from_db()
        
        return max_id
        
    except Exception as e:
        print(f"❌ API request failed: {str(e)}")
        print("🔄 Falling back to database query...")
        return get_max_video_id_from_db()

def get_single_line(text):
    # Remove newlines and excessive quotes for SQL safety
    return re.sub(r'[\r\n]+', ' ', text).replace("'", "''").strip()

def process_and_save_to_db(course_id):
    statements_file = os.path.join(STATEMENTS_DIR, f"{course_id}_statements.txt")
    videos = get_video_urls_from_archive_org(ITEM_IDENTIFIER)
    temp_dir = "temp_videos"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"\n🎬 Found {len(videos)} videos to process")
    print("=" * 60)

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    create_table_if_not_exists(cursor)

    for i, video in enumerate(videos, 1):
        video_url = video["url"]
        video_name = video["name"]
        local_path = os.path.join(temp_dir, video_name)

        print(f"\n📹 Processing video {i}/{len(videos)}: {video_name}")
        print("-" * 50)

        try:
            sequence_no = int(video_name.split('.', 1)[0])
        except (ValueError, IndexError):
            sequence_no = None

        try:
            print("📥 Starting download...")
            if not download_video(video_url, local_path):
                print("❌ Download failed, skipping video")
                continue

            print("⏱️  Getting video duration...")
            duration = get_video_duration(local_path)
            print(f"Duration: {duration} seconds")

            print("🎤 Transcribing audio...")
            transcript = transcribe_video(local_path, language='hi-IN')
            if transcript:
                print(f"✅ Transcription complete ({len(transcript)} characters)")
            else:
                print("⚠️  No transcription available")

            print("🤖 Generating AI title and description...")
            video_title_raw = get_chat_response(
                f"Based on the following transcript, provide ONE concise and clear video title in plain text (no lists, no markdown, no quotes):\n{transcript}"
            )
            video_description_raw = get_chat_response(
                f"Based on the following transcript, write ONE clear and detailed video description in plain text (no markdown, no lists, no quotes):\n{transcript}"
            )

            video_title = get_single_line(video_title_raw) if video_title_raw else f"Video {sequence_no}"
            video_description = get_single_line(video_description_raw) if video_description_raw else "No description available"

            print(f"📝 Title: {video_title[:50]}{'...' if len(video_title) > 50 else ''}")
            print(f"📄 Description: {video_description[:100]}{'...' if len(video_description) > 100 else ''}")

            print("💾 Saving to database...")
            insert_video_row(cursor, course_id, sequence_no, video_url, video_title, video_description, duration)
            conn.commit()
            print("✅ Saved successfully")

        except Exception as e:
            print(f"❌ Error processing video: {str(e)}")
            pass
        finally:
            if os.path.exists(local_path):
                print("🗑️  Cleaning up temporary file...")
                os.remove(local_path)

        print(f"✅ Completed video {i}/{len(videos)}")

    cursor.close()
    conn.close()
    print(f"\n🎉 All {len(videos)} videos processed successfully!")

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
    
    try:
        print(f"    🌐 POST {url}")
        print(f"    📦 Payload: ModuleId={module_id}, CourseId={course_id}, SequenceNo={sequence_no}")
        
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        
        response_data = resp.json()
        print(f"    ✅ Course module API response: {response_data}")
        return response_data
        
    except requests.exceptions.Timeout:
        raise Exception("API request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)} - Status: {resp.status_code if 'resp' in locals() else 'N/A'}")
    except ValueError as e:
        raise Exception(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")

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
    
    try:
        print(f"    🌐 POST {url}")
        print(f"    📦 Payload: VideoId={video_id}, ModuleId={module_id}, Duration={duration_in_seconds}s")
        
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        
        response_data = resp.json()
        print(f"    ✅ Module video API response: {response_data}")
        return response_data
        
    except requests.exceptions.Timeout:
        raise Exception("API request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)} - Status: {resp.status_code if 'resp' in locals() else 'N/A'}")
    except ValueError as e:
        raise Exception(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")

def push_to_prod_from_db(course_id):
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE course_id = %s ORDER BY sequence_no", (course_id,))
    rows = cursor.fetchall()

    if not rows:
        print("⚠️  No data found in database for this course ID")
        cursor.close()
        conn.close()
        return

    print(f"\n📤 Found {len(rows)} records to push to production")
    print("=" * 50)

    # Get max IDs with detailed logging
    print("🔍 Getting maximum IDs from production...")
    try:
        module_id = get_max_module_id()
        video_id = get_max_video_id()
        
        print(f"📊 Current max module ID: {module_id}")
        print(f"📊 Current max video ID: {video_id}")
        print(f"🎯 Next module ID will start from: {module_id + 1}")
        print(f"🎯 Next video ID will start from: {video_id + 1}")
        
        # Validate that we got reasonable values
        if module_id < 0:
            print("⚠️  Invalid module ID received, using 0")
            module_id = 0
        if video_id < 0:
            print("⚠️  Invalid video ID received, using 0")
            video_id = 0
            
    except Exception as e:
        print(f"❌ Error getting max IDs: {str(e)}")
        print("⚠️  Using fallback values: module_id=0, video_id=0")
        module_id = 0
        video_id = 0

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    successful_pushes = 0
    failed_pushes = 0
    
    for i, row in enumerate(rows, 1):
        # Increment IDs for this record
        current_module_id = module_id + i
        current_video_id = video_id + i

        print(f"\n📤 Pushing record {i}/{len(rows)}: {row['video_name'][:50]}{'...' if len(row['video_name']) > 50 else ''}")
        print(f"   🆔 Module ID: {current_module_id}, Video ID: {current_video_id}")

        try:
            # Insert into CourseModule via API
            print("  📚 Creating course module...")
            module_response = insert_course_module_api(
                module_id=str(current_module_id),
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
            print(f"  ✅ Module created successfully: {module_response}")

            # Insert into ModuleVideo via API
            print("  🎬 Creating module video...")
            video_response = insert_module_video_api(
                video_id=str(current_video_id),
                course_id=course_id,
                module_id=str(current_module_id),
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
            print(f"  ✅ Video created successfully: {video_response}")
            
            print(f"  ✅ Successfully pushed record {i}/{len(rows)}")
            successful_pushes += 1
            
        except Exception as e:
            print(f"  ❌ Failed to push record {i}: {str(e)}")
            failed_pushes += 1

    cursor.close()
    conn.close()
    
    print(f"\n🎉 Production push completed!")
    print(f"✅ Successful: {successful_pushes}")
    print(f"❌ Failed: {failed_pushes}")
    print(f"📊 Total processed: {len(rows)}")
    
    if failed_pushes > 0:
        print(f"⚠️  {failed_pushes} records failed to push. Check the error messages above.")

if __name__ == "__main__":
    print("🚀 Video Processing and Course Creation Tool")
    print("=" * 60)
    
    course_id = input("📝 Enter course ID: ").strip()
    
    if not course_id:
        print("❌ Course ID cannot be empty!")
        sys.exit(1)
    
    print(f"\n🎯 Starting processing for Course ID: {course_id}")
    print(f"🌐 API Base URL: {API_BASE_URL}")
    print(f"🎞️  Archive Identifier: {ITEM_IDENTIFIER}")
    print("=" * 60)
    
    # Test API connectivity first
    if not test_api_connectivity():
        print("\n❌ API connectivity test failed!")
        print("Please check:")
        print("1. API server is running")
        print("2. API_BASE_URL is correct")
        print("3. Network connectivity")
        sys.exit(1)
    
    try:
        # print("\n📋 Step 1: Processing videos and saving to database...")
        # process_and_save_to_db(course_id)
        
        print("\n📋 Step 2: Pushing data to production via API...")
        push_to_prod_from_db(course_id)
        
        print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"✅ Course '{course_id}' has been fully processed and uploaded")
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
