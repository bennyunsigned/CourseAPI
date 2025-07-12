from fastapi import APIRouter, HTTPException, Query, Depends
from DB.db import get_db_connection
from Utils.JWT import authenticate_request

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