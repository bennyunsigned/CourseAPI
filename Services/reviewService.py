from DB.db import get_db_connection
from Models.reviewModel import ReviewCreate, ReviewResponse
import mysql.connector
from datetime import datetime
from typing import Optional

def add_review(review: ReviewCreate) -> int:
    """Add a new review to the database."""
    # Convert to dict and sanitize 0/None values for Foreign Key columns
    review_data = review.dict()
    for key in ['courseId', 'bundleId', 'productId']:
        val = review_data.get(key)
        # Check if value is falsy (None, 0, or empty string)
        if not val:
            review_data[key] = None
        else:
            # Ensure it's an int if it's not None
            try:
                review_data[key] = int(val)
            except (ValueError, TypeError):
                review_data[key] = None

    query = """
    INSERT INTO CustomerReviews (UserId, CourseId, BundleId, ProductId, Rating, ReviewText)
    VALUES (%(userId)s, %(courseId)s, %(bundleId)s, %(productId)s, %(rating)s, %(reviewText)s)
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query, review_data)
            connection.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_top_reviews(limit: int = 30, course_id: Optional[int] = None, bundle_id: Optional[int] = None, product_id: Optional[int] = None):
    """Get the latest reviews with extended user information and optional filters."""
    query = """
    SELECT r.ReviewId, r.UserId, u.name as UserName, u.email as UserEmail, u.phone as UserPhone, u.user_image as UserImage,
           r.CourseId, r.BundleId, r.ProductId, r.Rating, r.ReviewText, r.CreatedAt, r.Status
    FROM CustomerReviews r
    JOIN Users u ON r.UserId = u.id
    WHERE r.Status = 'Active'
    """
    
    params = []
    if course_id is not None and course_id != 0:
        query += " AND r.CourseId = %s"
        params.append(course_id)
    if bundle_id is not None and bundle_id != 0:
        query += " AND r.BundleId = %s"
        params.append(bundle_id)
    if product_id is not None and product_id != 0:
        query += " AND r.ProductId = %s"
        params.append(product_id)

    query += " ORDER BY r.CreatedAt DESC LIMIT %s"
    params.append(limit)

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            reviews = []
            for row in rows:
                reviews.append(ReviewResponse(
                    reviewId=row['ReviewId'],
                    userId=row['UserId'],
                    userName=row['UserName'],
                    userEmail=row['UserEmail'],
                    userPhone=row['UserPhone'],
                    userImage=row['UserImage'],
                    courseId=row['CourseId'],
                    bundleId=row['BundleId'],
                    productId=row['ProductId'],
                    rating=row['Rating'],
                    reviewText=row['ReviewText'],
                    createdAt=row['CreatedAt'],
                    status=row['Status']
                ))
            return reviews
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")
