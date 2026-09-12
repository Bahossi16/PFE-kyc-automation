import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from faker import Faker

# Initialisation de Faker pour générer des noms/adresses tunisiens francisés et en arabe
fake = Faker('fr_FR')
fake_ar = Faker('ar_AA')

# Les dossiers d'entrée et de sortie
INPUT_DIR = r"D:\PFE\images_test"
OUTPUT_DIR = r"D:\PFE\dataset_synthetique"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Polices d'écriture
FONT_PATH = "arial.ttf"
FONT_BOLD_PATH = "arialbd.ttf"

def load_font(path, size, default_size=16):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def generate_steg(num_images=10):
    template_path = os.path.join(INPUT_DIR, "template_steg.png")
    if not os.path.exists(template_path):
        print(f"[Attention] Image introuvable : {template_path}")
        return
        
    base_img = Image.open(template_path).convert("RGBA")
    font_name = load_font(FONT_BOLD_PATH, 16)
    font_address = load_font(FONT_PATH, 14)

    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        full_name = f"MR {fake.last_name().upper()} {fake.first_name().upper()}"
        address = fake.street_address().upper() + ", " + fake.city().upper()
        
        # Effacer l'ancien nom et adresse (R MARÉCHAL ALFRED, etc.)
        draw.rectangle([0, 200, 350, 260], fill=(255, 255, 255))
        
        # Écrire le nouveau nom et adresse à l'emplacement exact
        x_text, y_text = 10, 204
        
        draw.text((x_text, y_text), full_name, fill=(20, 50, 100), font=font_name)
        draw.text((x_text, y_text + 30), address, fill=(20, 50, 100), font=font_address)
        
        angle = random.uniform(-1.5, 1.5)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255,255,255))
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"steg_synth_{i}.jpg"), quality=85)
    print(f"[OK] Genere : {num_images} factures STEG")

def generate_paie(template_name, paie_type, num_images=10):
    template_path = os.path.join(INPUT_DIR, template_name)
    if not os.path.exists(template_path):
        print(f"[Attention] Image introuvable : {template_path}")
        return
        
    base_img = Image.open(template_path).convert("RGBA")
    font_text = load_font(FONT_PATH, 14)
    font_bold = load_font(FONT_BOLD_PATH, 16)

    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        full_name = f"{fake.last_name().upper()} {fake.first_name().upper()}"
        salary = f"{random.uniform(800, 3500):.3f}" 
        
        if paie_type == 1:
            # Paie 1 (froissé Technique Transit) :
            # NOM ET PRENOM: y=110, x=497 → écrire nom à x=497, y=163 (ligne données)
            # SAL.NET: header y=746, x=754 → valeur y=815, x=754 (mais image 1190px large)
            x_name, y_name = 497, 163
            x_salary, y_salary = 760, 815
        else:
            # Paie 2 (RR2020 tableau propre) :
            # NOM & PRENOM: header y=90, x=280 → valeur y=110 (ligne sous header, dans la cellule)
            # SAL.NET: header y=493, x=609 → valeur y=512, x=609
            x_name, y_name = 280, 110
            x_salary, y_salary = 609, 512
        
        draw.text((x_name, y_name), full_name, fill=(0, 0, 0), font=font_text)
        draw.text((x_salary, y_salary), salary, fill=(0, 0, 0), font=font_bold)
        
        if random.random() > 0.5:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
            
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"paie{paie_type}_synth_{i}.jpg"), quality=85)
    print(f"[OK] Genere : {num_images} Fiches de paie (Modele {paie_type})")

def generate_cin(num_images=10):
    template_path = os.path.join(INPUT_DIR, "template_cin.png")
    if not os.path.exists(template_path):
        print(f"[Attention] Image introuvable : {template_path}")
        return
        
    base_img = Image.open(template_path).convert("RGBA")
    font_id = load_font(FONT_BOLD_PATH, 22) 
    font_name = load_font(FONT_BOLD_PATH, 18)

    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([320, 140, 480, 175], fill=(240, 238, 235)) 
        
        id_num = f"{random.randint(0, 99):02d}{random.randint(100000, 999999)}"
        last_name = fake.last_name().upper()
        first_name = fake.first_name().upper()
        
        draw.text((330, 145), id_num, fill=(20, 20, 20), font=font_id)
        draw.text((240, 180), last_name, fill=(20, 20, 20), font=font_name)
        draw.text((240, 220), first_name, fill=(20, 20, 20), font=font_name)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"cin_synth_{i}.jpg"), quality=85)
    print(f"[OK] Genere : {num_images} cartes CIN")

def generate_cin_ar(num_images=10):
    template_path = os.path.join(r"D:\PFE\doss_cin", "test_cin_arabic.png")
    if not os.path.exists(template_path):
        print(f"[Attention] Image introuvable : {template_path}")
        return
        
    base_img = Image.open(template_path).convert("RGBA")
    font_id = load_font(FONT_BOLD_PATH, 22) 
    # Pour l'arabe, utiliser une police qui supporte l'arabe si possible (Arial supporte l'arabe sous Windows)
    font_name = load_font("arial.ttf", 20)

    for i in range(num_images):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        # Rectangle pour cacher les anciens noms (x_min, y_min, x_max, y_max)
        # Estimation : le texte "السهول" et "ميار" se trouve à gauche des labels "اللقب" et "الاسم"
        draw.rectangle([350, 160, 520, 230], fill=(240, 238, 235)) 
        
        # ID number
        id_num = f"{random.randint(0, 99):02d}{random.randint(100000, 999999)}"
        draw.text((330, 145), id_num, fill=(20, 20, 20), font=font_id)
        
        # Générer des noms arabes
        last_name = fake_ar.last_name()
        first_name = fake_ar.first_name()
        
        # Comme PIL ne gère pas bien le RTL par défaut (sans libraqm),
        # il vaut mieux écrire tel quel. Sur des mots isolés, cela peut passer si Arial RTL.
        # Ou on peut utiliser un package comme arabic_reshaper, mais on va écrire directement pour tester
        import bidi.algorithm
        import arabic_reshaper
        try:
            last_name = bidi.algorithm.get_display(arabic_reshaper.reshape(last_name))
            first_name = bidi.algorithm.get_display(arabic_reshaper.reshape(first_name))
        except:
            pass # Si les libs ne sont pas dispo, écrire tel quel
        
        # Dessiner le nom et le prénom
        draw.text((450, 160), last_name, fill=(20, 20, 20), font=font_name)
        draw.text((450, 195), first_name, fill=(20, 20, 20), font=font_name)
        
        img.convert("RGB").save(os.path.join(OUTPUT_DIR, f"cin_ar_synth_{i}.jpg"), quality=85)
    print(f"[OK] Genere : {num_images} cartes CIN en arabe")

if __name__ == "__main__":
    print("\n[Start] Demarrage de la generation de donnees synthetiques...")
    
    generate_steg(num_images=20)
    generate_paie("template_paie1.jpg", paie_type=1, num_images=10) 
    generate_paie("template_paie2.jpg", paie_type=2, num_images=10) 
    generate_cin(num_images=20)
    generate_cin_ar(num_images=10)
    
    print("\n[Fin] Termine ! Les documents ont ete crees dans D:\\PFE\\dataset_synthetique.")
