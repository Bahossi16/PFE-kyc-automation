import os
import random
import datetime
import mysql.connector
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from faker import Faker

# Initialisation
fake = Faker('fr_FR')
fake_ar = Faker('ar_AA')

INPUT_DIR = r"D:\PFE\data\templates"
CIN_AR_DIR = r"D:\PFE\doss_cin"
OUTPUT_DIR = r"D:\PFE\dataset_synthetique_masse"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_PATH = "arial.ttf"
FONT_BOLD_PATH = "arialbd.ttf"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

# -------------------------------------------------------------------
# CONNEXION MYSQL (Pour que les documents générés existent dans le CBS)
# -------------------------------------------------------------------
def get_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='cbs_kyc'
    )

def insert_client_to_db(cin, nom, prenom, adresse, salaire, nom_ar="", prenom_ar=""):
    conn = get_db()
    cursor = conn.cursor()
    
    # Choisir un niveau de risque aléatoire
    niveau_risque = random.choices(["Faible", "Moyen", "Elevé"], weights=[70, 20, 10])[0]
    
    client_id = f"CL{random.randint(10000000, 99999999)}"
    email = f"{prenom.lower()}.{nom.lower()}@exemple.tn"
    
    cursor.execute("""
        INSERT INTO clients 
        (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, statut_kyc, date_creation, date_derniere_revue, date_prochaine_revue)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, niveau_risque, "Normal", datetime.date.today(), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=365*5)))
    
    conn.commit()
    conn.close()

# -------------------------------------------------------------------
# GENERATEURS D'IMAGES
# -------------------------------------------------------------------
def generate_mass_cin(num_images=300):
    template_path = os.path.join(INPUT_DIR, "template_cin_arabic.png")
    if not os.path.exists(template_path):
        return print(f"Template manquant: {template_path}")
        
    base_img = Image.open(template_path).convert("RGBA")
    font_id = load_font(FONT_BOLD_PATH, 22) 
    font_name = load_font("arial.ttf", 20)

    print(f"Generation de {num_images} CIN Arabes en cours...")
    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([350, 160, 520, 230], fill=(240, 238, 235)) 
        
        cin_num = f"{random.randint(0, 99):02d}{random.randint(100000, 999999)}"
        last_name_ar = fake_ar.last_name()
        first_name_ar = fake_ar.first_name()
        
        draw.text((330, 145), cin_num, fill=(20, 20, 20), font=font_id)
        
        import bidi.algorithm
        import arabic_reshaper
        try:
            ln_display = bidi.algorithm.get_display(arabic_reshaper.reshape(last_name_ar))
            fn_display = bidi.algorithm.get_display(arabic_reshaper.reshape(first_name_ar))
        except:
            ln_display = last_name_ar
            fn_display = first_name_ar
            
        draw.text((450, 160), ln_display, fill=(20, 20, 20), font=font_name)
        draw.text((450, 195), fn_display, fill=(20, 20, 20), font=font_name)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"cin_mass_{i}.jpg"), quality=85)
        
        # Inserer dans la DB
        insert_client_to_db(cin_num, "INCONNU", "INCONNU", "ADRESSE INCONNUE", 1000.0, nom_ar=last_name_ar, prenom_ar=first_name_ar)

def generate_mass_steg(num_images=300):
    template_path = os.path.join(INPUT_DIR, "template_steg.png")
    if not os.path.exists(template_path):
        return print(f"Template manquant: {template_path}")
        
    base_img = Image.open(template_path).convert("RGBA")
    font_name = load_font(FONT_BOLD_PATH, 16)
    font_address = load_font(FONT_PATH, 14)

    print(f"Génération de {num_images} Factures STEG en cours...")
    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        cin_num = f"99{random.randint(100000, 999999)}"
        nom = fake.last_name().upper()
        prenom = fake.first_name().upper()
        full_name = f"MR {nom} {prenom}"
        adresse = fake.street_address().upper() + ", " + fake.city().upper()
        
        draw.rectangle([0, 200, 350, 260], fill=(255, 255, 255))
        draw.text((10, 204), full_name, fill=(20, 50, 100), font=font_name)
        draw.text((10, 234), adresse, fill=(20, 50, 100), font=font_address)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"steg_mass_{i}.jpg"), quality=85)
        insert_client_to_db(cin_num, nom, prenom, adresse, 1500.0)

def generate_mass_paie(num_images=300):
    template_path = os.path.join(INPUT_DIR, "template_paie1.jpg")
    if not os.path.exists(template_path):
        return print(f"Template manquant: {template_path}")
        
    base_img = Image.open(template_path).convert("RGBA")
    font_text = load_font(FONT_PATH, 14)
    font_bold = load_font(FONT_BOLD_PATH, 16)

    print(f"Génération de {num_images} Fiches de paie en cours...")
    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        cin_num = f"88{random.randint(100000, 999999)}"
        nom = fake.last_name().upper()
        prenom = fake.first_name().upper()
        full_name = f"{nom} {prenom}"
        salaire = random.uniform(800, 3500)
        salaire_str = f"{salaire:.3f}" 
        
        draw.text((497, 163), full_name, fill=(0, 0, 0), font=font_text)
        draw.text((760, 815), salaire_str, fill=(0, 0, 0), font=font_bold)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"paie_mass_{i}.jpg"), quality=85)
        insert_client_to_db(cin_num, nom, prenom, "TUNIS", salaire)

if __name__ == "__main__":
    print("====================================================")
    print("LANCEMENT DE LA GENERATION DE MASSE (300 docs CIN)")
    print("====================================================")
    
    try:
        generate_mass_cin(300)
        # generate_mass_steg(300)
        # generate_mass_paie(300)
        print("\nTERMINE ! Les 300 images CIN sont dans D:\\PFE\\dataset_synthetique_masse")
        print("Les 300 clients ont ete inseres dans la base MySQL cbs_kyc.")
    except Exception as e:
        print(f"\nERREUR : {str(e)}\nAssurez-vous que XAMPP (MySQL) est allume !")
