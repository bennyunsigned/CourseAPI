import os
import sys
import json
import re
import random
import uuid
import requests
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm is not installed. Please run: pip install tqdm")
    sys.exit(1)

# Append parent dir for imports if needed
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from Utils.AES import AESCipher

# ================= OPTIONS =================
TARGET_DUMMY_USERS_COUNT = 50   # Ensure exactly this many dummy users exist in the database
TARGET_REVIEWS_PER_ITEM = 20    # The target number of reviews each course/product/bundle should have
CLEAN_PREVIOUS_REVIEWS = True  # If True, deletes all existing DUMMY reviews before inserting new ones
DUMMY_EMAIL_DOMAIN = "@dummy.vidyaroop.com" # Pattern to identify dummy users

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"
# ===========================================

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Fallback generic review texts in case Ollama is inaccessible or fails parsing
FALLBACK_REVIEWS = [
    "This was exactly what I needed! Highly recommend.",
    "Really good quality for the price.",
    "Met my expectations, very useful.",
    "Could be better, but still okay.",
    "I absolutely love this! 5 stars.",
    "Decent, but I expected a bit more depth.",
    "Fantastic experience overall.",
    "One of the best purchases I've made recently.",
    "Not really for me, but maybe good for others.",
    "Excellent value for money!",
    "I learned so much, the content is great.",
    "Very well structured and easy to follow.",
    "The quality is top notch.",
    "I would highly recommend this to anyone beginners or advanced.",
    "I had some issues at first but it grew on me."
]

FIRST_NAMES = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack", "Karen", "Leo", "Mia"]
LAST_NAMES = ["Smith", "Doe", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White"]

def generate_users(count):
    users = []
    for _ in range(count):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}.{uuid.uuid4().hex[:6]}{DUMMY_EMAIL_DOMAIN}"
        users.append({"name": name, "email": email})
    return users

def generate_item_specific_reviews(item_type, item_name, count):
    if count <= 0:
        return []

    prompt = f"Generate exactly {count} short, realistic, and unique customer reviews for a {item_type} named '{item_name}'. Return ONLY a valid JSON array of strings. Do not include any formatting, text, or markdown outside the JSON array."
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90) # generous timeout for item generation
        response.raise_for_status()
        content = response.json().get("response", "")
        
        # Parse JSON
        content = re.sub(r"```json", "", content)
        content = re.sub(r"```", "", content)
        content = content.strip()
        
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx+1]
            
        data = json.loads(content)
        parsed_list = None
        if isinstance(data, dict):
            for _, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                    parsed_list = val
                    break
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
            parsed_list = data
            
        if parsed_list:
            return parsed_list[:count]
    except Exception as e:
        pass # Silently fallback if anything fails during parsing or timeout
    
    return []

def main():
    print(f"--- Configuration ---")
    print(f"Target Dummy Users: {TARGET_DUMMY_USERS_COUNT}")
    print(f"Target Reviews Per Item: {TARGET_REVIEWS_PER_ITEM}")
    print(f"Clean Previous Reviews: {CLEAN_PREVIOUS_REVIEWS}")
    print(f"Dummy Email Domain: {DUMMY_EMAIL_DOMAIN}")
    print(f"Ollama Model: {OLLAMA_MODEL}")
    print(f"---------------------")

    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = connection.cursor(dictionary=True)

        aes = AESCipher()
        default_password = aes.encrypt("password123")
        default_phone = "0000000000"

        # Fetch existing dummy users first
        cursor.execute("SELECT id FROM Users WHERE email LIKE %s", (f"%{DUMMY_EMAIL_DOMAIN}",))
        dummy_users_pool = [row["id"] for row in cursor.fetchall()]
        existing_dummy_count = len(dummy_users_pool)

        if CLEAN_PREVIOUS_REVIEWS and existing_dummy_count > 0:
            print("Cleaning all previous dummy reviews...")
            in_clause = ','.join([str(u) for u in dummy_users_pool])
            cursor.execute(f"DELETE FROM customerreviews WHERE UserId IN ({in_clause})")
            connection.commit()
            print("Cleaned dummy reviews.")

        # Create new users only if we haven't reached TARGET_DUMMY_USERS_COUNT
        users_to_create = TARGET_DUMMY_USERS_COUNT - existing_dummy_count
        if users_to_create > 0:
            print(f"Target is {TARGET_DUMMY_USERS_COUNT} dummy users. {existing_dummy_count} exist. Creating {users_to_create} new dummy users...")
            new_users = generate_users(users_to_create)
            for u in new_users:
                cursor.execute("""
                    INSERT INTO Users (name, email, password, phone, provider, role, is_activated)
                    VALUES (%s, %s, %s, %s, 'local', 'User', 1)
                """, (u["name"], u["email"], default_password, default_phone))
            connection.commit()
            print(f"Inserted {users_to_create} new dummy users.")

            # Re-fetch the updated pool
            cursor.execute("SELECT id FROM Users WHERE email LIKE %s", (f"%{DUMMY_EMAIL_DOMAIN}",))
            dummy_users_pool = [row["id"] for row in cursor.fetchall()]
        else:
            print(f"Target is {TARGET_DUMMY_USERS_COUNT} dummy users. {existing_dummy_count} already exist. No new users needed.")

        if not dummy_users_pool:
            print("No dummy users exist in the database. Exiting.")
            return

        print(f"Total dummy users available in pool: {len(dummy_users_pool)}")

        # Fetch all courses, products, bundles with NAMES
        cursor.execute("SELECT CourseId, CourseName FROM coursemaster")
        courses = [(row["CourseId"], row["CourseName"]) for row in cursor.fetchall()]

        cursor.execute("SELECT ProductID, ProductName FROM productmaster")
        products = [(row["ProductID"], row["ProductName"]) for row in cursor.fetchall()]

        cursor.execute("SELECT BundleID, BundleName FROM bundlemaster")
        bundles = [(row["BundleID"], row["BundleName"]) for row in cursor.fetchall()]

        items_to_process = []
        for c, name in courses: items_to_process.append(("CourseId", c, "course", name))
        for p, name in products: items_to_process.append(("ProductId", p, "product", name))
        for b, name in bundles: items_to_process.append(("BundleId", b, "bundle", name))

        if not items_to_process:
            print("No courses, products, or bundles found in DB.")
            return

        reviews_added_total = 0
        errors = []

        # Process each item with progress bar and error handling
        print(f"Starting specific review generation and insertion for {len(items_to_process)} items...")
        for col_name, item_id, item_type, item_name in tqdm(items_to_process, desc="Processing items", unit="item"):
            try:
                # Query existing reviews for this item
                query = f"SELECT UserId FROM customerreviews WHERE {col_name} = %s"
                cursor.execute(query, (item_id,))
                existing_user_ids = {row["UserId"] for row in cursor.fetchall()}
                
                current_count = len(existing_user_ids)
                needed = TARGET_REVIEWS_PER_ITEM - current_count

                if needed > 0:
                    available_dummies = [uid for uid in dummy_users_pool if uid not in existing_user_ids]
                    to_add = min(needed, len(available_dummies))
                    
                    if to_add == 0:
                        continue
                        
                    selected_users = random.sample(available_dummies, to_add)
                    
                    # Generate specific reviews for this item
                    tailored_reviews = generate_item_specific_reviews(item_type, item_name, to_add)
                    
                    # Ensure we have enough reviews (pad with fallbacks if Ollama fell short)
                    while len(tailored_reviews) < to_add:
                        tailored_reviews.append(random.choice(FALLBACK_REVIEWS))
                    
                    for uid, r_text in zip(selected_users, tailored_reviews):
                        rating = random.randint(3, 5) # Usually 3 to 5 stars
                        
                        insert_query = f"""
                            INSERT INTO customerreviews 
                            (UserId, {col_name}, Rating, ReviewText)
                            VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (uid, item_id, rating, r_text))
                        reviews_added_total += 1
                        
                    connection.commit()
            except Exception as e:
                errors.append(f"Error at {col_name} {item_id}: {str(e)}")
                connection.rollback()

        print(f"\n--- Overall Status ---")
        print(f"Data insertion complete. Added {reviews_added_total} new realistic reviews.")
        if errors:
            print(f"Encountered {len(errors)} errors during processing:")
            for err in errors[:10]:
                print(f" - {err}")
            if len(errors) > 10:
                print(f" ... and {len(errors) - 10} more errors.")
        else:
            print("Successfully processed all items with zero errors.")

        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
