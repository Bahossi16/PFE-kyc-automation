import os
import re
import sys
import fitz  # PyMuPDF — pour convertir les PDF en image

# Désactiver MKLDNN / OneDNN pour éviter les bugs de compatibilité sur CPU
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


# =======================================================================
# MODULE 0 : CONVERSION PDF -> IMAGE (si nécessaire)
# =======================================================================

def convertir_pdf_en_image(pdf_path, output_dir=None):
    """
    Convertit la première page d'un PDF en image PNG haute résolution.
    Retourne le chemin de l'image générée.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(pdf_path), "uploads_converted")
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = 3
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    image_path = os.path.join(output_dir, f"{base_name}.png")
    pix.save(image_path)
    doc.close()
    return image_path


# =======================================================================
# MODULE 1 : EXTRACTION OCR DU TEXTE BRUT + COORDONNÉES GÉOMÉTRIQUES
# =======================================================================

def extraire_elements_ocr(image_path):
    """
    Extrait le texte ET les coordonnées X,Y de chaque bloc via PaddleOCR.
    Retourne une liste de dicts : [{'text': 'STEG', 'x': 10, 'y': 20}, ...]
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='ar', enable_mkldnn=False)
        result = ocr.ocr(image_path)

        elements = []
        if result and result[0]:
            if isinstance(result[0], dict):
                # PaddleX v3 — on a les polygones dans dt_polys
                polys = result[0].get('dt_polys', [])
                texts = result[0].get('rec_texts', [])
                scores = result[0].get('rec_scores', [])
                for i, (box, text) in enumerate(zip(polys, texts)):
                    score = scores[i] if i < len(scores) else 1.0
                    if score > 0.35 and text.strip():
                        x_min = min(point[0] for point in box)
                        y_min = min(point[1] for point in box)
                        elements.append({'text': text.strip(), 'x': x_min, 'y': y_min})
            elif isinstance(result[0], list):
                # PaddleOCR classique
                for line in result[0]:
                    try:
                        box = line[0]
                        text = line[1][0]
                        score = line[1][1]
                        if score > 0.35 and text.strip():
                            x_min = min(point[0] for point in box)
                            y_min = min(point[1] for point in box)
                            elements.append({'text': text.strip(), 'x': x_min, 'y': y_min})
                    except Exception:
                        pass
        return elements

    except ImportError:
        print("[ERREUR] PaddleOCR non installé.")
        return []
    except Exception as e:
        print(f"[ERREUR OCR] {e}")
        return []


def extraire_texte_ocr(image_path):
    """
    Compatibilité ascendante : retourne une simple liste de lignes de texte.
    Utilisé par : classification_documents, CIN, Passeport, Fiche de Paie.
    """
    elements = extraire_elements_ocr(image_path)
    return [el['text'] for el in elements]


# =======================================================================
# MODULE 2 : CLASSIFICATION AUTOMATIQUE DU TYPE DE DOCUMENT
# =======================================================================

MOTS_CLES_DOCUMENT = {
    "CIN": [
        "carte d'identite", "republique tunisienne", "identite nationale",
        "cin", "جمهورية تونسية", "بطاقة تعريف"
    ],
    "PASSEPORT": [
        "passeport", "passport", "republique tunisienne", "tunisian republic",
        "passaporto", "type p", "nationality"
    ],
    "FACTURE_STEG": [
        "steg", "electricite", "gaz", "societe tunisienne",
        "facture sur releve", "facture estimee", "kwh", "fte", "rtt",
        "consommation", "abonne"
    ],
    "FACTURE_SONEDE": [
        "sonede", "eau", "societe nationale", "m3", "compteur",
        "consommation eau", "abonnement eau"
    ],
    "FACTURE_TELECOM": [
        "ooredoo", "tunisie telecom", "orange tunisie", "ttelecom",
        "telecom", "facture telephone", "ligne fixe", "internet"
    ],
    "FICHE_DE_PAIE": [
        "bulletin de paie", "fiche de paie", "salaire net", "brut",
        "cotisation", "cnss", "irpp", "employeur", "employe",
        "net a payer", "periode de paie"
    ],
    "CONTRAT_BAIL": [
        "contrat de bail", "contrat de location", "loyer", "locataire",
        "bailleur", "logement", "loue"
    ],
}

def classifier_document(lignes_texte):
    texte_brut = " ".join(lignes_texte).lower()
    scores = {}
    for type_doc, mots_cles in MOTS_CLES_DOCUMENT.items():
        score = sum(1 for mot in mots_cles if mot.lower() in texte_brut)
        scores[type_doc] = score
    type_detecte = max(scores, key=scores.get)
    if scores[type_detecte] == 0:
        if re.search(r'\b(\d{8})\b', texte_brut):
            type_detecte = "CIN"
        else:
            type_detecte = "INCONNU"
    return type_detecte, scores


# =======================================================================
# MODULE 3 : EXTRACTION STRUCTURÉE PAR TYPE DE DOCUMENT
# =======================================================================

def extraire_donnees_cin(lignes):
    """Extrait les informations d'une Carte d'Identité Nationale tunisienne."""
    texte = " ".join(lignes)
    resultats = {"type": "CIN", "cin": None, "nom": None, "prenom": None,
                 "date_naissance": None, "lieu_naissance": None}

    match_cin = re.search(r'\b(\d{8})\b', texte)
    if match_cin:
        resultats["cin"] = match_cin.group(1)

    match_date = re.search(r'\b(\d{2}[./]\d{2}[./]\d{4})\b', texte)
    if match_date:
        resultats["date_naissance"] = match_date.group(1)

    MOTS_IGNORES_CIN = {
        "CIN", "REPUBLIQUE", "TUNISIENNE", "NATIONALE", "CARTE", "IDENTITE",
        "TUNISIE", "MR", "MME", "MLLE", "MONSIEUR", "MADAME", "SEXE",
        "NAISSANCE", "LIEU", "DATE", "VALIDITE", "SIGNATURE", "PORTEUR",
        "TITULAIRE", "NOM", "PRENOM", "جمهورية", "تونسية", "بطاقة", "تعريف",
        "الجمهورية", "التونسية", "الوطنية", "التعريف",
        "اللقب", "الاسم", "تاريخ", "الولادة", "مكانها", "بنت", "بن", "مكان", "ابن"
    }
    ARABIC_WORD = re.compile(r'[\u0600-\u06FF]+')

    for i, ligne in enumerate(lignes):
        ligne_stripped = ligne.strip()
        if 'اللقب' in ligne_stripped and not resultats["nom"]:
            texte_sans_label = ligne_stripped.replace('اللقب', '').strip()
            if texte_sans_label:
                mots = [m for m in texte_sans_label.split() if ARABIC_WORD.fullmatch(m) and m not in MOTS_IGNORES_CIN]
                if mots:
                    resultats["nom"] = mots[0]
            if not resultats["nom"] and i > 0:
                precedente = lignes[i-1].strip()
                if not any(k in precedente for k in ['الاسم', 'تونسية', 'وطنية', 'تعريف']):
                    mots = [m for m in precedente.split() if ARABIC_WORD.fullmatch(m) and m not in MOTS_IGNORES_CIN]
                    if mots:
                        resultats["nom"] = mots[-1]
            if not resultats["nom"]:
                for j in range(i + 1, min(i + 3, len(lignes))):
                    suivante = lignes[j].strip()
                    mots = [m for m in suivante.split() if ARABIC_WORD.fullmatch(m) and m not in MOTS_IGNORES_CIN]
                    if mots:
                        resultats["nom"] = mots[0]
                        break
        if 'الاسم' in ligne_stripped and not resultats["prenom"]:
            texte_sans_label = ligne_stripped.replace('الاسم', '').strip()
            if texte_sans_label:
                mots = [m for m in texte_sans_label.split() if ARABIC_WORD.fullmatch(m) and m not in MOTS_IGNORES_CIN]
                if mots:
                    resultats["prenom"] = mots[0]
            if not resultats["prenom"] and i > 0:
                precedente = lignes[i-1].strip()
                if not any(k in precedente for k in ['اللقب', 'تونسية', 'وطنية', 'تعريف']):
                    mots = [m for m in precedente.split() if ARABIC_WORD.fullmatch(m) and m not in MOTS_IGNORES_CIN]
                    if mots:
                        resultats["prenom"] = mots[-1]
            if not resultats["prenom"]:
                for j in range(i + 1, min(i + 3, len(lignes))):
                    suivante = lignes[j].strip()
                    mots = [m for m in suivante.split() if ARABIC_WORD.fullmatch(m) and m not in MOTS_IGNORES_CIN]
                    if mots:
                        resultats["prenom"] = mots[0]
                        break

    if not resultats["nom"] and "اللقب" in texte:
        partie_apres = texte.split("اللقب", 1)[1]
        mots_arabe = re.findall(r'[\u0600-\u06FF]+', partie_apres)
        for mot in mots_arabe:
            if mot not in MOTS_IGNORES_CIN:
                resultats["nom"] = mot
                break

    if not resultats["prenom"] and "الاسم" in texte:
        partie_apres = texte.split("الاسم", 1)[1]
        mots_arabe = re.findall(r'[\u0600-\u06FF]+', partie_apres)
        for mot in mots_arabe:
            if mot not in MOTS_IGNORES_CIN:
                resultats["prenom"] = mot
                break

    if not resultats["nom"] or not resultats["prenom"]:
        noms = re.findall(r'\b([A-Z]{2,}(?:\s[A-Z]{2,})*)\b', texte)
        # Filtrer les groupes où TOUS les tokens sont des mots à ignorer
        noms_filtres = [n for n in noms if not all(t in MOTS_IGNORES_CIN for t in n.split())]
        for groupe in noms_filtres:
            tokens = [t for t in groupe.split() if t not in MOTS_IGNORES_CIN]
            if not tokens:
                continue
            if not resultats["nom"]:
                resultats["nom"] = tokens[0]
                if not resultats["prenom"] and len(tokens) > 1:
                    # Le 2e mot (ou plus) du même groupe = prénom
                    resultats["prenom"] = " ".join(tokens[1:])
                break
            elif not resultats["prenom"]:
                resultats["prenom"] = tokens[0]
                break

    return resultats


def extraire_donnees_passeport(lignes):
    """Extrait les informations d'un Passeport tunisien."""
    texte = " ".join(lignes)
    resultats = {"type": "PASSEPORT", "numero": None, "nom": None,
                 "prenom": None, "date_naissance": None, "date_expiration": None}

    match_pass = re.search(r'\b([A-Z]\d{7})\b', texte)
    if match_pass:
        resultats["numero"] = match_pass.group(1)

    match_date = re.search(r'\b(\d{2}[./]\d{2}[./]\d{4})\b', texte)
    if match_date:
        resultats["date_expiration"] = match_date.group(1)

    noms = re.findall(r'\b([A-Z]{2,}(?:\s[A-Z]{2,})*)\b', texte)
    noms_filtres = [n for n in noms if n not in
                    ["PASSEPORT", "PASSPORT", "REPUBLIQUE", "TUNISIENNE",
                     "TUNISIAN", "REPUBLIC", "TYPE", "NATIONALITY"]]
    if len(noms_filtres) >= 1:
        resultats["nom"] = noms_filtres[0]
    if len(noms_filtres) >= 2:
        resultats["prenom"] = noms_filtres[1]

    return resultats


def extraire_donnees_facture_steg(lignes, elements_geo=None):
    """
    Extrait les informations d'une Facture STEG/SONEDE.
    Utilise le Parser Géométrique (Bounding Boxes) si les éléments 
    géométriques sont disponibles, sinon bascule sur Regex.
    """
    texte = " ".join(lignes)
    resultats = {"type": "FACTURE_STEG", "nom_abonne": None,
                 "adresse": None, "reference_client": None,
                 "montant_total": None, "date_echeance": None}

    # Référence client STEG
    match_ref = re.search(r'\b(\d{2,3}\s?\d{3}\s?\d{3}\s?\d?)\b', texte)
    if match_ref:
        resultats["reference_client"] = match_ref.group(1).replace(" ", "")

    # Montant total
    match_montant = re.search(r'(\d+[.,]\d{3})\s*(?:TND|DT|D\.T)?', texte, re.IGNORECASE)
    if match_montant:
        resultats["montant_total"] = match_montant.group(1)

    # Date d'échéance
    match_date = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', texte)
    if match_date:
        resultats["date_echeance"] = match_date.group(1)

    # ----------------------------------------------------------------
    # EXTRACTION NOM + ADRESSE : Parser Géométrique (prioritaire)
    # ----------------------------------------------------------------
    if elements_geo:
        anchor_y = None
        anchor_x = None
        nom_client = None
        adresse_client = None

        for el in elements_geo[:50]:
            t = el['text'].strip().upper()
            if t.startswith("MR ") or t.startswith("MME ") or t.startswith("STE ") or t.startswith("M ") or t.startswith("RES "):
                # Séparer Nom et Adresse si virgule présente
                if " , " in t or ", " in t:
                    parts = re.split(r'\s*,\s*', t, maxsplit=1)
                    nom_client = parts[0].strip()
                    adresse_client = parts[1].strip() if len(parts) > 1 else ""
                else:
                    nom_client = t.split(",")[0].strip() if "," in t else t.strip()
                    adresse_client = ""
                anchor_y = el['y']
                anchor_x = el['x']
                break

        if anchor_y is not None:
            blocs_adresse = [adresse_client] if adresse_client else []
            BRUIT = {"N°Dépannage", "N°depannage", "District", "district",
                     "Dépannage", "depannage", "FACTURE", "ESTIMEE", "RELEVE",
                     "Imprimer", "imprimer"}

            for el in elements_geo:
                if el['y'] > anchor_y and el['y'] < anchor_y + 120:
                    if el['x'] < anchor_x + 500:
                        est_bruit = any(b.lower() in el['text'].lower() for b in BRUIT)
                        if not est_bruit and el['text'].strip():
                            blocs_adresse.append(el['text'].strip())

            adresse_finale = " ".join(blocs_adresse).strip()
            adresse_finale = re.sub(r'\s+', ' ', adresse_finale)

            resultats["nom_abonne"] = nom_client
            resultats["adresse"] = adresse_finale if adresse_finale else None
            return resultats

    # ----------------------------------------------------------------
    # FALLBACK : Regex sur texte simple (si pas de coordonnées géo)
    # ----------------------------------------------------------------
    MOTS_IGNORES_STEG = {
        "STEG", "FACTURE", "RELEVE", "ELECTRICITE", "POINTE", "GAZ",
        "TUNISIENNE", "CONSOMMATION", "SERVICES", "COORDONNEES", "CLIENT",
        "ABONNE", "REFERENCE", "COMPTEUR", "MONTANT", "TOTAL", "DATE",
        "ECHEANCE", "PERIODE", "DISTRIBUTION", "NATIONALE", "SOCIETE",
        "ENERGIE", "TARIF", "PUISSANCE", "SOUSCRITE"
    }

    match_nom = re.search(
        r'(?:^|\n|\s)(?:NOM\s*:?\s*|MR\.?\s+|MME\.?\s+|M\.\s+)([A-Z][A-Z\s]{2,40}?)(?=\s*(?:,|\d|N°|RUE|AV|BD|IMP|CITE|LOT|$|\n))',
        texte, re.IGNORECASE | re.MULTILINE
    )
    if match_nom:
        resultats["nom_abonne"] = match_nom.group(1).strip()
    else:
        noms = re.findall(r'\b([A-Z]{2,}(?:\s[A-Z]{2,})+)\b', texte)
        candidats = [n for n in noms if not any(token in MOTS_IGNORES_STEG for token in n.split())]
        if candidats:
            resultats["nom_abonne"] = candidats[0]

    match_adr = re.search(
        r'\b(\d+\s+(?:RUE|AV|AVE|AVENUE|BOULEVARD|BD|ROUTE|IMP|CITE|LOT|ZON|CTE|CITE)\s+[A-Z\s,\-\.]+?)(?=\d{4}|\n|$)',
        texte, re.IGNORECASE
    )
    if match_adr:
        resultats["adresse"] = match_adr.group(1).strip()

    return resultats


def extraire_donnees_fiche_paie(lignes):
    """Extrait les informations d'une Fiche de Paie tunisienne."""
    texte = " ".join(lignes)
    resultats = {"type": "FICHE_DE_PAIE", "nom_employe": None,
                 "cin": None, "employeur": None,
                 "salaire_net": None, "periode": None}

    # 1. Extraction CIN
    match_cin = re.search(r'\b(\d{8})\b', texte)
    if match_cin:
        resultats["cin"] = match_cin.group(1)

    # 2. Extraction du Nom (Recherche ciblée après "NOM ET PRENOM" ou "NOM & PRENOM")
    nom_trouve = None
    MOIS = ["JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE"]
    MOTS_EXCLUS_PAIE = ["STATUT", "MATRICULE", "ECH", "QUALIFICATION", "AFFECTATION",
                        "CATEGORIE", "GRADE", "RUBRIQUE", "CODE", "DESIGNATION", "CAT"]
    
    for i, ligne in enumerate(lignes):
        if "NOM ET PRENOM" in ligne.upper() or "NOM & PRENOM" in ligne.upper():
            for j in range(1, 8):
                if i + j >= len(lignes):
                    break
                candidat = lignes[i+j].strip()
                cand_upper = candidat.upper()

                # Exclure les lignes avec chiffres
                if any(char.isdigit() for char in candidat):
                    continue
                # Exclure les mois
                if any(m in cand_upper for m in MOIS):
                    continue
                # Exclure les mots-clés structurels du bulletin
                if any(mot in cand_upper for mot in MOTS_EXCLUS_PAIE):
                    continue
                # Exclure les titres de poste (contiennent un tiret : "Sous-Chef")
                if '-' in candidat:
                    continue
                # Exclure les lignes trop courtes (1 lettre)
                if len(candidat) < 2:
                    continue

                # CAS 1 : Ligne entièrement en MAJUSCULES (ex: "SAAD") — nom de famille
                if candidat.isupper():
                    # Essayer de combiner avec la ligne suivante (le prénom)
                    if i + j + 1 < len(lignes):
                        suivante = lignes[i+j+1].strip()
                        if (not any(char.isdigit() for char in suivante)
                                and '-' not in suivante
                                and len(suivante) >= 2
                                and not any(m in suivante.upper() for m in MOIS)
                                and not any(mot in suivante.upper() for mot in MOTS_EXCLUS_PAIE)):
                            nom_trouve = candidat + " " + suivante
                        else:
                            nom_trouve = candidat
                    else:
                        nom_trouve = candidat
                    break

                # CAS 2 : Plusieurs mots sans tiret (ex: "Mohamed Ali")
                elif len(candidat.split()) >= 2:
                    nom_trouve = candidat
                    break
            if nom_trouve:
                break
                
    if not nom_trouve:
        # Fallback générique
        EXCLURE = {"CNSS", "IRPP", "TVA", "BRUT", "NET", "SALAIRE", "BULLETIN", "PAIE", "EMPLOYE", "EMPLOYEUR", "PAYER", "TOTAL", "MONTANT", "DESIGNATION", "TECHNIQUE", "PORTUAIRE", "ZONE", "EXPLOITATION", "DECLARANT", "RETENUES", "GAINS"}
        noms = re.findall(r'\b([A-Z]{2,}(?:\s[A-Z]{2,})*)\b', texte)
        candidats = [n for n in noms if not any(t in EXCLURE for t in n.split()) and len(n) > 8]
        if candidats:
            nom_trouve = max(candidats, key=len)

    if nom_trouve:
        # Nettoyer "MR" ou "MME"
        for prefix in ["MR ", "MME ", "M "]:
            if nom_trouve.upper().startswith(prefix):
                nom_trouve = nom_trouve[len(prefix):].strip()
        # Séparer les mots s'ils sont collés (ex: MBARKIOMRANE) mais c'est difficile sans dico.
        # Au moins on l'enregistre tel quel.
        resultats["nom_employe"] = nom_trouve

    # 3. Extraction du Net à payer
    # Format classique : "NET A PAYER 1499.000"
    match_salaire_ligne = re.search(
        r'(?:net\s*[\w]*\s*[\u00e0a]?\s*payer|salaire\s*net)\s*[:\-]?\s*([\d][\d.,\u00a0]*[\d]|\d)',
        texte, re.IGNORECASE
    )
    if match_salaire_ligne:
        raw = match_salaire_ligne.group(1)
    else:
        # Format Tabulaire Sage Paie : Le NET est souvent le dernier grand nombre avec 3 décimales de la page
        nombres = re.findall(r'\b(\d{3,}[\.\,]\d{3})\b', texte)
        if nombres:
            raw = nombres[-1] # On prend le dernier
        else:
            raw = None

    if raw:
        raw = raw.strip().replace('\u00a0', '').replace(' ', '').replace(',', '.')
        if raw.count('.') == 1 and len(raw.split('.')[1]) == 3 and float(raw) > 10000:
            # Gérer 1.500 comme 1500 si mal lu
            raw = raw.replace('.', '')
        try:
            resultats["salaire_net"] = float(raw)
        except ValueError:
            pass

    return resultats


# =======================================================================
# DICT D'EXTRACTEURS
# =======================================================================

EXTRACTEURS = {
    "CIN": extraire_donnees_cin,
    "PASSEPORT": extraire_donnees_passeport,
    "FACTURE_STEG": extraire_donnees_facture_steg,
    "FACTURE_SONEDE": extraire_donnees_facture_steg,
    "FACTURE_TELECOM": extraire_donnees_facture_steg,
    "FICHE_DE_PAIE": extraire_donnees_fiche_paie,
}

FACTURES_TYPES = {"FACTURE_STEG", "FACTURE_SONEDE", "FACTURE_TELECOM"}


def analyser_document(image_path):
    """
    Pipeline complet :
    1. Extraction OCR géométrique
    2. Classification du type de document
    3. Extraction structurée (avec Bounding Boxes pour les factures)
    """
    print("\n" + "="*65)
    print(f"  ANALYSE DU DOCUMENT : {os.path.basename(image_path)}")
    print("="*65)

    if not os.path.exists(image_path):
        print(f"[ERREUR] Fichier introuvable : {image_path}")
        return None

    print("Étape 1 : Extraction OCR géométrique en cours...")
    elements_geo = extraire_elements_ocr(image_path)
    lignes = [el['text'] for el in elements_geo]
    if not lignes:
        print("[ERREUR] Aucun texte extrait par l'OCR.")
        return None
    print(f"          {len(lignes)} blocs de texte extraits.")

    print("Étape 2 : Classification automatique du document...")
    type_doc, scores = classifier_document(lignes)
    print(f"          Type détecté : {type_doc}")

    print("Étape 3 : Extraction des données structurées...")
    extracteur = EXTRACTEURS.get(type_doc)
    if extracteur:
        if type_doc in FACTURES_TYPES:
            donnees = extracteur(lignes, elements_geo=elements_geo)
        else:
            donnees = extracteur(lignes)
    else:
        donnees = {"type": type_doc, "texte_brut": lignes}

    print("\n  DONNÉES EXTRAITES :")
    for cle, valeur in donnees.items():
        if valeur and cle != "type":
            print(f"   {cle:<20} : {valeur}")
    print("="*65 + "\n")
    return donnees


if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyser_document(sys.argv[1])
    else:
        print("\nUsage : .\\venv\\Scripts\\python classification_documents.py <chemin_image_ou_pdf>")
