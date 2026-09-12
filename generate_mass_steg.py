import os
import random
import datetime
import mysql.connector
from PIL import Image, ImageDraw, ImageFont
from faker import Faker
from tunisian_faker_provider import get_tunisian_faker

fake_tn = get_tunisian_faker()   # Données tunisiennes réalistes
fake_ar = Faker('ar_AA')

TEMPLATE_PATH = r"D:\PFE\data\templates\template_steg.png"
OUTPUT_DIR = r"D:\PFE\dataset_synthetique_masse"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Coordonnées et polices validées
try:
    font_name = ImageFont.truetype("arial.ttf", 15)
except:
    font_name = ImageFont.load_default()

X, Y = 80, 262

def get_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='cbs_kyc'
    )

def generate_existing_clients_steg(num_images=300):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients LIMIT %s", (num_images,))
    clients = cursor.fetchall()
    conn.close()

    if not clients:
        print("Aucun client existant trouve.")
        return

    print(f"Generation de {len(clients)} factures STEG pour les clients existants...")
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")

    for i, client in enumerate(clients):
        nom    = client['nom']
        prenom = client['prenom']
        adresse = client.get('adresse', 'TUNIS')

        img  = base_img.copy()
        draw = ImageDraw.Draw(img)

        ligne = f"MR {nom} {prenom} , {adresse}"
        draw.text((X, Y), ligne, fill="black", font=font_name)

        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"steg_mass_exist_{i}.jpg"), quality=85)

    print(f"  --> {len(clients)} factures STEG (clients existants) generees.")

def generate_new_clients_steg(num_images=300):
    conn = get_db()
    cursor = conn.cursor()
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")

    print(f"Generation de {num_images} factures STEG pour de NOUVEAUX clients...")

    for i in range(num_images):
        nom_fr   = fake_tn.tunisian_last_name()
        prenom_fr = fake_tn.tunisian_first_name()
        nom_ar   = fake_ar.last_name()
        prenom_ar = fake_ar.first_name()
        adresse  = fake_tn.tunisian_address_steg()  # Format court pour STEG

        cin_num   = f"{random.randint(0, 99):02d}{random.randint(100000, 999999)}"
        client_id = f"CL{random.randint(10000000, 99999999)}"
        email     = fake_tn.tunisian_email(nom_fr, prenom_fr)
        salaire   = round(random.uniform(800, 3500), 3)
        niveau_risque = random.choices(["Faible", "Moyen", "Elevé"], weights=[70, 20, 10])[0]

        cursor.execute("""
            INSERT INTO clients
            (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, statut_kyc, date_creation, date_derniere_revue, date_prochaine_revue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (client_id, cin_num, nom_fr, prenom_fr, nom_ar, prenom_ar, adresse, email, salaire,
              niveau_risque, "Normal",
              datetime.date.today(), datetime.date.today(),
              datetime.date.today() + datetime.timedelta(days=365*5)))

        img  = base_img.copy()
        draw = ImageDraw.Draw(img)

        ligne = f"MR {nom_fr} {prenom_fr} , {adresse}"
        draw.text((X, Y), ligne, fill="black", font=font_name)

        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"steg_mass_new_{i}.jpg"), quality=85)

    conn.commit()
    conn.close()
    print(f"  --> {num_images} factures STEG (nouveaux clients) generees.")

if __name__ == "__main__":
    print("====================================================")
    print("LANCEMENT DE LA GENERATION (600 Factures STEG)")
    print("====================================================")
    try:
        generate_existing_clients_steg(300)
        generate_new_clients_steg(300)
        print("\nTERMINE ! 600 factures STEG ont ete generees dans D:\\PFE\\dataset_synthetique_masse")
    except Exception as e:
        print(f"\nERREUR : {str(e)}\nAssurez-vous que XAMPP (MySQL) est allume !")
