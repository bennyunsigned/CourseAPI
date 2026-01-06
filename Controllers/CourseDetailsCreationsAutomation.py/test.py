from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import urllib.request
import os

USERNAME = "lakhanmaheswari24"
OUTPUT_FOLDER = "Reels"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=chrome_options)

driver.get(f"https://www.instagram.com/{USERNAME}/reels/")
time.sleep(5)

# Scroll to load reels
for _ in range(10):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

links = set()
elements = driver.find_elements(By.TAG_NAME, "a")

for el in elements:
    href = el.get_attribute("href")
    if href and "/reel/" in href:
        links.add(href)

print(f"Found {len(links)} reels")

for i, url in enumerate(links):
    driver.get(url)
    time.sleep(3)

    try:
        video = driver.find_element(By.TAG_NAME, "video")
        src = video.get_attribute("src")

        urllib.request.urlretrieve(src, f"{OUTPUT_FOLDER}/reel_{i}.mp4")
        print(f"Saved reel_{i}.mp4")
    except:
        print("Error downloading reel")

driver.quit()
