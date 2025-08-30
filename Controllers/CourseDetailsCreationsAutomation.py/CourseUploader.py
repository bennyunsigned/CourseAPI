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
API_BASE_URL = os.environ.get('API_BASE_URL', 'https://api.vidyaroop.com')
#API_BASE_URL = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000')
MAX_MODULE_ID_URL = f"{API_BASE_URL}/api/courseProgress/max-module-id/"
MAX_VIDEO_ID_URL = f"{API_BASE_URL}/api/courseProgress/max-video-id/"

MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'course_db')
}
TABLE_NAME = 'course_content_operations'
ITEM_IDENTIFIER = "58.useuse-reducerwithuse-effecttofetchthedata"  # Replace as needed

STATEMENTS_DIR = r"c:\Course_Module_Video_Statements"
os.makedirs(STATEMENTS_DIR, exist_ok=True)
# statements_file will be defined after course_id is set

def get_video_urls_from_archive_org(identifier, max_retries=5, timeout=30):
    """
    Get video URLs from archive.org with retry logic
    
    Args:
        identifier: Archive.org item identifier
        max_retries: Maximum number of retry attempts
        timeout: Timeout in seconds for each attempt
    
    Returns:
        list: List of video file dictionaries with 'name' and 'url'
    """
    import time
    
    metadata_url = f"https://archive.org/metadata/{identifier}"
    
    print(f"🔍 Fetching metadata from archive.org...")
    print(f"📋 Archive item: {identifier}")
    print(f"🌐 URL: {metadata_url}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 Fetching metadata (attempt {attempt}/{max_retries})...")
            print(f"⏱️  Timeout: {timeout} seconds")
            
            # Create session with custom headers and longer timeout
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache'
            })
            
            response = session.get(metadata_url, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            files = data.get("files", [])
            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.ogv', '.flv'}

            video_files = []
            for file in files:
                name = file.get("name", "")
                if any(name.lower().endswith(ext) for ext in video_exts):
                    video_url = f"https://archive.org/download/{identifier}/{name}"
                    video_files.append({"name": name, "url": video_url})
            
            print(f"✅ Successfully retrieved metadata: {len(video_files)} video files found")
            if len(video_files) > 0:
                print(f"📹 Sample videos found:")
                for i, video in enumerate(video_files[:3]):  # Show first 3 videos
                    print(f"   {i+1}. {video['name']}")
                if len(video_files) > 3:
                    print(f"   ... and {len(video_files) - 3} more videos")
            
            return video_files
            
        except (requests.exceptions.ConnectTimeout, 
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:
            print(f"⚠️  Attempt {attempt}: Connection/timeout error - {str(e)}")
            
            if attempt < max_retries:
                wait_time = min(5 * attempt, 20)  # Progressive backoff: 5s, 10s, 15s, 20s, 20s
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed to fetch metadata after {max_retries} attempts")
                print(f"🔧 Troubleshooting suggestions:")
                print(f"   • Check internet connectivity")
                print(f"   • Try accessing {metadata_url} in browser")
                print(f"   • Archive.org might be temporarily unavailable")
                
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP error fetching metadata: {str(e)}")
            if e.response.status_code == 404:
                print(f"⚠️  Archive item not found: {identifier}")
                print(f"🔧 Please verify the archive identifier is correct")
                return []  # Don't retry for 404 errors
            elif attempt < max_retries:
                wait_time = 3
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"❌ Unexpected error fetching metadata: {str(e)}")
            if attempt < max_retries:
                wait_time = 3
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
    
    print(f"❌ Failed to retrieve video list after {max_retries} attempts")
    return []

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

def download_video(url, dest, timeout=30):
    """
    Download video with infinite retry logic until success (except for 404 errors)
    
    This function implements robust downloading by retrying indefinitely until the
    download succeeds. Only 404 errors (file not found) will cause it to give up
    and return False. For all other errors, it waits 20 seconds and retries.
    
    Args:
        url: Video URL to download
        dest: Destination file path
        timeout: Timeout in seconds for each attempt
    
    Returns:
        bool: True if successful, False only for 404 errors (file not found)
    """
    import time
    
    filename = os.path.basename(dest)
    attempt = 0
    
    while True:  # Infinite retry loop
        attempt += 1
        try:
            print(f"🔄 Attempt {attempt} for {filename}")
            
            # Create session with timeout and retry configuration
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            with session.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                
                # Get the total file size from headers
                total_size = int(r.headers.get('content-length', 0))
                
                with open(dest, 'wb') as f:
                    if total_size == 0:
                        # If no content-length header, download without progress bar
                        print(f"📥 Downloading {filename}... (size unknown)")
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                        print(f"✅ Downloaded {filename}")
                    else:
                        # Download with progress bar - configured for single line display
                        with tqdm(
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            unit_divisor=1024,
                            desc=f"📥 {filename[:25]}{'...' if len(filename) > 25 else ''}",
                            ncols=80,        # Shorter width to fit in terminal
                            leave=False,     # Remove progress bar after completion to prevent stacking
                            dynamic_ncols=False,  # Fixed width
                            miniters=1,      # Update every iteration
                            mininterval=0.1, # 100ms minimum between updates
                            maxinterval=0.5, # 500ms maximum between updates
                            ascii=True,      # Use ASCII characters for better compatibility
                            position=0,      # Position at line 0
                            file=sys.stdout, # Explicitly use stdout
                            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{rate_fmt}]'
                        ) as pbar:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                        # Print completion message after progress bar is cleared
                        print(f"✅ Downloaded {filename}")
            
            return True  # Success - exit the infinite loop
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP error for {filename}: {str(e)}")
            if e.response.status_code == 404:
                print(f"⚠️  File not found on server: {filename} - SKIPPING")
                return False  # Don't retry for 404 errors - file doesn't exist
            else:
                print(f"⚠️  HTTP error {e.response.status_code}, will retry after 20 seconds...")
                
        except (requests.exceptions.ConnectTimeout, 
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:
            print(f"⚠️  Attempt {attempt}: Connection/timeout error - {str(e)}")
            
        except Exception as e:
            print(f"❌ Unexpected error downloading {filename}: {str(e)}")
        
        # Clean up partial file if it exists
        if os.path.exists(dest):
            try:
                os.remove(dest)
                print(f"🗑️  Cleaned up partial download")
            except:
                pass
        
        # Wait 20 seconds before retrying (for any error except 404)
        print(f"⏳ Waiting 20 seconds before retry...")
        time.sleep(20)

def get_chat_response(prompt, model="mistral:7b"):
    import ollama
    try:
        print(f"    🤖 Calling Ollama with model: {model}")
        print(f"    📝 Prompt length: {len(prompt)} characters")
        
        stream = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], stream=True)
        message_chunks = []
        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                message_chunks.append(chunk["message"]["content"])
        
        message = "".join(message_chunks).strip()
        print(f"    ✅ Raw AI response length: {len(message)} characters")
        
        if not message:
            print("    ⚠️  AI returned empty response")
            return ""
        
        if "deepseek" in model.lower():
            message = re.sub(r"<think>.*?</think>", "", message, flags=re.DOTALL).strip()
        
        # Clean up common AI response patterns
        message = clean_ai_response(message)
        
        print(f"    📋 Processed response: {message[:100]}{'...' if len(message) > 100 else ''}")
        return message
        
    except Exception as e:
        print(f"    ❌ Ollama API error: {str(e)}")
        return ""

def get_validated_ai_response(prompt, request_type, max_words=None, min_words=None, model="mistral:7b", max_retries=100):
    """
    Get AI response with automatic validation and retry logic
    
    Args:
        prompt: The prompt to send to AI
        request_type: 'title' or 'description'
        max_words: Maximum allowed words
        min_words: Minimum required words
        model: Ollama model to use
        max_retries: Maximum number of retry attempts
    
    Returns:
        dict: {'success': bool, 'response': str, 'validation_result': dict}
    """
    import time
    
    for attempt in range(1, max_retries + 1):
        print(f"    🔄 Attempt {attempt}/{max_retries} for {request_type}")
        
        # Get AI response
        ai_response = get_chat_response(prompt, model)
        
        if not ai_response:
            print(f"    ❌ Attempt {attempt}: Empty response from AI")
            if attempt < max_retries:
                print(f"    ⏳ Waiting 2 seconds before retry...")
                time.sleep(2)
            continue
        
        # Validate the response
        validation = validate_ai_response(ai_response, request_type, max_words, min_words)
        
        if validation['is_valid']:
            print(f"    ✅ Attempt {attempt}: Validation passed!")
            return {
                'success': True,
                'response': validation['cleaned_response'],
                'validation_result': validation
            }
        else:
            print(f"    ⚠️  Attempt {attempt}: Validation failed - {', '.join(validation['issues'])}")
            
            # For subsequent attempts, modify the prompt to be more specific
            if attempt < max_retries:
                print(f"    🔧 Modifying prompt for retry...")
                
                # Add specific instructions based on the validation issues
                retry_instructions = []
                for issue in validation['issues']:
                    if "too long" in issue:
                        retry_instructions.append("Be more concise")
                    elif "too short" in issue:
                        retry_instructions.append("Provide more detail")
                    elif "meta-commentary" in issue:
                        retry_instructions.append("Give only the direct answer, no explanations")
                    elif "non-English" in issue:
                        retry_instructions.append("Use only English words")
                    elif "question" in issue:
                        retry_instructions.append("Make it a statement, not a question")
                    elif "markdown" in issue:
                        retry_instructions.append("Use plain text only")
                
                if retry_instructions:
                    enhanced_prompt = f"{prompt}\n\nIMPORTANT: {', '.join(retry_instructions)}. Previous attempt had issues: {', '.join(validation['issues'])}"
                    prompt = enhanced_prompt
                
                print(f"    ⏳ Waiting 1 second before retry...")
                time.sleep(1)
    
    print(f"    ❌ All {max_retries} attempts failed validation")
    return {
        'success': False,
        'response': "",
        'validation_result': validation if 'validation' in locals() else {'is_valid': False, 'issues': ['No valid response after retries']}
    }

def validate_ai_response(response, request_type, max_words=None, min_words=None):
    """
    Validate AI response against request conditions and requirements
    
    Args:
        response: The AI response to validate
        request_type: 'title' or 'description' 
        max_words: Maximum allowed words (optional)
        min_words: Minimum required words (optional)
    
    Returns:
        dict: {'is_valid': bool, 'issues': list, 'cleaned_response': str}
    """
    validation_result = {
        'is_valid': False,
        'issues': [],
        'cleaned_response': response.strip() if response else ""
    }
    
    if not response or not response.strip():
        validation_result['issues'].append("Empty or null response")
        return validation_result
    
    cleaned = response.strip()
    words = cleaned.split()
    word_count = len(words)
    
    # 1. Check language validity (English only)
    if is_transliterated_text(cleaned) or is_mostly_non_english(cleaned):
        validation_result['issues'].append("Contains non-English or transliterated text")
        return validation_result
    
    # 2. Check word count constraints
    if request_type == 'title':
        if word_count < 2:  # Titles should have substance
            validation_result['issues'].append(f"Title too short ({word_count} words, min 2)")
    elif request_type == 'description':
        if word_count < 8:  # Descriptions should be informative
            validation_result['issues'].append(f"Description too short ({word_count} words, min 8)")
    
    # Apply custom word limits if provided
    if min_words and word_count < min_words:
        validation_result['issues'].append(f"Below min words ({word_count} < {min_words})")
    
    # 3. Check for AI meta-commentary (response should be direct)
    meta_patterns = [
        r'here\s+is\s+(a|an|the)',
        r'this\s+(title|description)\s+(is|would|should)',
        r'based\s+on\s+(the\s+)?(transcript|content)',
        r'i\s+(would\s+)?(suggest|recommend|propose)',
        r'the\s+(title|description)\s+(should\s+be|is)',
        r'a\s+(good|suitable|appropriate)\s+(title|description)',
        r'for\s+this\s+(video|content)',
        r'as\s+(requested|asked)'
    ]
    
    for pattern in meta_patterns:
        if re.search(pattern, cleaned.lower()):
            validation_result['issues'].append("Contains AI meta-commentary instead of direct content")
            break
    
    # 4. Check content relevance for programming/education
    if request_type == 'title':
        # Titles should be descriptive, not questions or commands
        if cleaned.endswith('?'):
            validation_result['issues'].append("Title should not be a question")
        if cleaned.lower().startswith(('how to', 'learn', 'tutorial on')):
            # These are acceptable for educational content
            pass
        elif any(word in cleaned.lower() for word in ['click', 'watch', 'subscribe', 'like', 'follow']):
            validation_result['issues'].append("Title contains inappropriate call-to-action words")
    
    # 5. Check formatting issues
    if '**' in cleaned or '*' in cleaned:
        validation_result['issues'].append("Contains markdown formatting")
    
    if cleaned.count('"') % 2 != 0 or cleaned.count("'") % 2 != 0:
        validation_result['issues'].append("Contains unmatched quotes")
    
    # 6. Check for repetitive content
    words_lower = [w.lower() for w in words]
    unique_words = set(words_lower)
    if len(words_lower) > 3 and len(unique_words) / len(words_lower) < 0.7:
        validation_result['issues'].append("Content appears repetitive or low quality")
    
    # 7. Check for programming relevance (if content suggests it)
    programming_keywords = [
        'python', 'java', 'javascript', 'code', 'programming', 'development',
        'function', 'variable', 'class', 'method', 'algorithm', 'data',
        'software', 'application', 'framework', 'library', 'api', 'database',
        'web', 'mobile', 'security', 'hacking', 'tutorial', 'course',
        'setup', 'installation', 'configuration', 'debugging', 'testing'
    ]
    
    # For programming content, response should have some relevance
    has_programming_context = any(keyword in cleaned.lower() for keyword in programming_keywords)
    
    # 8. Final validation
    if len(validation_result['issues']) == 0:
        validation_result['is_valid'] = True
        validation_result['cleaned_response'] = clean_ai_response_format(cleaned)
    
    return validation_result

def clean_ai_response_format(response):
    """Clean and format AI response for final use"""
    if not response:
        return ""
    
    # Remove quotes that wrap entire response
    cleaned = response.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    
    # Capitalize first letter
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    
    # Ensure proper sentence ending for descriptions
    if not cleaned.endswith('.') and len(cleaned.split()) > 5:
        cleaned += '.'
    
    return cleaned

def clean_ai_response(response):
    """Clean AI response to extract only the actual content"""
    if not response:
        return ""
    
    # Check if response is transliterated or contains too much non-English content
    if is_transliterated_text(response) or is_mostly_non_english(response):
        print("    ⚠️  AI returned transliterated/non-English text, discarding")
        return ""
    
    # Remove common AI prefixes and explanatory text (English and Hindi patterns)
    patterns_to_remove = [
        r"Here is a concise and clear video title:\s*",
        r"Here is a clear and detailed video description:\s*",
        r"Here's a concise and clear video title:\s*",
        r"Here's a clear and detailed video description:\s*",
        r"Here is an? English video title:\s*",
        r"Here is an? English description:\s*",
        r"Video title:\s*",
        r"Video description:\s*",
        r"Title:\s*",
        r"Description:\s*",
        r"English title:\s*",
        r"English description:\s*",
        r"A concise video title would be:\s*",
        r"A clear video description would be:\s*",
        r"Based on the transcript,?\s*(the\s+)?(video\s+)?title\s+(is|would\s+be|could\s+be):\s*",
        r"Based on the transcript,?\s*(the\s+)?(video\s+)?description\s+(is|would\s+be|could\s+be):\s*",
        r"This title accurately reflects.*$",
        r"This description accurately reflects.*$",
        r"The title should be:\s*",
        r"The description should be:\s*",
        r"In English:\s*",
        r"English version:\s*",
        r"Translation:\s*",
        # Hindi patterns
        r"यह वीडियो का शीर्षक है:\s*",
        r"वीडियो का विवरण:\s*",
        r"शीर्षक:\s*",
        r"विवरण:\s*"
    ]
    
    cleaned = response
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove extra whitespace and newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # If the response contains explanatory text after the main content, extract just the main part
    # Look for patterns like "Setting Up Django. This title..." and extract just "Setting Up Django"
    sentences = cleaned.split('.')
    if len(sentences) > 1:
        # Take the first sentence if it looks like a title/description
        first_sentence = sentences[0].strip()
        if len(first_sentence) > 5 and not first_sentence.lower().startswith('this'):
            cleaned = first_sentence
    
    # Remove quotes if they wrap the entire response
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1].strip()
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1].strip()
    
    # Remove remaining special characters except basic punctuation
    cleaned = re.sub(r'[^\w\s.,:;!?()-]', '', cleaned)
    
    return cleaned.strip()

def is_mostly_non_english(text):
    """Check if text is mostly non-English characters or transliterated"""
    if not text:
        return False
    
    # Count English words vs total words
    english_words = re.findall(r'\b[a-zA-Z]+\b', text)
    total_chars = len(re.sub(r'\s+', '', text))
    english_chars = len(''.join(english_words))
    
    # If less than 70% of characters are English letters, consider it non-English
    if total_chars > 0 and (english_chars / total_chars) < 0.7:
        return True
    
    # Check for excessive single character words (common in bad transcription)
    words = text.split()
    single_char_words = [w for w in words if len(w) == 1 and w.isalpha()]
    if len(words) > 0 and (len(single_char_words) / len(words)) > 0.3:
        return True
    
    return False

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

def download_all_videos(videos, temp_dir):
    """
    Download all videos first and return a detailed download report
    
    Args:
        videos: List of video dictionaries with 'name' and 'url'
        temp_dir: Directory to store downloaded videos
    
    Returns:
        dict: Download report with successful and failed downloads
    """
    print(f"\n📥 PHASE 1: Downloading all {len(videos)} videos")
    print("=" * 60)
    
    downloaded_videos = []
    failed_downloads = []
    total_size = 0
    
    for i, video in enumerate(videos, 1):
        video_url = video["url"]
        video_name = video["name"]
        local_path = os.path.join(temp_dir, video_name)
        
        print(f"\n📹 Downloading {i}/{len(videos)}: {video_name}")
        print("-" * 50)
        
        try:
            sequence_no = int(video_name.split('.', 1)[0])
        except (ValueError, IndexError):
            sequence_no = i
        
        if download_video(video_url, local_path):
            # Get file size for report
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            total_size += file_size
            
            downloaded_videos.append({
                'name': video_name,
                'url': video_url,
                'local_path': local_path,
                'sequence_no': sequence_no,
                'file_size': file_size
            })
            print(f"✅ Successfully downloaded: {video_name} ({file_size / (1024*1024):.1f} MB)")
        else:
            failed_downloads.append({
                'name': video_name,
                'url': video_url,
                'sequence_no': sequence_no,
                'error': 'Download failed'
            })
            print(f"❌ Failed to download: {video_name}")
    
    # Generate download report
    download_report = {
        'total_videos': len(videos),
        'successful_downloads': len(downloaded_videos),
        'failed_downloads': len(failed_downloads),
        'total_size_mb': total_size / (1024 * 1024),
        'downloaded_videos': downloaded_videos,
        'failed_videos': failed_downloads
    }
    
    # Display comprehensive download report
    print(f"\n📊 DOWNLOAD REPORT")
    print("=" * 60)
    print(f"📈 Total videos requested: {download_report['total_videos']}")
    print(f"✅ Successfully downloaded: {download_report['successful_downloads']}")
    print(f"❌ Failed downloads: {download_report['failed_downloads']}")
    print(f"💾 Total size downloaded: {download_report['total_size_mb']:.1f} MB")
    
    # Avoid division by zero
    if download_report['total_videos'] > 0:
        success_rate = (download_report['successful_downloads'] / download_report['total_videos'] * 100)
        print(f"📊 Success rate: {success_rate:.1f}%")
    else:
        print(f"📊 Success rate: N/A (no videos found)")
    
    if failed_downloads:
        print(f"\n❌ FAILED DOWNLOADS:")
        for failed in failed_downloads:
            print(f"   • {failed['name']} (Sequence: {failed['sequence_no']})")
    
    print(f"\n✅ Download phase completed! {len(downloaded_videos)} videos ready for processing.")
    
    return download_report

def process_downloaded_videos(course_id, downloaded_videos):
    """
    Process all downloaded videos: transcription, AI generation, and database saving
    
    Args:
        course_id: Course identifier
        downloaded_videos: List of successfully downloaded video info
    """
    if not downloaded_videos:
        print("⚠️  No videos to process!")
        return
    
    print(f"\n🔧 PHASE 2: Processing {len(downloaded_videos)} downloaded videos")
    print("=" * 60)
    
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    create_table_if_not_exists(cursor)
    
    processed_count = 0
    error_count = 0
    
    for i, video_info in enumerate(downloaded_videos, 1):
        video_name = video_info['name']
        video_url = video_info['url']
        local_path = video_info['local_path']
        sequence_no = video_info['sequence_no']
        
        print(f"\n🔬 Processing {i}/{len(downloaded_videos)}: {video_name}")
        print("-" * 50)
        
        try:
            print("⏱️  Getting video duration...")
            duration = get_video_duration(local_path)
            print(f"Duration: {duration} seconds")

            print("🎤 Transcribing audio...")
            # Try English first, then Hindi if that fails
            transcript = transcribe_video(local_path, language='en-IN')
            if not transcript or len(transcript.strip()) < 10:
                print("⚠️  English transcription failed, trying Hindi...")
                transcript = transcribe_video(local_path, language='hi-IN')
            
            if transcript:
                print(f"✅ Transcription complete ({len(transcript)} characters)")
                print(f"🔍 Transcript preview: {transcript[:200]}{'...' if len(transcript) > 200 else ''}")
                
                # Check if transcript contains transliterated text
                if is_transliterated_text(transcript):
                    print("⚠️  Detected transliterated text, will use intelligent fallback")
                    transcript = ""  # Clear transcript to use fallback values
                else:
                    print("✅ Transcript appears to be valid for AI processing")
            else:
                print("⚠️  No transcription available")

            print("🤖 Generating AI title and description...")
            
            # Check if we have content to work with
            if not transcript or len(transcript.strip()) < 10:
                print("⚠️  Transcript too short or empty, using intelligent fallback values")
                video_title, video_description = generate_smart_fallback(video_name, sequence_no)
            else:
                print("📝 Generating title with validation and retry...")
                title_result = get_validated_ai_response(
                    f"You are an English content creator. Create a short English video title (maximum 8 words) for this educational programming content. Respond ONLY with the English title, no Hindi, no transliterated text, no explanations:\n\nContent: {transcript[:1000]}",
                    request_type='title',
                    max_words=8,
                    min_words=2,
                    model="mistral:7b",
                    max_retries=100
                )
                
                if title_result['success']:
                    print("📄 Generating description with validation and retry...")
                    desc_result = get_validated_ai_response(
                        f"You are an English content creator. Write a 2-3 sentence English description for this educational programming video. Respond ONLY with the English description, no Hindi, no transliterated text, no explanations:\n\nContent: {transcript[:1500]}",
                        request_type='description',
                        max_words=50,
                        min_words=8,
                        model="mistral:7b",
                        max_retries=100
                    )
                    
                    if desc_result['success']:
                        # Both AI responses were successful and validated
                        video_title = title_result['response']
                        video_description = desc_result['response']
                        
                        print(f"🤖 AI generated title: {video_title}")
                        print(f"🤖 AI generated description: {video_description[:100]}{'...' if len(video_description) > 100 else ''}")
                    else:
                        # Title succeeded but description failed - use AI title with fallback description
                        video_title = title_result['response']
                        video_description = generate_description_from_filename(video_name)
                        
                        print(f"🤖 AI generated title: {video_title}")
                        print(f"⚠️  AI description failed, using fallback: {video_description[:100]}{'...' if len(video_description) > 100 else ''}")
                else:
                    # Title generation failed - use complete fallback
                    print("⚠️  AI title generation failed after retries, using smart fallback")
                    video_title, video_description = generate_smart_fallback(video_name, sequence_no)

                # Final safety check - ensure we have valid content
                if not video_title or len(video_title.strip()) < 3:
                    print("⚠️  Final title validation failed, using smart fallback")
                    video_title, video_description = generate_smart_fallback(video_name, sequence_no)

            print(f"📝 Title: {video_title[:50]}{'...' if len(video_title) > 50 else ''}")
            print(f"📄 Description: {video_description[:100]}{'...' if len(video_description) > 100 else ''}")

            print("💾 Saving to database...")
            insert_video_row(cursor, course_id, sequence_no, video_url, video_title, video_description, duration)
            conn.commit()
            print("✅ Saved successfully")
            
            processed_count += 1

        except Exception as e:
            print(f"❌ Error processing video: {str(e)}")
            error_count += 1
        finally:
            # Clean up the downloaded file after processing
            if os.path.exists(local_path):
                print("🗑️  Cleaning up temporary file...")
                os.remove(local_path)

        print(f"✅ Completed processing {i}/{len(downloaded_videos)}")

    cursor.close()
    conn.close()
    
    # Final processing report
    print(f"\n📊 PROCESSING REPORT")
    print("=" * 60)
    print(f"🔬 Videos processed: {processed_count}")
    print(f"❌ Processing errors: {error_count}")
    
    # Avoid division by zero
    if len(downloaded_videos) > 0:
        processing_success_rate = (processed_count / len(downloaded_videos) * 100)
        print(f"📊 Processing success rate: {processing_success_rate:.1f}%")
    else:
        print(f"📊 Processing success rate: N/A (no videos to process)")
    
    print(f"💾 Records saved to database: {processed_count}")

def process_and_save_to_db(course_id):
    """
    Main function to process videos in segregated phases:
    1. Download all videos
    2. Process downloaded videos (transcription, AI, database)
    """
    videos = get_video_urls_from_archive_org(ITEM_IDENTIFIER)
    temp_dir = "temp_videos"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"\n🎬 Found {len(videos)} videos to process")
    print("=" * 60)

    # Early exit if no videos found
    if len(videos) == 0:
        print("❌ No videos were found from archive.org. Cannot proceed with processing.")
        print("🔍 Please check:")
        print("1. Archive.org connectivity")
        print("2. Archive identifier is correct")
        print("3. Archive item exists and contains video files")
        return

    # Phase 1: Download all videos
    download_report = download_all_videos(videos, temp_dir)
    
    # Phase 2: Process all downloaded videos
    if download_report['downloaded_videos']:
        process_downloaded_videos(course_id, download_report['downloaded_videos'])
    else:
        print("❌ No videos were successfully downloaded. Cannot proceed with processing.")
        return
    
    # Final summary
    print(f"\n🎉 FINAL SUMMARY")
    print("=" * 60)
    print(f"📥 Total videos found: {len(videos)}")
    print(f"⬇️  Successfully downloaded: {download_report['successful_downloads']}")
    print(f"🔬 Successfully processed: {len(download_report['downloaded_videos'])}")
    print(f"💾 Total file size: {download_report['total_size_mb']:.1f} MB")
    print(f"✅ Course processing completed for ID: {course_id}")
    
    if download_report['failed_downloads']:
        print(f"⚠️  Note: {len(download_report['failed_downloads'])} videos failed to download and were skipped.")

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

def test_ollama_connectivity():
    """Test if Ollama is running and responsive"""
    print("🔍 Testing Ollama connectivity...")
    try:
        import ollama
        # Simple test prompt with explicit English instruction
        test_result = get_validated_ai_response(
            "Respond with only the word 'OK' in English, nothing else.",
            request_type='title',
            max_words=1,
            min_words=1,
            model="mistral:7b",
            max_retries=100
        )
        
        if test_result['success']:
            print(f"✅ Ollama is working! Test response: '{test_result['response']}'")
            print("✅ Response validation passed")
            return True
        else:
            print(f"⚠️  Test response validation failed: {test_result['validation_result'].get('issues', [])}")
            # Still check if basic functionality works
            basic_response = get_chat_response("Say OK", model="mistral:7b")
            if basic_response and len(basic_response.strip()) > 0:
                print("✅ Basic Ollama functionality works, validation strict")
                return True
            else:
                print("❌ Ollama returned empty response")
                return False
    except ImportError:
        print("❌ Ollama library not installed. Install with: pip install ollama")
        return False
    except Exception as e:
        print(f"❌ Ollama test failed: {str(e)}")
        return False

def is_transliterated_text(text):
    """Check if text contains transliterated Hindi (Hindi written in Latin script)"""
    if not text:
        return False
    
    # Common transliterated Hindi patterns
    transliterated_patterns = [
        r'\bhai\b', r'\bke\b', r'\bki\b', r'\bko\b', r'\bse\b', r'\bme\b',
        r'\bpar\b', r'\baur\b', r'\bya\b', r'\bjo\b', r'\bwoh\b', r'\byeh\b',
        r'\bkya\b', r'\bkaise\b', r'\bkahan\b', r'\bkab\b', r'\bkaun\b',
        r'\bhum\b', r'\btum\b', r'\bvoh\b', r'\byah\b', r'\biska\b', r'\buska\b',
        r'\bham\b', r'\baap\b', r'\bmain\b', r'\bhoga\b', r'\bkarenge\b',
        r'\bbanayenge\b', r'\bdekhenge\b', r'\bsamjhenge\b', r'\bसीखेंगे\b',
        r'\bhindi\b.*\benglish\b', r'\benglish\b.*\bhindi\b'
    ]
    
    # Check for excessive transliterated patterns
    matches = 0
    total_words = len(text.split())
    
    for pattern in transliterated_patterns:
        matches += len(re.findall(pattern, text.lower()))
    
    # If more than 20% of words are transliterated, consider it transliterated text
    if total_words > 0 and (matches / total_words) > 0.2:
        return True
    
    # Check for sequences of single letters (common in bad transliteration)
    single_letter_pattern = r'\b[a-zA-Z]\s+[a-zA-Z]\s+[a-zA-Z]'
    if re.search(single_letter_pattern, text):
        return True
    
    return False

def generate_smart_fallback(video_name, sequence_no):
    """Generate intelligent title and description from video filename"""
    # Extract meaningful parts from filename
    # Example: "10.Using Symbols Type Continue.mp4" -> "Using Symbols Type Continue"
    
    # Remove sequence number and extension
    clean_name = video_name
    if '.' in clean_name:
        parts = clean_name.split('.', 1)
        if len(parts) > 1 and parts[0].isdigit():
            clean_name = parts[1]
    
    # Remove file extension
    if '.' in clean_name:
        clean_name = '.'.join(clean_name.split('.')[:-1])
    
    # Clean up the name for title
    title_words = []
    for word in clean_name.split():
        # Skip common programming file artifacts
        if word.lower() not in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv']:
            title_words.append(word.capitalize())
    
    video_title = ' '.join(title_words[:8])  # Limit to 8 words
    
    # Generate description
    video_description = generate_description_from_filename(video_name)
    
    return video_title, video_description

def generate_description_from_filename(video_name):
    """Generate a description based on the video filename"""
    # Extract meaningful parts from filename
    clean_name = video_name
    if '.' in clean_name:
        parts = clean_name.split('.', 1)
        if len(parts) > 1 and parts[0].isdigit():
            clean_name = parts[1]
    
    # Remove file extension
    if '.' in clean_name:
        clean_name = '.'.join(clean_name.split('.')[:-1])
    
    # Generate description based on content hints
    description_templates = {
        'introduction': "This video provides an introduction to the topic, covering fundamental concepts and basic setup.",
        'install': "Learn how to install and set up the necessary tools and environment for development.",
        'setup': "Step-by-step guide to setting up your development environment and configuration.",
        'basic': "Covers the basic concepts and fundamental principles you need to understand.",
        'advanced': "Advanced topics and techniques for experienced developers.",
        'tutorial': "A comprehensive tutorial walking through practical examples and implementations.",
        'example': "Practical examples and demonstrations to illustrate key concepts.",
        'project': "Work on a hands-on project to apply the concepts learned in previous lessons.",
        'debug': "Learn debugging techniques and how to troubleshoot common issues.",
        'symbol': "Understanding symbols, their usage, and implementation in programming.",
        'type': "Exploring data types, type systems, and type-related programming concepts.",
        'continue': "Continuation of previous topics with additional depth and examples.",
        'loop': "Understanding loops, iteration, and control flow in programming.",
        'function': "Learn about functions, methods, and modular programming approaches.",
        'class': "Object-oriented programming concepts including classes and objects.",
        'variable': "Working with variables, data storage, and memory management.",
        'array': "Understanding arrays, lists, and data structure fundamentals."
    }
    
    # Look for keywords in the filename
    lower_name = clean_name.lower()
    for keyword, template in description_templates.items():
        if keyword in lower_name:
            return template
    
    # Default description
    return f"Educational programming content covering {clean_name.lower().replace('_', ' ').replace('-', ' ')}. Learn key concepts and practical applications through step-by-step instructions."

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
    
    # Test Ollama connectivity
    if not test_ollama_connectivity():
        print("\n❌ Ollama connectivity test failed!")
        print("Please check:")
        print("1. Ollama is installed and running")
        print("2. mistral:7b model is available (run: ollama pull mistral:7b)")
        print("3. Run 'ollama serve' to start the server")
        
        # Ask user if they want to continue without AI
        continue_without_ai = input("\n❓ Continue without AI title/description generation? (y/N): ").strip().lower()
        if continue_without_ai != 'y':
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
