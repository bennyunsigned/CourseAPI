import requests
import os
import subprocess
from openpyxl import Workbook
import sys
from tqdm import tqdm

def get_video_urls_from_archive_org(identifier):
    metadata_url = f"https://archive.org/metadata/{identifier}"
    try:
        response = requests.get(metadata_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata: {e}")
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
    except Exception as e:
        print(f"Error getting duration for {filepath}: {e}")
        return 0

def download_video(url, dest):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def print_progress(current, total, bar_length=40):
    percent = float(current) / total
    arrow = '-' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    sys.stdout.write(f"\rProgress: [{arrow}{spaces}] {int(percent*100)}% ({current}/{total})")
    sys.stdout.flush()
    if current == total:
        print()  # Move to next line

if __name__ == "__main__":
    item_identifier = "1.-java-programming-bootcamp-zero-to-mastery-zero-to-mastery-academy-1920x-1080-4085-k"  # Replace as needed
    videos = get_video_urls_from_archive_org(item_identifier)

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Sl", "VideoURL", "VideoTitle", "VideoDescription", "Duration", "InsertQueries"])

    temp_dir = "temp_videos"
    os.makedirs(temp_dir, exist_ok=True)

    for idx, video in enumerate(tqdm(videos, desc="Processing videos", unit="video"), 1):
        video_url = video["url"]
        video_name = video["name"]
        local_path = os.path.join(temp_dir, video_name)

        print(f"\nDownloading {video_url} ...")
        if download_video(video_url, local_path):
            duration = get_video_duration(local_path)
        else:
            duration = 0

        # Fill Excel row
        ws.append([
            idx,
            video_url,
            video_name,
            "",  # Description placeholder
            duration,
            ""   # InsertQueries placeholder
        ])

        # Optionally, remove the video after processing to save space
        os.remove(local_path)

    excel_filename = f"{item_identifier}_videos.xlsx"
    wb.save(excel_filename)
    print(f"Excel file saved as {excel_filename}")
