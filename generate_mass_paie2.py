import os
import random
import datetime
import mysql.connector
from PIL import Image, ImageDraw, ImageFont
from faker import Faker
from tunisian_faker_provider import get_tunisian_faker

# Initialisation Faker
fake_tn = get_tunisian_faker()   # Données tunisiennes réalistes
fake_ar = Faker('ar_AA')         # Données arabes pour nom_ar/prenom_ar

TEMPLATE_PATH = r"D:\PFE\data\templates\template_paie2.jpg"
OUTPUT_DIR = r"D:\PFE\dataset_synthetique_masse"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Polices d'écriture validées
try:
    font_text = ImageFont.truetype("arial.ttf", 14)
    font_bold = ImageFont.truetype("arialbd.ttf", 16)
except:
    font_text = ImageFont.load_default()
    font_bold = ImageFont.load_default()

def get_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='cbs_kyc'
    )

def generate_existing_clients_paie(num_images=300):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Prendre 300 clients existants au hasard (ou les 300 premiers)
    cursor.execute("SELECT * FROM clients LIMIT %s", (num_images,))
    clients = cursor.fetchall()
    
    if not clients:
        print("Aucun client existant trouve.")
    else:
        print(f"Generation de {len(clients)} fiches de paie (Template 2) pour les clients existants...")
        
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")
    
    for i, client in enumerate(clients):
        # On utilise le nom et le prénom qui existent déjà dans la base
        nom_fr = client['nom']
        prenom_fr = client['prenom']
        
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        full_name = f"{nom_fr} {prenom_fr}"
        salaire_str = f"{float(client['salaire']):.3f}"
        
        # Coordonnées validées pour paie2
        draw.text((280, 118), full_name, fill="black", font=font_text)
        draw.text((579, 492), salaire_str, fill="black", font=font_bold)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"paie2_mass_exist_{i}.jpg"), quality=85)
        
    conn.commit()
    conn.close()

def generate_new_clients_paie(num_images=300):
    conn = get_db()
    cursor = conn.cursor()
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")
    
    print(f"Generation de {num_images} fiches de paie (Template 2) pour de NOUVEAUX clients...")
    
    for i in range(num_images):
        nom_fr = fake_tn.tunisian_last_name()
        prenom_fr = fake_tn.tunisian_first_name()
        nom_ar = fake_ar.last_name()
        prenom_ar = fake_ar.first_name()
        
        cin_num = f"{random.randint(0, 99):02d}{random.randint(100000, 999999)}"
        client_id = f"CL{random.randint(10000000, 99999999)}"
        email = fake_tn.tunisian_email(nom_fr, prenom_fr)
        salaire = round(random.uniform(800, 3500), 3)
        adresse = fake_tn.tunisian_address()
        niveau_risque = random.choices(["Faible", "Moyen", "Elevé"], weights=[70, 20, 10])[0]
        
        cursor.execute("""
            INSERT INTO clients 
            (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, statut_kyc, date_creation, date_derniere_revue, date_prochaine_revue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (client_id, cin_num, nom_fr, prenom_fr, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, "Normal", datetime.date.today(), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=365*5)))
        
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        full_name = f"{nom_fr} {prenom_fr}"
        salaire_str = f"{salaire:.3f}"
        
        draw.text((280, 118), full_name, fill="black", font=font_text)
        draw.text((579, 492), salaire_str, fill="black", font=font_bold)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"paie2_mass_new_{i}.jpg"), quality=85)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("====================================================")
    print("LANCEMENT DE LA GENERATION (600 Fiches de Paie Type 2)")
    print("====================================================")
    
    try:
        generate_existing_clients_paie(300)
        generate_new_clients_paie(300)
        print("\nTERMINE ! 600 fiches de paie ont ete generees dans D:\\PFE\\dataset_synthetique_masse")
    except Exception as e:
        print(f"\nERREUR : {str(e)}\nAssurez-vous que XAMPP (MySQL) est allume !")
