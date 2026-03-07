from DB.db import get_db_connection
import json

def diag():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    with open("diag_output.txt", "w") as f:
        f.write("--- PAYMENT TABLE COLUMNS ---\n")
        cur.execute("DESCRIBE Payment")
        cols = cur.fetchall()
        for col in cols:
            f.write(f"{col['Field']} | {col['Type']}\n")
            
        f.write("\n--- RECENT PAYMENTS ---\n")
        cur.execute("SELECT * FROM Payment ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        for r in rows:
            f.write(str(r) + "\n")
            
        f.write("\n--- RECENT LOGS ---\n")
        cur.execute("SELECT * FROM PaymentLog ORDER BY id DESC LIMIT 20")
        logs = cur.fetchall()
        for l in logs:
            f.write(f"{l['id']} | {l['payment_id']} | {l['step']} | {l['message']}\n")
            
        f.write("\n--- RECENT EMAILS ---\n")
        cur.execute("SELECT * FROM EmailMaster ORDER BY EmailId DESC LIMIT 5")
        emails = cur.fetchall()
        for e in emails:
            f.write(str(e) + "\n")
            
    cur.close()
    conn.close()
    print("Done. Check diag_output.txt")

if __name__ == "__main__":
    diag()
