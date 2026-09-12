import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='', database='cbs_kyc')
cursor = conn.cursor(dictionary=True)

# Voir distribution des adresses
cursor.execute("SELECT adresse FROM clients ORDER BY client_id LIMIT 20")
for r in cursor.fetchall():
    print(repr(r['adresse']))

print('\n--- Clients avec adresses courtes (type ville française) ---')
cursor.execute("SELECT client_id, nom, adresse FROM clients WHERE LENGTH(adresse) < 25 LIMIT 15")
for r in cursor.fetchall():
    print(r)

conn.close()
