from fastapi import APIRouter, HTTPException, Query, Depends, Request
from DB.db import get_db_connection
from Utils.JWT import authenticate_request
import base64
import os
from Models.publicCourseContentModel import CourseContentModel, ModuleModel, VideoModel
import threading
import time
from typing import Dict, Any, List

course_progress_router = APIRouter()

# In-memory cache for category results. Keys: category_id -> {"data": [dict], "updated_at": timestamp}
_category_cache_lock = threading.Lock()
_category_cache: Dict[int, Dict[str, Any]] = {}

# Background refresher controls
_cache_thread: threading.Thread | None = None
_cache_stop_event: threading.Event | None = None

def _fetch_courses_by_category_from_db(category_id: int) -> List[dict]:
    """Perform DB call and return list of course dicts (same shape used to construct CourseContentModel)."""
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.callproc('GetCourseContentDetailsByCategory', [category_id])
        for result in cursor.stored_results():
            rows = result.fetchall()
            break
        else:
            rows = []

        response: List[dict] = []
        for row in rows:
            banner_path = row.get("BannerImage")
            base64_banner = None
            if banner_path and os.path.isfile("." + banner_path):
                with open("." + banner_path, "rb") as img_file:
                    base64_banner = "data:image/jpeg;base64," + base64.b64encode(img_file.read()).decode("utf-8")
            course_data = {
                "CourseId": row["CourseId"],
                "CourseName": row["CourseName"],
                "CourseDescription": row["CourseDescription"],
                "CourseInfo": row.get("CourseInfo"),
                "CourseLanguage": row.get("CourseLanguage"),
                "BannerImage": base64_banner,
                "Author": row.get("Author"),
                "Rating": row.get("Rating"),
                "ActualPrice": row["ActualPrice"],
                "DiscountedPrice": row["DiscountedPrice"],
                "IsPremium": row["IsPremium"],
                "IsBestSeller": row["IsBestSeller"],
                "VideoPath": row.get("VideoPath"),
                "IsPublic": row["IsPublic"],
                # prefer CourseDuration (proc) then TotalDurationPerCourse then 0
                "TotalDurationPerCourse": int(row.get("CourseDuration") if row.get("CourseDuration") is not None else (row.get("TotalDurationPerCourse") or 0)),
                "CategoryId": row["CategoryId"],
                "CategoryName": row["CategoryName"],
                "Modules": []  # no modules returned by this proc
            }
            response.append(course_data)
        return response
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def refresh_category_cache() -> None:
    """Refresh cache for all cached categories. Safe to call from background thread."""
    with _category_cache_lock:
        keys = list(_category_cache.keys())
    for cat_id in keys:
        try:
            data = _fetch_courses_by_category_from_db(cat_id)
            with _category_cache_lock:
                _category_cache[cat_id] = {"data": data, "updated_at": time.time()}
        except Exception as e:
            # keep existing cache on failure; print for visibility
            print(f"Failed to refresh cache for category {cat_id}: {e}")

def populate_category_cache(category_id: int) -> List[dict]:
    """Fetch from DB and store into cache (used by endpoint on first request)."""
    data = _fetch_courses_by_category_from_db(category_id)
    with _category_cache_lock:
        _category_cache[category_id] = {"data": data, "updated_at": time.time()}
    return data

def start_cache_refresh_thread(interval_seconds: int = 900) -> None:
    """Start background thread that refreshes cached categories every interval_seconds (default 15 minutes)."""
    global _cache_thread, _cache_stop_event
    if _cache_thread and _cache_thread.is_alive():
        return
    _cache_stop_event = threading.Event()

    def _run():
        # initial wait then loop
        while not _cache_stop_event.wait(interval_seconds):
            try:
                refresh_category_cache()
            except Exception as e:
                print("Cache refresher error:", e)

    _cache_thread = threading.Thread(target=_run, daemon=True)
    _cache_thread.start()

def stop_cache_refresh_thread() -> None:
    """Stop the background cache refresher thread if running."""
    global _cache_thread, _cache_stop_event
    if _cache_stop_event:
        _cache_stop_event.set()
    if _cache_thread:
        _cache_thread.join(timeout=5)
        _cache_thread = None
        _cache_stop_event = None

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
            # Normalize duration field: prefer CourseDuration (from proc), fallback to TotalDurationPerCourse or 0
            TotalDurationPerCourse=int(course_info.get("CourseDuration") if course_info.get("CourseDuration") is not None else (course_info.get("TotalDurationPerCourse") or 0)),
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



@course_progress_router.post("/course-module/")
async def insert_course_module(request: Request):
    data = await request.json()
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO CourseModule (ModuleId, CourseId, ModuleName, ModuleDescription, SequenceNo, CreatedBy, CreatedAt, UpdatedBy, UpdatedAt, Status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["ModuleId"],
                data["CourseId"],
                data["ModuleName"],
                data["ModuleDescription"],
                data["SequenceNo"],
                data.get("CreatedBy", "system"),
                data.get("CreatedAt"),
                data.get("UpdatedBy", "system"),
                data.get("UpdatedAt"),
                data.get("Status", "Active")
            )
        )
        connection.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@course_progress_router.post("/module-video/")
async def insert_module_video(request: Request):
    data = await request.json()
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO ModuleVideo (VideoId, CourseId, ModuleId, VideoTitle, VideoUrl, DurationInSeconds, SequenceNo, CreatedBy, CreatedAt, UpdatedBy, UpdatedAt, Status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["VideoId"],
                data["CourseId"],
                data["ModuleId"],
                data["VideoTitle"],
                data["VideoUrl"],
                data["DurationInSeconds"],
                data["SequenceNo"],
                data.get("CreatedBy", "system"),
                data.get("CreatedAt"),
                data.get("UpdatedBy", "system"),
                data.get("UpdatedAt"),
                data.get("Status", "Active")
            )
        )
        connection.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            
@course_progress_router.get("/public-course-content-by-category/", response_model=list[CourseContentModel])
def get_public_course_content_by_category(
    category_id: int = Query(..., description="Category ID")
):
    """
    Public endpoint to get course content details by category using the stored procedure GetCourseContentDetailsByCategory.
    Only category_id is accepted as input. BannerImage will be returned as a base64 string.
    """
    # Use cache if available, otherwise populate it.
    try:
        with _category_cache_lock:
            cached = _category_cache.get(category_id)
        if cached and isinstance(cached.get("data"), list):
            data = cached["data"]
        else:
            data = populate_category_cache(category_id)

        if not data:
            raise HTTPException(status_code=404, detail="No courses found for this category")

        # Build Pydantic models from cached dicts
        response = [CourseContentModel(**course) for course in data]
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
