import sys
import traceback

def log(msg):
    try:
        with open("payment_debug_out.txt", "a") as f:
            f.write(msg + "\n")
    except:
        pass

if __name__ == "__main__":
    # Clear file
    with open("payment_debug_out.txt", "w") as f:
        f.write("Starting script...\n")
    
    try:
        log("Importing DB...")
        from DB.db import get_db_connection
        log("Import success.")
        
        log("Connecting to DB...")
        conn = get_db_connection()
        if not conn:
            log("Connection failed (return None).")
        else:
            log("Connected. Fetching logs...")
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM PaymentLog ORDER BY id DESC LIMIT 10")
                rows = cur.fetchall()
                log(f"Found {len(rows)} logs.")
                for r in rows:
                    log(str(r))
            except Exception as e:
                log(f"Query Error: {e}")
                log(traceback.format_exc())
            finally:
                conn.close()
                log("Connection closed.")
                
    except Exception as e:
        log(f"Top Level Error: {e}")
        log(traceback.format_exc())

