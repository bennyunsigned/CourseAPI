import mysql.connector
conn=mysql.connector.connect(host='localhost',user='root',password='Tosh#140695',database='VidyaRoop')
cur=conn.cursor(dictionary=True)
cur.execute("SELECT id, name, email, is_activated, created_at FROM Users WHERE email = 'bennyunsigned@gmail.com';")
print(cur.fetchall())
cur.close()
conn.close()
