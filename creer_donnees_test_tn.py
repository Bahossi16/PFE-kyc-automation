import os
from PIL import Image, ImageDraw, ImageFont

def creer_mock_cin_tunisienne(output_path):
    # Créer un fond de carte (style CIN tunisienne)
    # Dimensions : 850 x 540 (ratio standard carte bancaire / ID)
    width, height = 850, 540
    image = Image.new('RGB', (width, height), color=(245, 247, 250))
    draw = ImageDraw.Draw(image)

    # Essayer de charger une police système Windows standard
    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_header = ImageFont.truetype("arial.ttf", 24)
        font_body = ImageFont.truetype("arial.ttf", 22)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
    except IOError:
        # Fallback si arial n'est pas accessible
        font_title = font_header = font_body = font_bold = ImageFont.load_default()

    # Dessiner des éléments graphiques (cadre, décoration)
    draw.rectangle([15, 15, width-15, height-15], outline=(180, 200, 220), width=3)
    draw.rectangle([20, 20, width-20, 90], fill=(225, 235, 245))
    
    # En-tête
    draw.text((width // 2, 35), "REPUBLIQUE TUNISIENNE", fill=(160, 40, 45), font=font_title, anchor="mm")
    draw.text((width // 2, 70), "CARTE D'IDENTITE NATIONALE", fill=(30, 60, 100), font=font_header, anchor="mm")

    # Données textuelles de la CIN (Mohamed Trabelsi)
    labels_and_values = [
        ("Nom :", "TRABELSI", 140),
        ("Prenom :", "Mohamed", 190),
        ("Date de naissance :", "20.10.1985", 240),
        ("Lieu de naissance :", "Tunis", 290),
        ("Adresse :", "15 Rue de la Liberte, Tunis", 340),
        ("N° CIN :", "12345678", 390)
    ]

    for label, val, y in labels_and_values:
        # Label en gras / gris foncé
        draw.text((80, y), label, fill=(70, 80, 95), font=font_body)
        # Valeur en bleu foncé / noir
        draw.text((320, y), val, fill=(20, 30, 50), font=font_bold)

    # Pied de page simulé
    draw.text((width // 2, 480), "Delivree le 10.05.2019  -  Signature de l'Autorite", fill=(100, 110, 120), font=font_body, anchor="mm")

    # Créer le répertoire de destination s'il n'existe pas
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
    print(f"[OK] Mock CIN Tunisienne cree avec succes : {output_path}")

def creer_mock_facture_steg(output_path):
    # Dimensions : 800 x 1000 (format vertical type facture A4)
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 32)
        font_header = ImageFont.truetype("arialbd.ttf", 22)
        font_body = ImageFont.truetype("arial.ttf", 18)
        font_bold = ImageFont.truetype("arialbd.ttf", 18)
    except IOError:
        font_title = font_header = font_body = font_bold = ImageFont.load_default()

    # En-tête de la facture STEG
    draw.rectangle([20, 20, width-20, 110], fill=(240, 248, 255), outline=(100, 149, 237), width=2)
    draw.text((40, 45), "STEG", fill=(0, 70, 150), font=font_title)
    draw.text((40, 80), "Societe Tunisienne de l'Electricite et du Gaz", fill=(70, 80, 95), font=font_body)

    # Titre de la facture
    draw.text((width // 2, 160), "FACTURE D'ELECTRICITE ET DE GAZ", fill=(0, 0, 0), font=font_header, anchor="mm")
    draw.line([150, 180, width-150, 180], fill=(200, 200, 200), width=1)

    # Bloc informations client
    draw.rectangle([40, 220, width-40, 360], fill=(250, 250, 250), outline=(220, 220, 220), width=1)
    draw.text((60, 240), "COORDONNEES DE L'ABONNE", fill=(0, 70, 150), font=font_header)
    
    draw.text((60, 280), "Nom et Prenom :", fill=(80, 80, 80), font=font_body)
    draw.text((220, 280), "MOHAMED TRABELSI", fill=(0, 0, 0), font=font_bold)
    
    draw.text((60, 310), "Adresse :", fill=(80, 80, 80), font=font_body)
    draw.text((220, 310), "15 RUE DE LA LIBERTE, TUNIS", fill=(0, 0, 0), font=font_bold)

    # Détails de la facture
    draw.rectangle([40, 400, width-40, 550], fill=(255, 250, 240), outline=(238, 232, 170), width=1)
    draw.text((60, 420), "DETAILS DE LA FACTURE", fill=(139, 69, 19), font=font_header)
    
    draw.text((60, 460), "Reference client :", fill=(80, 80, 80), font=font_body)
    draw.text((220, 460), "987654321", fill=(0, 0, 0), font=font_bold)

    draw.text((60, 490), "Montant a payer (TND) :", fill=(80, 80, 80), font=font_body)
    draw.text((220, 490), "142,500 TND", fill=(139, 0, 0), font=font_bold)

    # Footer
    draw.text((width // 2, 950), "Merci pour votre confiance. Service Client STEG Tunisie.", fill=(120, 120, 120), font=font_body, anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
    print(f"[OK] Mock Facture STEG cree avec succes : {output_path}")

if __name__ == "__main__":
    # Générer les images tunisiennes de test
    creer_mock_cin_tunisienne("images_test/cin_tunisienne.png")
    creer_mock_facture_steg("images_test/facture_steg.png")
