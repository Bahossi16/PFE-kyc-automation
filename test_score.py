import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from classification_documents import extraire_elements_ocr, classifier_document, extraire_donnees_cin
import re
from jellyfish import jaro_winkler_similarity

img = r'C:\Users\bahae\.gemini\antigravity\brain\e35d5f8a-4fec-411f-a99a-7f6fa81e8e12\.user_uploaded\media__1784839503778.jpg'
elements = extraire_elements_ocr(img)
lignes_texte = [elem['text'] for elem in elements]
donnees = extraire_donnees_cin(lignes_texte)

nom_clean = f"{donnees.get('nom', '')} {donnees.get('prenom', '')}".strip().upper()
print(f"nom_clean from OCR: '{nom_clean}'")

db_nom_ar = "مباركي"
db_prenom_ar = "عمران"
nom_cbs = f"{db_nom_ar} {db_prenom_ar}".strip()
print(f"nom_cbs from DB: '{nom_cbs}'")

def jws(s1, s2):
    s1 = s1.strip().upper()
    s2 = s2.strip().upper()
    if not s1 or not s2: return 0.0
    from jellyfish import jaro_similarity
    jaro = jaro_similarity(s1, s2)
    prefix_len = 0
    for c1, c2 in zip(s1, s2):
        if c1 == c2: prefix_len += 1
        else: break
        if prefix_len == 4: break
    return (jaro + 0.1 * prefix_len * (1.0 - jaro)) * 100

score = jws(nom_clean, nom_cbs)
print(f"Score direct: {score}")

nom_extrait_sorted = " ".join(sorted(nom_clean.split()))
nom_cbs_sorted = " ".join(sorted(nom_cbs.split()))
score_sorted = jws(nom_extrait_sorted, nom_cbs_sorted)
print(f"Score sorted: {score_sorted}")

final = max(score, score_sorted)
print(f"Final Score: {final}")
