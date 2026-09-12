import os
from PIL import Image, ImageDraw, ImageFont

TEMPLATE_PATH = r"D:\PFE\data\templates\template_steg.png"
OUTPUT_PATH = r"D:\PFE\data\test_steg_calibration.png"

try:
    font_name = ImageFont.truetype("arial.ttf", 15)
    font_ref  = ImageFont.truetype("arialbd.ttf", 12)
    font_addr = ImageFont.truetype("arial.ttf", 11)
except:
    font_name = ImageFont.load_default()
    font_ref  = ImageFont.load_default()
    font_addr = ImageFont.load_default()

def calibrate():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Erreur : Le fichier {TEMPLATE_PATH} est introuvable.")
        return

    img = Image.open(TEMPLATE_PATH).convert("RGBA")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    print(f"Taille de l'image : {w} x {h} pixels")

    # Textes de test - format exact comme la vraie facture STEG
    # Nom + Adresse sur la même ligne (ou 2 lignes si trop long)
    nom_test     = "MR BEN ALI MOHAMED"
    adresse_test = "7 RUE DE LA LIBERTE, TUNIS"
    
    ligne1 = f"{nom_test} , {adresse_test}"

    # Zone entre référence et CONSOMMATION & SERVICES, décalée à droite et en bas
    x, y = 80, 262

    draw.rectangle([x, y, x+400, y+16], outline="red", width=1)
    draw.text((x, y), ligne1, fill="blue", font=font_name)

    img.convert("RGB").save(OUTPUT_PATH, quality=90)
    print(f"Image de calibration generee : {OUTPUT_PATH}")

if __name__ == "__main__":
    calibrate()
