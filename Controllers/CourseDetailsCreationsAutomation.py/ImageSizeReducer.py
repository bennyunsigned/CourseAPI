import os
from PIL import Image

# Set your folder path here
FOLDER_PATH = r"c:\Users\benny\Desktop\Apps\CourseAPI\Uploads\CourseImages"

# Desired output size (width, height)
OUTPUT_SIZE = (800, 800)  # Change as needed

def reduce_image_size(folder_path, output_size):
	for filename in os.listdir(folder_path):
		if filename.lower().endswith((".jpg", ".jpeg", ".png")):
			file_path = os.path.join(folder_path, filename)
			try:
				with Image.open(file_path) as img:
					img = img.convert("RGB")
					img.thumbnail(output_size)
					# Try different quality levels to get under 10KB
					for quality in range(85, 5, -5):
						img.save(file_path, optimize=True, quality=quality)
						if os.path.getsize(file_path) <= 10 * 1024:
							print(f"Reduced size for: {filename} (quality={quality})")
							break
					else:
						# If still too large, try reducing dimensions further
						for scale in [0.8, 0.6, 0.4, 0.2]:
							new_size = (int(output_size[0]*scale), int(output_size[1]*scale))
							img.thumbnail(new_size)
							img.save(file_path, optimize=True, quality=10)
							if os.path.getsize(file_path) <= 10 * 1024:
								print(f"Reduced size for: {filename} (scale={scale}, quality=10)")
								break
						else:
							print(f"Could not reduce {filename} below 10KB, final size: {os.path.getsize(file_path)//1024}KB")
			except Exception as e:
				print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
	reduce_image_size(FOLDER_PATH, OUTPUT_SIZE)
