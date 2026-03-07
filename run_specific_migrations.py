import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from DB.dbCreation import ensure_getCartProductsByUser_procedure_exists, create_cart_table, ensure_users_activation_column

print("Starting migrations...")
try:
    print("Ensuring Users.is_activated column...")
    ensure_users_activation_column()
    print("Creating Cart table...")
    create_cart_table()
    print("Ensuring GetCartProductsByUser procedure exists...")
    ensure_getCartProductsByUser_procedure_exists()
    print("Migrations completed successfully.")
except Exception as e:
    print(f"Error during migrations: {e}")
