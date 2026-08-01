import mysql.connector
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'cbs_kyc',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clients 
        (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, pays, 
         date_creation, date_derniere_revue, date_prochaine_revue, niveau_risque, statut_kyc)
        VALUES 
        ('FC-5002', '07654321', 'SAAD', 'MOHAMED ALI', 'سعد', 'محمد علي',
         'TUNIS', 'saad.mohamedali@test.com', 1756.178, 'Tunisie',
         '2021-03-15', '2026-03-15', '2027-03-15', 'Faible', 'Normal')
    """)
    conn.commit()
    print("Client insere avec succes !")

    cursor.execute("SELECT client_id, cin, nom, prenom, nom_ar, prenom_ar, salaire FROM clients WHERE cin = '07654321'")
    row = cursor.fetchone()
    print(f"Verifie dans la base :")
    print(f"  ID       : {row[0]}")
    print(f"  CIN      : {row[1]}")
    print(f"  Nom      : {row[2]} ({row[4]})")
    print(f"  Prenom   : {row[3]} ({row[5]})")
    print(f"  Salaire  : {row[6]}")
    conn.close()
except Exception as e:
    print(f"Erreur : {e}")
