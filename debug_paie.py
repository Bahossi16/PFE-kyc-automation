import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from classification_documents import extraire_elements_ocr, classifier_document, extraire_donnees_fiche_paie

img = r'D:\PFE\uploads\doc_1785455637_Fiche-Paie-1.jpg'
elements = extraire_elements_ocr(img)
lignes = [e['text'] for e in elements]

print("=== TEXTE BRUT LU PAR L'OCR ===")
for i, l in enumerate(lignes):
    print(f"  [{i:02d}] {l}")

print("\n=== EXTRACTION FICHE DE PAIE ===")
donnees = extraire_donnees_fiche_paie(lignes)
for k, v in donnees.items():
    print(f"  {k}: {v}")
