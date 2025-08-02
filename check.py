import requests
from moviepy.editor import VideoFileClip
import tempfile
import os
from urllib.parse import urlparse, unquote


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
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None


def get_video_duration_mmss(details_url):
    download_url = convert_to_download_url(details_url)
    if not download_url:
        return "Invalid archive.org /details/ URL"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            print("Downloading video...")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                temp_video.write(chunk)

        # Load video and get duration
        clip = VideoFileClip(temp_video.name)
        duration = int(clip.duration)
        clip.close()

        minutes = duration // 60
        seconds = duration % 60
        return f"{minutes:02d}:{seconds:02d}"

    except Exception as e:
        return f"Error processing video: {e}"
    finally:
        if os.path.exists(temp_video.name):
            os.remove(temp_video.name)


# Example usage:
if __name__ == "__main__":
    url = "https://archive.org/details/001-introduction_202507/001+Introduction.mp4"
    print("Duration:", get_video_duration_mmss(url))
