import mysql.connector

DB_CONFIG_INIT = {
    'host': 'localhost',
    'user': 'root',
    'password': ''
}

def reset_db():
    conn = mysql.connector.connect(**DB_CONFIG_INIT)
    cursor = conn.cursor()
    
    with open('init_cbs_db.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
        
    # Exécuter les commandes séparées par des points-virgules
    commands = [c.strip() for c in sql.split(';') if c.strip()]
    for cmd in commands:
        try:
            cursor.execute(cmd)
        except Exception as e:
            print(f"Erreur sur la commande: {cmd[:50]}... => {e}")
            
    conn.commit()
    conn.close()
    print("Base de données réinitialisée avec succès !")

if __name__ == '__main__':
    reset_db()
