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

TEMPLATE_PATH = r"D:\PFE\data\templates\template_paie1.png"
OUTPUT_DIR = r"D:\PFE\dataset_synthetique_masse"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Polices d'écriture
try:
    font_text = ImageFont.truetype("arial.ttf", 16)
    font_bold = ImageFont.truetype("arialbd.ttf", 18)
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
    
    # Récupérer 300 clients ayant un nom "INCONNU"
    cursor.execute("SELECT * FROM clients WHERE nom = 'INCONNU' LIMIT %s", (num_images,))
    clients = cursor.fetchall()
    
    if not clients:
        print("Aucun client existant avec nom 'INCONNU' trouve.")
    else:
        print(f"Generation de {len(clients)} fiches de paie pour les clients existants...")
        
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")
    
    for i, client in enumerate(clients):
        # 1. Générer de vrais noms tunisiens pour remplacer "INCONNU"
        nom_fr = fake_tn.tunisian_last_name()
        prenom_fr = fake_tn.tunisian_first_name()
        
        # 2. Mettre à jour la base de données
        cursor.execute("UPDATE clients SET nom = %s, prenom = %s WHERE client_id = %s", 
                       (nom_fr, prenom_fr, client['client_id']))
        
        # 3. Dessiner sur l'image
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        full_name = f"{nom_fr} {prenom_fr}"
        salaire_str = f"{float(client['salaire']):.3f}"
        
        # Coordonnées validées
        draw.text((497, 185), full_name, fill="black", font=font_text)
        draw.text((760, 815), salaire_str, fill="black", font=font_bold)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"paie_mass_exist_{i}.jpg"), quality=85)
        
    conn.commit()
    conn.close()

def generate_new_clients_paie(num_images=300):
    conn = get_db()
    cursor = conn.cursor()
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")
    
    print(f"Generation de {num_images} fiches de paie pour de NOUVEAUX clients...")
    
    for i in range(num_images):
        # 1. Générer de nouveaux profils bilingues
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
        
        # 2. Insérer dans la base de données
        cursor.execute("""
            INSERT INTO clients 
            (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, statut_kyc, date_creation, date_derniere_revue, date_prochaine_revue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (client_id, cin_num, nom_fr, prenom_fr, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, "Normal", datetime.date.today(), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=365*5)))
        
        # 3. Dessiner sur l'image
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        full_name = f"{nom_fr} {prenom_fr}"
        salaire_str = f"{salaire:.3f}"
        
        # Coordonnées validées
        draw.text((497, 185), full_name, fill="black", font=font_text)
        draw.text((760, 815), salaire_str, fill="black", font=font_bold)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"paie_mass_new_{i}.jpg"), quality=85)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("====================================================")
    print("LANCEMENT DE LA GENERATION DE MASSE (600 Fiches de Paie)")
    print("====================================================")
    
    try:
        generate_existing_clients_paie(300)
        generate_new_clients_paie(300)
        print("\nTERMINE ! 600 fiches de paie ont ete generees dans D:\\PFE\\dataset_synthetique_masse")
    except Exception as e:
        print(f"\nERREUR : {str(e)}\nAssurez-vous que XAMPP (MySQL) est allume !")
