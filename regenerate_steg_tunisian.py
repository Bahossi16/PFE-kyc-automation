"""
=======================================================================
  REGENERATION DES 600 FACTURES STEG - Données Tunisiennes
  Projet PFE : Automatisation KYC
  -----------------------------------------------------------------------
  Stratégie :
  1. steg_mass_exist_*  : Mettre à jour les adresses des 300 clients
                          existants vers des adresses tunisiennes réalistes,
                          puis régénérer les 300 images.
  2. steg_mass_new_*    : Créer 300 NOUVEAUX clients avec adresses tunisiennes
                          et régénérer les 300 images (les anciens clients
                          avec adresses françaises restent en base mais ne
                          sont plus référencés par aucune image).
=======================================================================
"""
import os
import random
import datetime
import mysql.connector
from PIL import Image, ImageDraw, ImageFont
from faker import Faker
from tunisian_faker_provider import get_tunisian_faker

fake_tn = get_tunisian_faker()
fake_ar = Faker('ar_AA')

TEMPLATE_PATH = r"D:\PFE\data\templates\template_steg.png"
OUTPUT_DIR    = r"D:\PFE\dataset_synthetique_masse"
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    font_name = ImageFont.truetype("arial.ttf", 15)
except:
    font_name = ImageFont.load_default()

X, Y = 80, 262

def get_db():
    return mysql.connector.connect(
        host='localhost', user='root', password='', database='cbs_kyc',
        charset='utf8mb4', collation='utf8mb4_unicode_ci'
    )

# -----------------------------------------------------------------------
# PARTIE 1 : Mettre à jour les 300 clients existants + régénérer images
# -----------------------------------------------------------------------
def regenerate_exist_steg(num_images=300):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients LIMIT %s", (num_images,))
    clients = cursor.fetchall()
    conn_w  = get_db()
    cursor_w = conn_w.cursor()

    print(f"[1/2] Mise a jour des adresses + regeneration de {len(clients)} factures STEG (clients existants)...")
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")

    updated  = 0
    for i, client in enumerate(clients):
        # Générer une adresse tunisienne réaliste
        new_adresse = fake_tn.tunisian_address_steg()

        # Mettre à jour l'adresse dans CBS
        cursor_w.execute(
            "UPDATE clients SET adresse = %s WHERE client_id = %s",
            (new_adresse, client['client_id'])
        )

        # Régénérer l'image STEG avec la même adresse
        nom    = client['nom']
        prenom = client['prenom']

        img  = base_img.copy()
        draw = ImageDraw.Draw(img)
        ligne = f"MR {nom} {prenom} , {new_adresse}"
        draw.text((X, Y), ligne, fill="black", font=font_name)
        img.convert("RGB").save(
            os.path.join(OUTPUT_DIR, f"steg_mass_exist_{i}.jpg"), quality=85
        )
        updated += 1
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(clients)} images regenerees...", flush=True)

    conn_w.commit()
    conn_w.close()
    conn.close()
    print(f"  --> {updated} factures STEG (exist) regenerees avec adresses tunisiennes.")

# -----------------------------------------------------------------------
# PARTIE 2 : Créer 300 nouveaux clients tunisiens + générer images
# -----------------------------------------------------------------------
def regenerate_new_steg(num_images=300):
    conn   = get_db()
    cursor = conn.cursor()

    print(f"\n[2/2] Insertion de {num_images} nouveaux clients tunisiens + generation des factures STEG...")
    base_img = Image.open(TEMPLATE_PATH).convert("RGBA")

    inserted = 0
    for i in range(num_images):
        nom_fr    = fake_tn.tunisian_last_name()
        prenom_fr = fake_tn.tunisian_first_name()
        nom_ar    = fake_ar.last_name()
        prenom_ar = fake_ar.first_name()
        adresse   = fake_tn.tunisian_address_steg()

        cin_num      = f"{random.randint(0, 19):02d}{random.randint(100000, 999999)}"
        client_id    = f"CL{random.randint(10000000, 99999999)}"
        email        = fake_tn.tunisian_email(nom_fr, prenom_fr)
        salaire      = round(random.uniform(800, 3500), 3)
        niveau_risque = random.choices(
            ["Faible", "Moyen", "Eleve"], weights=[70, 20, 10]
        )[0]

        try:
            cursor.execute("""
                INSERT INTO clients
                (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email,
                 salaire, niveau_risque, statut_kyc,
                 date_creation, date_derniere_revue, date_prochaine_revue)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                client_id, cin_num, nom_fr, prenom_fr, nom_ar, prenom_ar,
                adresse, email, salaire, niveau_risque, "Normal",
                datetime.date.today(), datetime.date.today(),
                datetime.date.today() + datetime.timedelta(days=365 * 5)
            ))
        except Exception as e:
            # En cas de doublon de client_id, régénérer un nouvel id
            client_id = f"CL{random.randint(10000000, 99999999)}"
            cursor.execute("""
                INSERT INTO clients
                (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email,
                 salaire, niveau_risque, statut_kyc,
                 date_creation, date_derniere_revue, date_prochaine_revue)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                client_id, cin_num, nom_fr, prenom_fr, nom_ar, prenom_ar,
                adresse, email, salaire, niveau_risque, "Normal",
                datetime.date.today(), datetime.date.today(),
                datetime.date.today() + datetime.timedelta(days=365 * 5)
            ))

        # Générer l'image STEG
        img  = base_img.copy()
        draw = ImageDraw.Draw(img)
        ligne = f"MR {nom_fr} {prenom_fr} , {adresse}"
        draw.text((X, Y), ligne, fill="black", font=font_name)
        img.convert("RGB").save(
            os.path.join(OUTPUT_DIR, f"steg_mass_new_{i}.jpg"), quality=85
        )
        inserted += 1
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{num_images} images generees...", flush=True)

    conn.commit()
    conn.close()
    print(f"  --> {inserted} nouveaux clients tunisiens inseres + factures STEG generees.")

# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  REGENERATION DES 600 FACTURES STEG (Donnees Tunisiennes)")
    print("=" * 60)
    try:
        regenerate_exist_steg(300)
        regenerate_new_steg(300)
        print("\nTERMINE ! 600 factures STEG regenerees avec adresses tunisiennes.")
        print("Les images sont dans : D:\\PFE\\dataset_synthetique_masse\\")
    except Exception as e:
        import traceback
        print(f"\nERREUR : {e}")
        traceback.print_exc()
