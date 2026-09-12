import mysql.connector, hashlib

def h(p):
    return hashlib.sha256(p.encode()).hexdigest()

conn = mysql.connector.connect(
    host="localhost", user="root", password="",
    database="cbs_kyc", charset="utf8mb4"
)
cursor = conn.cursor()

create_sql = (
    "CREATE TABLE IF NOT EXISTS agents ("
    "agent_id INT AUTO_INCREMENT PRIMARY KEY,"
    "username VARCHAR(50) UNIQUE NOT NULL,"
    "password_hash VARCHAR(255) NOT NULL,"
    "nom_complet VARCHAR(100) NOT NULL,"
    "role ENUM('agent','superviseur') DEFAULT 'agent',"
    "actif TINYINT(1) DEFAULT 1,"
    "date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    ")"
)
cursor.execute(create_sql)

agents = [
    ("admin",   h("admin123"),  "Administrateur Systeme", "superviseur"),
    ("b.hassan",h("kyc2025"),   "Bahae Hassan",           "superviseur"),
    ("agent1",  h("agent123"),  "Agent Back-Office 1",    "agent"),
    ("agent2",  h("agent123"),  "Agent Back-Office 2",    "agent"),
]
for a in agents:
    try:
        cursor.execute(
            "INSERT INTO agents (username, password_hash, nom_complet, role) VALUES (%s,%s,%s,%s)", a
        )
        print(f"  Compte cree : {a[0]} ({a[3]})")
    except Exception as e:
        print(f"  Compte deja existant ou erreur : {a[0]} -> {e}")

conn.commit()
conn.close()
print("Termine.")
