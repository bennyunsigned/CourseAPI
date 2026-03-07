import os
import mysql.connector
from dotenv import load_dotenv

def repair():
    load_dotenv()
    print("Connecting to database...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            connect_timeout=10
        )
        cur = conn.cursor()
        
        # Table BundlePayment
        print("Ensuring BundlePayment table exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS BundlePayment (
                BundlePaymentID INT AUTO_INCREMENT PRIMARY KEY,
                UserID INT NOT NULL,
                BundleID INT NOT NULL,
                Amount DECIMAL(10, 2) NOT NULL,
                PaymentID VARCHAR(255) NOT NULL,
                Status VARCHAR(50) DEFAULT 'Completed',
                PaymentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (UserID) REFERENCES Users(id) ON DELETE CASCADE,
                FOREIGN KEY (BundleID) REFERENCES BundleMaster(BundleID) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # Table ProductPayment
        print("Ensuring ProductPayment table exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ProductPayment (
                ProductPaymentID INT AUTO_INCREMENT PRIMARY KEY,
                UserID INT NOT NULL,
                ProductID INT NOT NULL,
                Amount DECIMAL(10, 2) NOT NULL,
                PaymentID VARCHAR(255) NOT NULL,
                Status VARCHAR(50) DEFAULT 'Completed',
                PaymentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (UserID) REFERENCES Users(id) ON DELETE CASCADE,
                FOREIGN KEY (ProductID) REFERENCES ProductMaster(ProductID) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        conn.commit()
        print("All tables ensured to exist.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Repair failed: {e}")

if __name__ == "__main__":
    repair()
