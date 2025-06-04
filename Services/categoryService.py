from DB.db import get_db_connection
from Models.categoryModel import CategoryRequest, CategoryResponse, CategoryUpdateRequest
import mysql.connector

def create_category(category_data: CategoryRequest, user_id: int) -> CategoryResponse:
    query = """
        INSERT INTO CategoryMaster (
            CategoryName, CreatedBy, Status
        ) VALUES (%s, %s, %s)
    """
    print("Creating category with data:", category_data)
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (
            category_data.CategoryName,            
            user_id,
            'Active'            
        ))
        connection.commit()
        CategoryId = cursor.lastrowid
        return CategoryResponse(
            CategoryId=CategoryId,
            CategoryName=category_data.CategoryName,   
            CreatedBy=str(user_id),         
            Status='Active',
        )
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def get_category_by_id(CategoryId: int) -> CategoryResponse:
    query = "SELECT CategoryId,CategoryName,CreatedBy,Status FROM CategoryMaster WHERE CategoryId = %s"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (CategoryId,))
        category = cursor.fetchone()        
        if not category:
            raise Exception("Module not found")
        return CategoryResponse(
            CategoryId=category["CategoryId"],
            CategoryName=category["CategoryName"],            
            CreatedBy=category["CreatedBy"],
            Status=category["Status"]
        )
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def get_all_categories() -> list[CategoryResponse]:
    query = "SELECT CategoryId,CategoryName,CreatedBy,Status FROM CategoryMaster where Status='Active'"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        categories = cursor.fetchall()
        return [
            CategoryResponse(
                CategoryId=category["CategoryId"],
                CategoryName=category["CategoryName"],            
                CreatedBy=category["CreatedBy"],
                Status=category["Status"]
            ) for category in categories
        ]
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def update_category(CategoryId: int, category_data: CategoryUpdateRequest, UpdatedBy: int) -> str:
    query = """
        UPDATE CategoryMaster SET            
            CategoryName = %s,                  
            UpdatedBy = %s,
            UpdatedAt = NOW(),
            Status = %s
        WHERE CategoryId = %s
    """
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, (
            category_data.CategoryName,            
            UpdatedBy,
            'Active',
            CategoryId
        ))
        connection.commit()
        return "Category updated successfully"
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

def delete_category(CategoryId: int) -> str:
    query = "update CategoryMaster set Status='Deactive' WHERE CategoryId = %s"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, (CategoryId,))
        connection.commit()
        return "Category deleted successfully"
    finally:
        if cursor: cursor.close()
        if connection: connection.close()



