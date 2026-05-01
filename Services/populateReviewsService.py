from DB.db import get_db_connection
import mysql.connector
from typing import List, Dict, Any

def get_dummy_users(domain: str) -> List[int]:
    connection = get_db_connection()
    if not connection:
        raise Exception("Database connection failed")
    
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT id FROM Users WHERE email LIKE %s"
        cursor.execute(query, (f"%{domain}",))
        return [row["id"] for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

def clean_dummy_reviews(user_ids: List[int]) -> int:
    if not user_ids:
        return 0
        
    connection = get_db_connection()
    if not connection:
        raise Exception("Database connection failed")
        
    try:
        cursor = connection.cursor()
        format_strings = ','.join(['%s'] * len(user_ids))
        query = f"DELETE FROM customerreviews WHERE UserId IN ({format_strings})"
        cursor.execute(query, tuple(user_ids))
        connection.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        connection.close()

def insert_dummy_users(users: List[Dict[str, Any]]) -> int:
    if not users:
        return 0
        
    connection = get_db_connection()
    if not connection:
        raise Exception("Database connection failed")
        
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO Users (name, email, password, phone, provider, role, is_activated)
            VALUES (%s, %s, %s, %s, 'local', 'User', 1)
        """
        values = [(u["name"], u["email"], u["password"], u["phone"]) for u in users]
        cursor.executemany(query, values)
        connection.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        connection.close()

def get_all_items() -> Dict[str, List[Dict[str, Any]]]:
    connection = get_db_connection()
    if not connection:
        raise Exception("Database connection failed")
        
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT CourseId, CourseName FROM coursemaster")
        courses = [{"id": row["CourseId"], "name": row["CourseName"]} for row in cursor.fetchall()]
        
        cursor.execute("SELECT ProductID as ProductId, ProductName FROM productmaster")
        products = [{"id": row["ProductId"], "name": row["ProductName"]} for row in cursor.fetchall()]
        
        cursor.execute("SELECT BundleID as BundleId, BundleName FROM bundlemaster")
        bundles = [{"id": row["BundleId"], "name": row["BundleName"]} for row in cursor.fetchall()]
        
        return {
            "courses": courses,
            "products": products,
            "bundles": bundles
        }
    finally:
        cursor.close()
        connection.close()

def get_item_reviewers(col_name: str, item_id: int) -> List[int]:
    allowed_cols = ["CourseId", "ProductId", "BundleId"]
    if col_name not in allowed_cols:
        raise ValueError(f"Invalid column name: {col_name}")
        
    connection = get_db_connection()
    if not connection:
        raise Exception("Database connection failed")
        
    try:
        cursor = connection.cursor(dictionary=True)
        query = f"SELECT UserId FROM customerreviews WHERE {col_name} = %s"
        cursor.execute(query, (item_id,))
        return [row["UserId"] for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

def insert_reviews(reviews: List[Dict[str, Any]]) -> int:
    if not reviews:
        return 0
        
    connection = get_db_connection()
    if not connection:
        raise Exception("Database connection failed")
        
    try:
        cursor = connection.cursor()
        
        # Determine the columns to insert. Not all reviews might be for the same item type,
        # but to use executemany we need a uniform structure, or we can iterate.
        # Since the script inserts per item, we can just iterate.
        inserted = 0
        for r in reviews:
            # Expected keys: userId, colName (CourseId, ProductId, BundleId), itemId, rating, reviewText
            col_name = r.get("colName")
            allowed_cols = ["CourseId", "ProductId", "BundleId"]
            if col_name not in allowed_cols:
                continue
                
            query = f"""
                INSERT INTO customerreviews 
                (UserId, {col_name}, Rating, ReviewText)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (r["userId"], r["itemId"], r["rating"], r["reviewText"]))
            inserted += 1
            
        connection.commit()
        return inserted
    finally:
        cursor.close()
        connection.close()
