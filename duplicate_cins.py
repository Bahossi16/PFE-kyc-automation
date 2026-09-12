import os
import shutil

INPUT_DIR = r"D:\PFE\data"
OUTPUT_DIR = r"D:\PFE\data\mass_300_cins"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Récupérer les 11 fichiers cin originaux
base_files = [f for f in os.listdir(INPUT_DIR) if f.startswith('cin') and f.endswith('.png')]

if not base_files:
    print("Aucun fichier CIN trouvé dans le dossier D:\\PFE\\data")
    exit()

print(f"Trouvé {len(base_files)} fichiers de base. Début de la duplication pour atteindre 300 fichiers...")

# Créer 300 fichiers
for i in range(1, 301):
    # Choisir un des fichiers de base à copier (en boucle)
    source_file = base_files[i % len(base_files)]
    source_path = os.path.join(INPUT_DIR, source_file)
    
    # Nouveau nom (ex: cin_001.png)
    dest_name = f"cin_mass_{i:03d}.png"
    dest_path = os.path.join(OUTPUT_DIR, dest_name)
    
    shutil.copy2(source_path, dest_path)

print(f"\n✅ TERMINÉ ! 300 copies ont été générées dans : {OUTPUT_DIR}")
