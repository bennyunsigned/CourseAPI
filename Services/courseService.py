from DB.db import get_db_connection
from Models.courseModel import CourseRequest, CourseResponse, CourseUpdateRequest
import mysql.connector

def create_course(course_data: CourseRequest, user_id: int) -> CourseResponse:
    print(CourseRequest)
    print("UserId:"+str(user_id))
    """
    Create a new course using an inline query.
    """
    query = """
        INSERT INTO CourseMaster (
            CategoryId,CourseName, CourseDescription, CourseInfo, CourseLanguage, BannerImage, Author, Rating,
            ActualPrice, DiscountedPrice, IsPremium, IsBestSeller, VideoPath, IsPublic, CreatedBy, Status
        ) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                query,
                (
                    course_data.category_id,  
                    course_data.course_name,
                    course_data.course_description,
                    course_data.course_info,
                    course_data.course_language,
                    course_data.banner_image,
                    course_data.author,
                    course_data.rating,
                    course_data.actual_price,
                    course_data.discounted_price,
                    course_data.is_premium,
                    course_data.is_best_seller,
                    course_data.video_path,
                    course_data.is_public,
                    user_id,
                    "Active",  # Default status
                ),
            )
            connection.commit()

            # Retrieve the newly created course ID
            course_id = cursor.lastrowid

            # Return the full course response
            return CourseResponse(
                course_id=course_id,
                category_id=course_data.category_id,
                course_name=course_data.course_name,
                course_description=course_data.course_description,
                course_info=course_data.course_info,
                course_language=course_data.course_language,
                banner_image=course_data.banner_image,
                author=course_data.author,
                rating=course_data.rating,
                actual_price=course_data.actual_price,
                discounted_price=course_data.discounted_price,
                is_premium=course_data.is_premium,
                is_best_seller=course_data.is_best_seller,
                video_path=course_data.video_path,
                is_public=course_data.is_public,
                created_by=str(user_id),  # Convert user_id to string
                status="Active",
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_course_by_id(course_id: int) -> CourseResponse:
    """
    Retrieve a course by its ID using an inline query.
    """
    query = "SELECT * FROM CourseMaster WHERE CourseId = %s"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (course_id,))
            course = cursor.fetchone()
            if not course:
                raise Exception("Course not found")
            return CourseResponse(
                course_id=course["CourseId"],
                category_id=course["CategoryId"],
                course_name=course["CourseName"],
                course_description=course["CourseDescription"],
                course_info=course["CourseInfo"],
                course_language=course["CourseLanguage"],
                banner_image=course["BannerImage"],
                author=course["Author"],
                rating=course["Rating"],
                actual_price=course["ActualPrice"],
                discounted_price=course["DiscountedPrice"],
                is_premium=course["IsPremium"],
                is_best_seller=course["IsBestSeller"],
                video_path=course["VideoPath"],
                is_public=course["IsPublic"],
                created_by=course["CreatedBy"],
                status=course["Status"],
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def update_course(course_id: int, course_data: CourseUpdateRequest, updated_by: int) -> str:
    """
    Update a course using an inline query.
    """
    query = """
        UPDATE CourseMaster
        SET CategoryId=%s,
            CourseName = %s,
            CourseDescription = %s,
            CourseInfo = %s,
            CourseLanguage = %s,
            BannerImage = %s,
            Author = %s,
            Rating = %s,
            ActualPrice = %s,
            DiscountedPrice = %s,
            IsPremium = %s,
            IsBestSeller = %s,
            VideoPath = %s,
            IsPublic = %s,
            UpdatedBy = %s,
            UpdatedAt = NOW(),
            Status = %s
        WHERE CourseId = %s
    """
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                query,
                (
                    course_data.category_id, 
                    course_data.course_name,
                    course_data.course_description,
                    course_data.course_info,
                    course_data.course_language,
                    course_data.banner_image,
                    course_data.author,
                    course_data.rating,
                    course_data.actual_price,
                    course_data.discounted_price,
                    course_data.is_premium,
                    course_data.is_best_seller,
                    course_data.video_path,
                    course_data.is_public,
                    updated_by,  # Use the updated_by parameter
                    "Active",  # Default status
                    course_id,
                ),
            )
            connection.commit()
            return "Course updated successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def delete_course(course_id: int) -> str:
    """
    Delete a course using an inline query.
    """
    query = "DELETE FROM CourseMaster WHERE CourseId = %s"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query, (course_id,))
            connection.commit()
            return "Course deleted successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_all_courses() -> list[CourseResponse]:
    """
    Retrieve all courses using an inline query.
    """
    query = "SELECT * FROM CourseMaster where Status = 'Active' ORDER BY CourseId DESC"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            courses = cursor.fetchall()
            if not courses:
                return []
            return [
                CourseResponse(
                    course_id=course["CourseId"],
                    category_id=course["CategoryId"],
                    course_name=course["CourseName"],
                    course_description=course["CourseDescription"],
                    course_info=course["CourseInfo"],
                    course_language=course["CourseLanguage"],
                    banner_image=course["BannerImage"],
                    author=course["Author"],
                    rating=course["Rating"],
                    actual_price=course["ActualPrice"],
                    discounted_price=course["DiscountedPrice"],
                    is_premium=course["IsPremium"],
                    is_best_seller=course["IsBestSeller"],
                    video_path=course["VideoPath"],
                    is_public=course["IsPublic"],
                    created_by=course["CreatedBy"],
                    status=course["Status"],
                )
                for course in courses
            ]
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")