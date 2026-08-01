import os
import sys
import logging
import warnings
# Désactiver MKLDNN / OneDNN pour éviter les bugs de compatibilité sur CPU
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

# Configurer la console Windows pour l'affichage UTF-8 (évite les crashs d'encodage)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Désactiver les avertissements inutiles pour garder la console propre
warnings.filterwarnings('ignore')
logging.disable(logging.DEBUG)

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("[ERREUR] PaddleOCR n'est pas installé dans cet environnement virtuel.")
    print("Veuillez installer paddlepaddle et paddleocr.")
    sys.exit(1)

def analyser_image_ocr(image_path):
    print("\n" + "="*60)
    print(f"🚀 ANALYSE OCR : {image_path}")
    print("="*60)
    
    if not os.path.exists(image_path):
        print(f"[ERREUR] Le fichier {image_path} n'existe pas.")
        return
        
    print("⏳ Chargement du modèle PaddleOCR (CPU)...")
    try:
        # Initialisation de PaddleOCR (langue française/anglaise par défaut)
        # use_angle_cls=True permet de redresser le texte orienté
        ocr = PaddleOCR(use_angle_cls=True, lang='fr', enable_mkldnn=False)
        print("✅ Modèle chargé avec succès !")
        print("⏳ Extraction du texte...")
        
        result = ocr.ocr(image_path)
        
        if result and result[0]:
            # Cas 1 : Le résultat est un dictionnaire (PaddleX v3)
            if isinstance(result[0], dict):
                texts = result[0].get('rec_texts', [])
                scores = result[0].get('rec_scores', [])
                print(f"📄 {len(texts)} lignes de texte extraites :\n")
                for i in range(len(texts)):
                    texte = texts[i]
                    confiance = scores[i] if i < len(scores) else 1.0
                    if confiance > 0.40:
                        print(f"➡️  [Conf: {confiance:.2f}] {texte}")
            # Cas 2 : Le résultat est une liste standard (PaddleOCR classique)
            elif isinstance(result[0], list):
                print(f"📄 {len(result[0])} blocs de texte détectés :\n")
                for line in result[0]:
                    try:
                        coords = line[0]
                        text_info = line[1]
                        texte = text_info[0]
                        confiance = text_info[1]
                        if confiance > 0.40:
                            print(f"➡️  [Conf: {confiance:.2f}] {texte}")
                    except Exception as e_inner:
                        pass
        else:
            print("❌ Aucun texte détecté sur cette image.")
            
    except Exception as e:
        print(f"❌ Une erreur est survenue lors de l'analyse : {e}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Si un fichier est passé en argument, on l'analyse, sinon on liste les images
    if len(sys.argv) > 1:
        analyser_image_ocr(sys.argv[1])
    else:
        dossier_images = "images_test"
        extensions_valides = ('.png', '.jpg', '.jpeg')
        
        if os.path.exists(dossier_images):
            fichiers = [os.path.join(dossier_images, f) for f in os.listdir(dossier_images) 
                        if f.lower().endswith(extensions_valides)]
            
            if fichiers:
                print(f"Trouvé {len(fichiers)} images de test dans le dossier '{dossier_images}'.")
                print("Pour analyser une image spécifique, passez son chemin en argument :")
                print("Exemple : .\\venv\\Scripts\\python extraction_ocr.py images_test/1.jpg\n")
                
                for f in fichiers:
                    # On affiche juste la liste pour ne pas surcharger, ou on propose de lancer
                    print(f" - {f}")
            else:
                print(f"Aucune image trouvée dans '{dossier_images}'.")
        else:
            print(f"Le dossier '{dossier_images}' n'existe pas.")
