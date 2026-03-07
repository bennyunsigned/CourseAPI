from DB.db import get_db_connection
from Models.bundleModel import BundleRequest, BundleResponse, BundleUpdateRequest
from Models.productModel import ProductResponse
from Services.productService import get_product_by_id
import mysql.connector

def create_bundle(bundle_data: BundleRequest) -> BundleResponse:
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Insert into BundleMaster
            query_bundle = """
                INSERT INTO BundleMaster (BundleName, BundleDescription, ActualBundlePrice, DiscountBundlePrice, IsActive, EmailSubject, EmailBody)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_bundle, (
                bundle_data.bundle_name,
                bundle_data.bundle_description,
                bundle_data.bundle_price,
                bundle_data.bundle_discount_price,
                bundle_data.is_active,
                bundle_data.email_subject,
                bundle_data.email_body
            ))
            bundle_id = cursor.lastrowid
            
            # Insert into BundleMapping
            query_mapping = "INSERT INTO BundleMapping (BundleID, ProductID) VALUES (%s, %s)"
            for product_id in bundle_data.product_ids:
                cursor.execute(query_mapping, (bundle_id, product_id))
            
            connection.commit()
            return get_bundle_by_id(bundle_id)
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_bundle_by_id(bundle_id: int) -> BundleResponse:
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM BundleMaster WHERE BundleID = %s", (bundle_id,))
            bundle = cursor.fetchone()
            if not bundle:
                raise Exception("Bundle not found")
            
            # Fetch products in this bundle
            cursor.execute("""
                SELECT p.* FROM ProductMaster p
                JOIN BundleMapping bm ON p.ProductID = bm.ProductID
                WHERE bm.BundleID = %s
            """, (bundle_id,))
            products_data = cursor.fetchall()
            
            products = [
                ProductResponse(
                    product_id=p["ProductID"],
                    product_name=p["ProductName"],
                    product_price=p["ActualProductPrice"],
                    product_discount_price=p["DiscountProductPrice"],
                    product_description=p["ProductDescription"],
                    product_content=p["ProductContent"],
                    product_image=p["ProductImage"],
                    is_active=p.get("IsActive", True),
                    created_on=p["CreatedOn"].isoformat() if p.get("CreatedOn") else None,
                    updated_on=p["UpdatedOn"].isoformat() if p.get("UpdatedOn") else None
                ) for p in products_data
            ]
            
            return BundleResponse(
                bundle_id=bundle["BundleID"],
                bundle_name=bundle["BundleName"],
                bundle_description=bundle["BundleDescription"],
                bundle_price=bundle["ActualBundlePrice"],
                bundle_discount_price=bundle["DiscountBundlePrice"],
                is_active=bundle.get("IsActive", True),
                email_subject=bundle.get("EmailSubject"),
                email_body=bundle.get("EmailBody"),
                created_on=bundle["CreatedOn"].isoformat() if bundle.get("CreatedOn") else None,
                updated_on=bundle["UpdatedOn"].isoformat() if bundle.get("UpdatedOn") else None,
                products=products
            )
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def get_all_bundles() -> list[BundleResponse]:
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT BundleID FROM BundleMaster ORDER BY BundleID DESC")
            bundle_ids = cursor.fetchall()
            return [get_bundle_by_id(b["BundleID"]) for b in bundle_ids]
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def update_bundle(bundle_id: int, bundle_data: BundleUpdateRequest) -> str:
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            
            # Update BundleMaster
            update_fields = []
            params = []
            if bundle_data.bundle_name is not None:
                update_fields.append("BundleName = %s")
                params.append(bundle_data.bundle_name)
            if bundle_data.bundle_description is not None:
                update_fields.append("BundleDescription = %s")
                params.append(bundle_data.bundle_description)
            if bundle_data.bundle_price is not None:
                update_fields.append("ActualBundlePrice = %s")
                params.append(bundle_data.bundle_price)
            if bundle_data.bundle_discount_price is not None:
                update_fields.append("DiscountBundlePrice = %s")
                params.append(bundle_data.bundle_discount_price)
            if bundle_data.is_active is not None:
                update_fields.append("IsActive = %s")
                params.append(bundle_data.is_active)
            if bundle_data.email_subject is not None:
                update_fields.append("EmailSubject = %s")
                params.append(bundle_data.email_subject)
            if bundle_data.email_body is not None:
                update_fields.append("EmailBody = %s")
                params.append(bundle_data.email_body)
            
            if update_fields:
                query = f"UPDATE BundleMaster SET {', '.join(update_fields)}, UpdatedOn = NOW() WHERE BundleID = %s"
                params.append(bundle_id)
                cursor.execute(query, tuple(params))
            
            # Update Product Mapping if provided
            if bundle_data.product_ids is not None:
                cursor.execute("DELETE FROM BundleMapping WHERE BundleID = %s", (bundle_id,))
                query_mapping = "INSERT INTO BundleMapping (BundleID, ProductID) VALUES (%s, %s)"
                for product_id in bundle_data.product_ids:
                    cursor.execute(query_mapping, (bundle_id, product_id))
            
            connection.commit()
            return "Bundle updated successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")

def delete_bundle(bundle_id: int) -> str:
    connection = get_db_connection()
    cursor = None
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM BundleMaster WHERE BundleID = %s", (bundle_id,))
            connection.commit()
            return "Bundle deleted successfully"
        except mysql.connector.Error as err:
            raise Exception(f"Database error: {err}")
        finally:
            if cursor: cursor.close()
            connection.close()
    else:
        raise Exception("Failed to connect to the database.")
