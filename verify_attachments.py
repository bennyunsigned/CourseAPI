import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from Services.productService import create_product, get_product_by_id, save_product_attachments, get_all_products, delete_product_attachment, get_all_attachment_details
from Models.productModel import ProductRequest, ProductAttachmentRequest

def verify_attachments():
    print("Verifying Product Attachments implementation...")
    
    # 1. Create a test product
    product_data = ProductRequest(
        product_name="Test Product with Attachments",
        product_price=100.0,
        product_discount_price=80.0,
        product_description="Testing attachments functionality",
        product_content="Some content",
        product_image="test.jpg",
        is_active=True
    )
    
    try:
        new_product = create_product(product_data)
        pid = new_product.product_id
        print(f"Created test product with ID: {pid}")
        
        # 2. Add attachments
        attachments = [
            ProductAttachmentRequest(file_name="Manual", file_url="http://example.com/manual.pdf", file_type="pdf"),
            ProductAttachmentRequest(file_name="Image1", file_url="http://example.com/img1.png", file_type="png")
        ]
        
        result = save_product_attachments(pid, attachments)
        print(f"Save attachments result: {result}")
        
        # 3. Retrieve product and check attachments
        product = get_product_by_id(pid)
        print(f"Retrieved product: {product.product_name}")
        print(f"Attachments found: {len(product.attachments)}")
        
        for att in product.attachments:
            print(f" - {att.file_name}: {att.file_url}")
            
        if len(product.attachments) == 2:
            print("SUCCESS: Attachments verified.")
        else:
            print("FAILURE: Attachment count mismatch.")
            
        # 4. Test delete_product_attachment
        aid_to_delete = product.attachments[0].attachment_id
        print(f"Deleting attachment ID: {aid_to_delete}")
        del_result = delete_product_attachment(pid, aid_to_delete)
        print(f"Delete result: {del_result}")
        
        # Verify deletion
        product_after_del = get_product_by_id(pid)
        print(f"Attachments after deletion: {len(product_after_del.attachments)}")
        
        # 5. Test get_all_attachment_details
        all_atts = get_all_attachment_details()
        print(f"Total attachments in system: {len(all_atts)}")
        
        if len(product_after_del.attachments) == 1 and len(all_atts) >= 1:
            print("SUCCESS: New attachment methods verified.")
        else:
            print("FAILURE: Verification failed for new methods.")
            
    except Exception as e:
        print(f"ERROR during verification: {e}")

if __name__ == "__main__":
    verify_attachments()
