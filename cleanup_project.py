import os
import shutil

root_dir = r"d:\Apps\CourseAPI"
files_to_remove = [
    "apply_bundle_schema.py", "check_payment_logs.py", "check_products_db.py", 
    "check_users_schema.py", "debug_counts.py", "debug_email_queue.py", 
    "debug_payment_log.py", "debug_simple.py", "diag_db.py", 
    "diag_db_state.py", "diag_payment.py", "diag_payment_fix.py", 
    "force_migrate.py", "installation.py", "migrate_email_config.py", 
    "repair_db.py", "row_count.py", "run_specific_migrations.py", 
    "ttv.py", "verify_attachments.py", "verify_cleanup_impl.py", 
    "verify_db_fix.py", "verify_purchase_flow.py", "verify_refined_emails.py"
]

dirs_to_remove = [
    "InstaDownload", "Cookies", "reels", "reels_downloads", "temp_videos",
    os.path.join("Controllers", "CourseDetailsCreationsAutomation.py")
]

print("Starting cleanup...")

for file in files_to_remove:
    path = os.path.join(root_dir, file)
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"Removed file: {file}")
        except Exception as e:
            print(f"Error removing file {file}: {e}")

for directory in dirs_to_remove:
    path = os.path.join(root_dir, directory)
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"Removed directory: {directory}")
        except Exception as e:
            print(f"Error removing directory {directory}: {e}")

print("Cleanup script finished.")
