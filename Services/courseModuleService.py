from DB.db import get_db_connection
from Models.courseModuleModel import CourseModuleRequest, CourseModuleResponse, CourseModuleUpdateRequest
import mysql.connector

def create_module(module_data: CourseModuleRequest, user_id: int) -> CourseModuleResponse:
    query = """
        INSERT INTO CourseModule (
            CourseId, ModuleName, ModuleDescription,
            SequenceNo, CreatedBy, Status
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    print("Creating module with data:", module_data)
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (
            module_data.CourseId,
            module_data.ModuleName,
            module_data.ModuleDescription,
            module_data.SequenceNo,
            user_id,
            'Active'            
            
        ))
        connection.commit()
        ModuleId = cursor.lastrowid
        return CourseModuleResponse(
            ModuleId=ModuleId,
            CourseId=module_data.CourseId,
            ModuleName=module_data.ModuleName,
            ModuleDescription=module_data.ModuleDescription,
            SequenceNo=str(module_data.SequenceNo) if module_data.SequenceNo is not None else None,
            Status='Active',
            CreatedBy=str(user_id),
            
        )
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def get_module_by_id(ModuleId: int) -> CourseModuleResponse:
    query = "SELECT ModuleId,CourseId,ModuleName,ModuleDescription,SequenceNo,CreatedBy,Status FROM CourseModule WHERE ModuleId = %s"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (ModuleId,))
        module = cursor.fetchone()
        print(module)
        if not module:
            raise Exception("Module not found")
        return CourseModuleResponse(
            ModuleId=module["ModuleId"],
            CourseId=module["CourseId"],
            ModuleName=module["ModuleName"],
            ModuleDescription=module["ModuleDescription"],
            SequenceNo=str(module["SequenceNo"]) if module["SequenceNo"] is not None else None,            
            CreatedBy=module["CreatedBy"],
            Status=module["Status"]
        )
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def get_all_modules() -> list[CourseModuleResponse]:
    query = "SELECT A.CourseId,B.CourseName,A.ModuleId,A.ModuleName,A.ModuleDescription,A.SequenceNo,A.CreatedBy,A.Status FROM CourseModule A inner join CourseMaster B on A.CourseId=B.CourseId where A.Status='Active'"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        modules = cursor.fetchall()
        return [
            CourseModuleResponse(
                ModuleId=m["ModuleId"],
                CourseId=m["CourseId"],
                ModuleName=m["ModuleName"],
                ModuleDescription=m["ModuleDescription"],
                SequenceNo=str(m["SequenceNo"]) if m["SequenceNo"] is not None else None,               
                CreatedBy=m["CreatedBy"],
                Status=m["Status"],
                CourseName=m["CourseName"] if m["CourseName"] is not None else None
            ) for m in modules
        ]
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def update_module(ModuleId: int, module_data: CourseModuleUpdateRequest, UpdatedBy: int) -> str:
    query = """
        UPDATE CourseModule SET
            CourseId = %s,
            ModuleName = %s,
            ModuleDescription = %s,
            SequenceNo = %s,            
            UpdatedBy = %s,
            UpdatedAt = NOW(),
            Status = %s
        WHERE ModuleId = %s
    """
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, (
            module_data.CourseId,
            module_data.ModuleName,
            module_data.ModuleDescription,
            module_data.SequenceNo,
            UpdatedBy,
            module_data.Status,
            ModuleId
        ))
        connection.commit()
        return "Module updated successfully"
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def delete_module(ModuleId: int) -> str:
    query = "update CourseModule set Status='Deactive' WHERE ModuleId = %s"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, (ModuleId,))
        connection.commit()
        return "Module deleted successfully"
    finally:
        if cursor: cursor.close()
        if connection: connection.close()



