from fastapi import APIRouter, HTTPException, Query, Depends
from DB.db import get_db_connection
from Utils.JWT import authenticate_request
import base64
import os
from Models.publicCourseContentModel import CourseContentModel, ModuleModel, VideoModel

course_progress_router = APIRouter()

@course_progress_router.get("/course-progress/")
def get_course_progress(
    course_id: int = Query(..., description="Course ID"),
    claims: dict = Depends(authenticate_request)
):
    query = """
    SELECT 
        A.CourseId,
        B.CourseName,
        B.CourseDescription,
        A.ModuleId,
        A.ModuleName,
        A.ModuleDescription,
        A.SequenceNo as ModuleSequence,
        C.VideoTitle,
        C.VideoUrl,
        C.DurationInSeconds,
        C.SequenceNo as VideoSequence
    FROM CourseModule A 
    INNER JOIN CourseMaster B ON A.CourseId=B.CourseId 
    INNER JOIN ModuleVideo C ON A.ModuleId=C.ModuleId
    WHERE A.Status='Active' AND B.Status='Active' AND A.CourseId=%s
    ORDER BY A.SequenceNo, C.SequenceNo
    """
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (course_id,))
        results = cursor.fetchall()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@course_progress_router.get("/public-course-content/", response_model=CourseContentModel)
def get_public_course_content(
    course_id: int = Query(..., description="Course ID")
):
    """
    Public endpoint to get course content details using the stored procedure.
    BannerImage will be returned as a base64 string.
    """
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.callproc('GetCourseContentDetails', [course_id])
        for result in cursor.stored_results():
            rows = result.fetchall()
            break
        else:
            rows = []

        if not rows:
            raise HTTPException(status_code=404, detail="Course not found")

        # Extract course-level info from the first row
        course_info = rows[0]
        banner_path = course_info.get("BannerImage")
        base64_banner = None
        if banner_path and os.path.isfile("." + banner_path):
            with open("." + banner_path, "rb") as img_file:
                base64_banner = "data:image/jpeg;base64," + base64.b64encode(img_file.read()).decode("utf-8")

        # Organize modules and videos
        modules_dict = {}
        for row in rows:
            mod_id = row["ModuleId"]
            if mod_id not in modules_dict:
                modules_dict[mod_id] = {
                    "ModuleId": mod_id,
                    "ModuleName": row["ModuleName"],
                    "ModuleDescription": row["ModuleDescription"],
                    "ModuleSequenceNo": row["ModuleSequenceNo"],
                    "TotalDurationPerModule": row["TotalDurationPerModule"],
                    "Videos": []
                }
            modules_dict[mod_id]["Videos"].append(VideoModel(
                VideoId=row["VideoId"],
                VideoTitle=row["VideoTitle"],
                VideoUrl=row["VideoUrl"],
                DurationInSeconds=int(row["DurationInSeconds"]),
                VideoSequenceNo=row["VideoSequenceNo"]
            ))

        # Build the response model
        response = CourseContentModel(
            CourseId=course_info["CourseId"],
            CourseName=course_info["CourseName"],
            CourseDescription=course_info["CourseDescription"],
            CourseInfo=course_info.get("CourseInfo"),
            CourseLanguage=course_info.get("CourseLanguage"),
            BannerImage=base64_banner,
            Author=course_info.get("Author"),
            Rating=course_info.get("Rating"),
            ActualPrice=course_info["ActualPrice"],
            DiscountedPrice=course_info["DiscountedPrice"],
            IsPremium=course_info["IsPremium"],
            IsBestSeller=course_info["IsBestSeller"],
            VideoPath=course_info.get("VideoPath"),
            IsPublic=course_info["IsPublic"],
            TotalDurationPerCourse=course_info["TotalDurationPerCourse"],
            Modules=[ModuleModel(**mod) for mod in modules_dict.values()]
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@course_progress_router.get("/max-module-id/")
def get_max_module_id():
    """
    Returns the maximum ModuleId from courseModule table.
    """
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT MAX(ModuleId) AS MaxModuleId FROM CourseModule")
        result = cursor.fetchone()
        return {"MaxModuleId": result["MaxModuleId"] if result["MaxModuleId"] is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@course_progress_router.get("/max-video-id/")
def get_max_video_id():
    """
    Returns the maximum VideoId from modulevideo table.
    """
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT MAX(VideoId) AS MaxVideoId FROM ModuleVideo")
        result = cursor.fetchone()
        return {"MaxVideoId": result["MaxVideoId"] if result["MaxVideoId"] is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()