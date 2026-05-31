import sys
import os
sys.path.append('d:/Apps/CourseAPI')
import mysql.connector
from Utils.AES import AESCipher

conn=mysql.connector.connect(host='localhost',user='root',password='Tosh#140695',database='VidyaRoop')
cur=conn.cursor(dictionary=True)
cur.execute("SELECT password FROM Users WHERE email = 'bennyunsigned@gmail.com';")
row = cur.fetchone()
if row:
    cipher = AESCipher()
    try:
        dec = cipher.decrypt(row['password'])
        print(f"Decrypted password is: {dec}")
    except Exception as e:
        print(f"Decryption failed: {e}")
cur.close()
conn.close()
