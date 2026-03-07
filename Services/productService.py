from DB.db import get_db_connection
from Models.productModel import ProductRequest, ProductResponse, ProductUpdateRequest, ProductAttachmentRequest, ProductAttachmentResponse
import mysql.connector

def create_product(product_data: ProductRequest) -> ProductResponse:
    """
    Create a new product using an inline query.
    """
    query = """
        INSERT INTO ProductMaster (
            ProductName, ActualProductPrice, DiscountProductPrice, 
            ProductDescription, ProductContent, ProductImage, IsActive,
            EmailSubject, EmailBody
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                query,
                (
                    product_data.product_name,
                    product_data.product_price,
                    product_data.product_discount_price,
                    product_data.product_description,
                    product_data.product_content,
                    product_data.product_image,
                    product_data.is_active,
                    product_data.email_subject,
                    product_data.email_body,
                ),
            )
            connection.commit()

            # Retrieve the newly created product ID
            product_id = cursor.lastrowid

            # Fetch the created product to get timestamps
            cursor.execute("SELECT * FROM ProductMaster WHERE ProductID = %s", (product_id,))
            product = cursor.fetchone()

            # Return the full product response
            return ProductResponse(
                product_id=product["ProductID"],
                product_name=product["ProductName"],
                product_price=product["ActualProductPrice"],
                product_discount_price=product["DiscountProductPrice"],
                product_description=product["ProductDescription"],
                product_content=product["ProductContent"],
                product_image=product["ProductImage"],
                is_active=product.get("IsActive", True),
                email_subject=product.get("EmailSubject"),
                email_body=product.get("EmailBody"),
                created_on=product["CreatedOn"].isoformat() if product.get("CreatedOn") else None,
                updated_on=product["UpdatedOn"].isoformat() if product.get("UpdatedOn") else None,
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_product_by_id(product_id: int) -> ProductResponse:
    """
    Retrieve a product by its ID using an inline query.
    """
    query = "SELECT * FROM ProductMaster WHERE ProductID = %s"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (product_id,))
            product = cursor.fetchone()
            if not product:
                raise Exception("Product not found")
            return ProductResponse(
                product_id=product["ProductID"],
                product_name=product["ProductName"],
                product_price=product["ActualProductPrice"],
                product_discount_price=product["DiscountProductPrice"],
                product_description=product["ProductDescription"],
                product_content=product["ProductContent"],
                product_image=product["ProductImage"],
                is_active=product.get("IsActive", True),
                email_subject=product.get("EmailSubject"),
                email_body=product.get("EmailBody"),
                created_on=product["CreatedOn"].isoformat() if product.get("CreatedOn") else None,
                updated_on=product["UpdatedOn"].isoformat() if product.get("UpdatedOn") else None,
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def update_product(product_id: int, product_data: ProductUpdateRequest) -> str:
    """
    Update a product using an inline query.
    """
    query = """
        UPDATE ProductMaster
        SET ProductName = %s,
            ActualProductPrice = %s,
            DiscountProductPrice = %s,
            ProductDescription = %s,
            ProductContent = %s,
            ProductImage = %s,
            IsActive = %s,
            EmailSubject = %s,
            EmailBody = %s,
            UpdatedOn = NOW()
        WHERE ProductID = %s
    """
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                query,
                (
                    product_data.product_name,
                    product_data.product_price,
                    product_data.product_discount_price,
                    product_data.product_description,
                    product_data.product_content,
                    product_data.product_image,
                    product_data.is_active,
                    product_data.email_subject,
                    product_data.email_body,
                    product_id,
                ),
            )
            connection.commit()
            return "Product updated successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def delete_product(product_id: int) -> str:
    """
    Delete a product using an inline query.
    """
    query = "DELETE FROM ProductMaster WHERE ProductID = %s"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query, (product_id,))
            connection.commit()
            return "Product deleted successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_all_products() -> list[ProductResponse]:
    """
    Retrieve all products using an inline query.
    """
    query = "SELECT * FROM ProductMaster ORDER BY ProductID DESC"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            products = cursor.fetchall()
            if not products:
                return []
            return [
                ProductResponse(
                    product_id=product["ProductID"],
                    product_name=product["ProductName"],
                    product_price=product["ActualProductPrice"],
                    product_discount_price=product["DiscountProductPrice"],
                    product_description=product["ProductDescription"],
                    product_content=product["ProductContent"],
                    product_image=product["ProductImage"],
                    is_active=product.get("IsActive", True),
                    email_subject=product.get("EmailSubject"),
                    email_body=product.get("EmailBody"),
                    created_on=product["CreatedOn"].isoformat() if product.get("CreatedOn") else None,
                    updated_on=product["UpdatedOn"].isoformat() if product.get("UpdatedOn") else None,
                    attachments=get_product_attachments(product["ProductID"])
                )
                for product in products
            ]
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_product_attachments(product_id: int) -> list[ProductAttachmentResponse]:
    """
    Retrieve all attachments for a specific product.
    """
    query = "SELECT * FROM ProductAttachments WHERE ProductID = %s"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (product_id,))
            attachments = cursor.fetchall()
            return [
                ProductAttachmentResponse(
                    attachment_id=item["AttachmentID"],
                    product_id=item["ProductID"],
                    file_name=item["FileName"],
                    file_url=item["FileURL"],
                    file_type=item["FileType"],
                    uploaded_on=item["UploadedOn"].isoformat() if item["UploadedOn"] else None
                )
                for item in attachments
            ]
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    return []

def save_product_attachments(product_id: int, attachments: list[ProductAttachmentRequest]) -> str:
    """
    Save multiple attachments for a product.
    """
    delete_query = "DELETE FROM ProductAttachments WHERE ProductID = %s"
    insert_query = """
        INSERT INTO ProductAttachments (ProductID, FileName, FileURL, FileType)
        VALUES (%s, %s, %s, %s)
    """
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            # For simplicity, we replace existing attachments. 
            # Alternatively, we could perform an incremental update.
            cursor.execute(delete_query, (product_id,))
            
            for att in attachments:
                cursor.execute(insert_query, (product_id, att.file_name, att.file_url, att.file_type))
            
            connection.commit()
            return "Attachments saved successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def delete_product_attachment(product_id: int, attachment_id: int) -> str:
    """
    Delete a specific attachment for a product.
    """
    query = "DELETE FROM ProductAttachments WHERE ProductID = %s AND AttachmentID = %s"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query, (product_id, attachment_id))
            connection.commit()
            if cursor.rowcount == 0:
                raise Exception("Attachment not found or does not belong to the product")
            return "Attachment deleted successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_all_attachment_details(product_id: int) -> list[ProductAttachmentResponse]:
    """
    Retrieve all attachments for a specific product.
    """
    query = "SELECT * FROM ProductAttachments WHERE ProductID = %s ORDER BY UploadedOn DESC"
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (product_id,))
            attachments = cursor.fetchall()
            return [
                ProductAttachmentResponse(
                    attachment_id=item["AttachmentID"],
                    product_id=item["ProductID"],
                    file_name=item["FileName"],
                    file_url=item["FileURL"],
                    file_type=item["FileType"],
                    uploaded_on=item["UploadedOn"].isoformat() if item["UploadedOn"] else None
                )
                for item in attachments
            ]
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor:
                cursor.close()
            connection.close()
    return []
