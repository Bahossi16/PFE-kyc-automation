import os
from PIL import Image, ImageDraw, ImageFont

TEMPLATE_PATH = r"D:\PFE\data\templates\template_paie2.jpg"
OUTPUT_PATH = r"D:\PFE\data\test_paie2_calibration.png"

# Essayer de charger Arial, sinon police par défaut
try:
    font_text = ImageFont.truetype("arial.ttf", 14) # Un peu plus petit (14 au lieu de 16)
    font_bold = ImageFont.truetype("arialbd.ttf", 16) # Un peu plus petit (16 au lieu de 18)
except:
    font_text = ImageFont.load_default()
    font_bold = ImageFont.load_default()

def calibrate():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Erreur : Le fichier {TEMPLATE_PATH} est introuvable.")
        return

    img = Image.open(TEMPLATE_PATH).convert("RGBA")
    draw = ImageDraw.Draw(img)
    # Coordonnées ajustées
    # Nom validé
    x_name, y_name = 280, 118
    # Salaire un peu plus à gauche
    x_salary, y_salary = 579, 492
    
    texte_nom = "BEN ALI MOHAMED"
    texte_salaire = "1250.500"
    
    # Dessiner un rectangle rouge autour pour bien repérer la zone
    draw.rectangle([x_name, y_name, x_name+200, y_name+20], outline="red", width=2)
    draw.text((x_name + 5, y_name + 2), texte_nom, fill="blue", font=font_text)
    
    draw.rectangle([x_salary, y_salary, x_salary+100, y_salary+20], outline="red", width=2)
    draw.text((x_salary + 5, y_salary + 2), texte_salaire, fill="blue", font=font_bold)
    
    img.convert("RGB").save(OUTPUT_PATH, quality=90)
    print(f"Image de calibration générée avec succès : {OUTPUT_PATH}")

if __name__ == "__main__":
    calibrate()
