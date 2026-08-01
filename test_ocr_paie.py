import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from classification_documents import extraire_elements_ocr, classifier_document, extraire_donnees_fiche_paie

img = r'C:\Users\bahae\.gemini\antigravity\brain\e35d5f8a-4fec-411f-a99a-7f6fa81e8e12\.user_uploaded\media__1784839822656.jpg'
elements = extraire_elements_ocr(img)
lignes_texte = [elem['text'] for elem in elements]
type_doc, scores = classifier_document(lignes_texte)

if type_doc == 'FICHE_DE_PAIE':
    donnees = extraire_donnees_fiche_paie(lignes_texte)
    print(f"Type: {donnees['type']}")
    print(f"Nom: {donnees['nom_employe']}")
    print(f"Net: {donnees['salaire_net']}")
else:
    print(f"Type détecté : {type_doc}, attendu : FICHE_DE_PAIE")
    print(f"Texte extrait : {lignes_texte}")
