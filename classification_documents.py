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

# Instance globale PaddleOCR (singleton)
_ocr_instance = None

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
        global _ocr_instance
        if _ocr_instance is None:
            _ocr_instance = PaddleOCR(use_textline_orientation=True, lang='ar', enable_mkldnn=False)
        ocr = _ocr_instance
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
                        x_min = float(min(point[0] for point in box))
                        y_min = float(min(point[1] for point in box))
                        elements.append({'text': text.strip(), 'x': x_min, 'y': y_min})
            elif isinstance(result[0], list):
                # PaddleOCR classique
                for line in result[0]:
                    try:
                        box = line[0]
                        text = line[1][0]
                        score = line[1][1]
                        if score > 0.35 and text.strip():
                            x_min = float(min(point[0] for point in box))
                            y_min = float(min(point[1] for point in box))
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
    finally:
        # Force la libération de la mémoire (Memory Leak PaddlePaddle)
        import gc
        gc.collect()


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
        "cin", "جمهورية تونسية", "بطاقة تعريف", "الجمهورية التونسية", "بطاقة التعريف"
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
        "net a payer", "net à payer", "periode de paie",
        "traitement net", "net mensuel", "net verse", "salaire de base",
        "bulletin de salaire", "bulletin mensuel", "retenues", "gains"
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
        # Supprimer les diacritiques arabes (Tashkeel) pour une comparaison robuste
        ligne_stripped = re.sub(r'[\u064B-\u065F]', '', ligne_stripped)
        
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
                 "nom": None, "prenom": None,
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

    def _finaliser_steg(res):
        nom_complet = res.pop("nom_abonne", None)
        if nom_complet:
            nom_upper = nom_complet.upper().strip()
            # Cas spécial : Résidence ou Société → pas de Nom/Prénom séparables
            if nom_upper.startswith("RES ") or nom_upper.startswith("STE "):
                res["nom"] = nom_complet.strip()
                res["prenom"] = ""
                return res
            # Supprimer les civilités courantes
            for prefix in ["MR B ", "MME B ", "MR ", "MME ", "M "]:
                if nom_upper.startswith(prefix):
                    nom_complet = nom_complet[len(prefix):].strip()
                    nom_upper = nom_complet.upper().strip()
                    break
            parts = nom_complet.split()
            if len(parts) >= 2:
                # Cas noms composés tunisiens : B / BEN / EL / AL en tête
                if parts[0].upper() in ["BEN", "B", "EL", "AL", "ABOU", "HAJ", "ELHAJ"] and len(parts) >= 3:
                    res["nom"] = parts[0] + " " + parts[1]
                    res["prenom"] = " ".join(parts[2:])
                # Cas particule courte (DE, DU, JE, etc. <= 2 chars) : regrouper avec le mot suivant
                elif len(parts[0]) <= 2 and len(parts) >= 3:
                    res["nom"] = parts[0] + " " + parts[1]
                    res["prenom"] = " ".join(parts[2:])
                else:
                    res["nom"] = parts[0]
                    res["prenom"] = " ".join(parts[1:])
            else:
                res["nom"] = nom_complet
                res["prenom"] = ""
        return res

    # ----------------------------------------------------------------
    # EXTRACTION NOM + ADRESSE : Parser Géométrique (prioritaire)
    # ----------------------------------------------------------------
    if elements_geo:
        anchor_y = None
        anchor_x = None
        nom_client = None
        adresse_client = None

        for el in elements_geo[:80]:
            t = el['text'].strip().upper()
            # Chercher la ligne qui commence par une civilité ou RES/STE
            # On accepte aussi t == "RES" (sans espace) car l'OCR peut couper le bloc
            is_anchor = (
                t.startswith("MR ") or t.startswith("MME ") or t.startswith("STE ")
                or t.startswith("M ") or t.startswith("RES ")
                or t in ("RES", "MR", "MME", "STE")
            )
            if is_anchor:
                idx = elements_geo.index(el)
                ligne_complete = el['text'].strip()
                # Limiter la concaténation à la MOITIÉ GAUCHE du document
                # pour ne pas avaler la colonne N°Dépannage (droite)
                X_LIGNE_MAX = el['x'] + 300
                for el2 in elements_geo[idx+1:idx+6]:
                    # Même ligne (y proche) ET dans la partie gauche
                    if abs(el2['y'] - el['y']) < 10 and el2['x'] < X_LIGNE_MAX:
                        # Stopper si on rencontre N° ou texte arabe ou un mot du district dans le bloc
                        if re.search(r'N°|رقم|تدخل|DISTRICT|TUNIS|VILLE|SFAX|SOUSSE|NABEUL', el2['text'], re.IGNORECASE):
                            break
                        ligne_complete += " " + el2['text'].strip()
                    else:
                        break
                ligne_complete = ligne_complete.upper()
                # Séparer Nom et Adresse si virgule présente
                if ", " in ligne_complete:
                    parts = re.split(r'\s*,\s*', ligne_complete, maxsplit=1)
                    nom_client = parts[0].strip()
                    adresse_client = parts[1].strip() if len(parts) > 1 else ""
                else:
                    nom_client = ligne_complete.strip()
                    adresse_client = ""
                anchor_y = el['y']
                anchor_x = el['x']
                break

        if anchor_y is not None:
            # ---- Stratégie 1 : L'adresse est DÉJÀ dans la ligne du nom ----
            # Si adresse_client contient un code postal tunisien (4 chiffres),
            # on l'utilise directement sans chercher d'autres blocs.
            CODE_POSTAL_RE = re.compile(r'\b\d{4}\b')
            if adresse_client and CODE_POSTAL_RE.search(adresse_client):
                # Nettoyer : tronquer au premier N° ou texte arabe et la 1ère date
                adresse_propre = adresse_client
                adresse_propre = re.split(r'(?i)\s*N°|\s*رقم|\s*تدخل', adresse_propre, maxsplit=1)[0].strip()
                adresse_propre = re.split(
                    r'\s*(?:من|إلى|CONSOMMATION|SERVICES|من\s|\d{2}[-/]\d{2}[-/]\d{4})',
                    adresse_propre, maxsplit=1
                )[0].strip()
                resultats["nom_abonne"] = nom_client
                resultats["adresse"] = adresse_propre if adresse_propre else None
                return _finaliser_steg(resultats)

            # ---- Stratégie 2 : Chercher l'adresse dans les blocs géométriques voisins ----
            blocs_adresse = [adresse_client] if adresse_client else []
            BRUIT = {
                # En-têtes STEG droit (numéro de dépannage, district, etc.)
                "N\u00b0Dépannage", "N°depannage", "N°DEPANNAGE", "DEPANNAGE",
                "District", "district", "DISTRICT",
                "Dépannage", "depannage", "FACTURE", "ESTIMEE", "RELEVE",
                "Imprimer", "imprimer", "CONSOMMATION", "SERVICES",
                "ELECTRICITE", "Référence", "REFERENCE", "MONTANT",
                "TOTAL", "Facture", "Abonné", "ABONNE",
                # Noms de villes tunisiennes (peuvent apparaître dans le champ District)
                "TUNIS", "VILLE", "SFAX", "SOUSSE", "NABEUL", "BIZERTE",
                "ARIANA", "BEN AROUS", "MONASTIR", "MAHDIA", "GABES",
                # Mots-clés arabes des tableaux STEG
                "المعدل", "الكمية", "عدد", "الأشهر", "سعر", "الوحدة",
                "المبلغ", "الإنسباب", "الاستهلاك", "الخدمات", "السبيانات",
                "كهرباء", "البيانات", "الأقساط", "ديون", "دفوعات",
                "من", "إلى", "المرجع", "رقم", "التدخل",
            }

            # La colonne droite du document STEG (N°Dépannage, district) commence
            # généralement à x > anchor_x + 250 — on la coupe strictement
            X_MAX = anchor_x + 260
            for el in elements_geo:
                if el['y'] > anchor_y and el['y'] < anchor_y + 70:
                    if el['x'] < X_MAX:
                        est_bruit = any(b.lower() in el['text'].lower() for b in BRUIT)
                        import unicodedata
                        est_arabe = all(
                            unicodedata.bidirectional(c) in ('AL', 'AN', 'NSM', 'WS', 'ON')
                            for c in el['text'].replace(' ', '') if c.strip()
                        )
                        # Stopper immédiatement si on rencontre "N°" ou du texte arabe
                        if re.search(r'N°|رقم|تدخل', el['text'], re.IGNORECASE):
                            break
                        if not est_bruit and not est_arabe and el['text'].strip():
                            blocs_adresse.append(el['text'].strip())
                            if CODE_POSTAL_RE.search(el['text']):
                                break

            adresse_finale = " ".join(blocs_adresse).strip()
            adresse_finale = re.sub(r'\s+', ' ', adresse_finale)
            # Tronquer au premier N° ou texte arabe parasite
            adresse_finale = re.split(r'\s*N°|\s*رقم|\s*تدخل', adresse_finale, maxsplit=1)[0].strip()
            # Tronquer si du bruit traîne quand même après le code postal
            match_troncature = re.search(r'(\d{4}\s+[A-Z]+)', adresse_finale.upper())
            if match_troncature:
                adresse_finale = adresse_finale[:match_troncature.end()].strip()

            resultats["nom_abonne"] = nom_client
            resultats["adresse"] = adresse_finale if adresse_finale else None
            return _finaliser_steg(resultats)


    # ----------------------------------------------------------------
    # FALLBACK : Regex sur texte simple (si pas de coordonnées géo)
    # ----------------------------------------------------------------
    MOTS_IGNORES_STEG = {
        "STEG", "FACTURE", "RELEVE", "ELECTRICITE", "POINTE", "GAZ",
        "TUNISIENNE", "CONSOMMATION", "SERVICES", "COORDONNEES", "CLIENT",
        "ABONNE", "REFERENCE", "COMPTEUR", "MONTANT", "TOTAL", "DATE",
        "ECHEANCE", "PERIODE", "DISTRIBUTION", "NATIONALE", "SOCIETE",
        "ENERGIE", "TARIF", "PUISSANCE", "SOUSCRITE", "ZERO", "MILLIMES", "TTC",
        "TND", "PAYER", "AVANT", "COPIE", "NET", "TVA"
    }

    # Regex : cherche une ligne qui commence par MR / MME / RES / STE
    # On scanne les lignes brutes pour capturer même quand le texte est concaténé
    nom_trouve = None
    for ligne in lignes:
        l = ligne.strip()
        lu = l.upper()
        if (lu.startswith("MR ") or lu.startswith("MME ") or lu.startswith("M ")
                or lu.startswith("RES ") or lu.startswith("STE ")):
            # Garder uniquement la partie avant la première virgule ou chiffre
            nom_partie = re.split(r'\s*,', l, maxsplit=1)[0].strip()
            # Nettoyer : supprimer N° et tout ce qui suit
            nom_partie = re.split(r'\s*N°', nom_partie, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if nom_partie:
                nom_trouve = nom_partie
                break

    if not nom_trouve:
        # Fallback regex sur le texte brut concaténé
        match_nom = re.search(
            r'(?:^|\n)\s*((?:MR\.?\s+|MME\.?\s+|M\.\s+|RES\s+|STE\s+)[A-Z][A-Z\s\.]{1,50}?)(?=\s*,|\s*\d|\s*$)',
            texte, re.IGNORECASE | re.MULTILINE
        )
        if match_nom:
            nom_trouve = match_nom.group(1).strip()
        else:
            # Dernier recours : candidats tout-majuscules en ignorant le bruit STEG
            noms = re.findall(r'\b([A-Z]{2,}(?:\s[A-Z]{2,})+)\b', texte)
            MOTS_BRUIT = MOTS_IGNORES_STEG | {"ELECTRICITE", "ECLAIRAGE", "GAZ", "NATUR",
                                               "BLOC", "ETAGE", "APP", "CITE", "CTE", "RDC",
                                               "BIS", "RUE", "DEPANNAGE", "DISTRICT"}
            candidats = [n for n in noms if not any(token in MOTS_BRUIT for token in n.split())]
            if candidats:
                nom_trouve = candidats[0]

    if nom_trouve:
        resultats["nom_abonne"] = nom_trouve

    match_adr = re.search(
        r'\b(\d+\s+(?:RUE|AV|AVE|AVENUE|BOULEVARD|BD|ROUTE|IMP|CITE|LOT|ZON|CTE|CITE)\s+[A-Z\s,\-\.]+?)(?=\d{4}|\n|$)',
        texte, re.IGNORECASE
    )
    if match_adr:
        resultats["adresse"] = match_adr.group(1).strip()

    return _finaliser_steg(resultats)


def extraire_donnees_fiche_paie(lignes, elements_geo=None, image_path=None):
    """Extrait les informations d'une Fiche de Paie tunisienne."""
    texte = " ".join(lignes)
    resultats = {"type": "FICHE_DE_PAIE", "nom": None, "prenom": None,
                 "cin": None, "employeur": None,
                 "salaire_net": None, "periode": None}

    # 1. Extraction CIN (Doit être précédé d'un mot-clé pour éviter les faux positifs type matricule)
    match_cin = re.search(r'(?:C\.?I\.?N|CARTE D\'IDENTITE|IDENTITE|CIN\s*N°|CN)\s*[:\-]?\s*\(?\s*(\d{7,8})', texte, re.IGNORECASE)
    if match_cin:
        resultats["cin"] = match_cin.group(1).zfill(8)

    # 2. Extraction du Nom (Recherche ciblée après "NOM ET PRENOM" ou "NOM & PRENOM")
    nom_trouve = None
    MOIS = ["JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE"]
    MOTS_EXCLUS_PAIE = ["STATUT", "MATRICULE", "ECH", "QUALIFICATION", "AFFECTATION",
                        "CATEGORIE", "GRADE", "RUBRIQUE", "CODE", "DESIGNATION", "CAT",
                        "NOM", "PRENOM"]  # Eviter que les labels du tableau soient pris comme nom
    
    for i, ligne in enumerate(lignes):
        ligne_up = ligne.upper()
        # Variantes larges pour l'étiquette du nom (robuste aux espaces manquants de l'OCR)
        est_etiquette_nom = bool(
            re.search(r'NOM\s*(?:ET|&)\s*PRENOM', ligne_up)
            or re.search(r'\bNOM\s*:', ligne_up)
        )
        # Cas spécial : "NOM : SAAD" sur la même ligne
        if est_etiquette_nom and ":" in ligne:
            partie = ligne.split(":", 1)[1].strip()
            if partie and not any(char.isdigit() for char in partie):
                nom_trouve = partie
                break
        if est_etiquette_nom:
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
                # Exclure les lignes avec symbole & (entête "NOM & PRENOM")
                if '&' in candidat:
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

    # CAS SPECIAL : "NOM :" et "PRENOM :" sur des lignes séparées
    if not nom_trouve:
        nom_seul, prenom_seul = None, None
        for ligne in lignes:
            m = re.match(r'\b(?:NOM|NOM DE FAMILLE)\b\s*:?\s*(.+)', ligne, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val and not any(c.isdigit() for c in val):
                    nom_seul = val
            m2 = re.match(r'\bPRENOM\b\s*:?\s*(.+)', ligne, re.IGNORECASE)
            if m2:
                val2 = m2.group(1).strip()
                if val2 and not any(c.isdigit() for c in val2):
                    prenom_seul = val2
        if nom_seul and prenom_seul:
            nom_trouve = nom_seul + " " + prenom_seul
        elif nom_seul:
            nom_trouve = nom_seul

    # CAS SPECIAL : "NOMME", "MONSIEUR", "M./MME" suivi du nom
    if not nom_trouve:
        m = re.search(r'\b(?:NOMME|INTITULE|MONSIEUR|MADAME|MR|MME|M\.?)\b\s*[:\-]?\s*([A-Z][A-Za-z\s]{3,})', texte, re.IGNORECASE)
        if m:
            nom_trouve = m.group(1).strip()

    if not nom_trouve:
        # Fallback générique
        EXCLURE = {
            "CNSS", "IRPP", "TVA", "BRUT", "NET", "SALAIRE", "BULLETIN", "PAIE",
            "EMPLOYE", "EMPLOYEUR", "PAYER", "TOTAL", "MONTANT", "DESIGNATION",
            "TECHNIQUE", "PORTUAIRE", "ZONE", "EXPLOITATION", "DECLARANT",
            "RETENUES", "GAINS", "URSSAF", "CSG", "FNAL", "AGS", "APEC",
            # Entêtes de colonnes à exclure
            "NOM", "PRENOM", "MATRICULE", "STATUT", "RUBRIQUE", "QUALIFICATION",
            "AFFECTATION", "CODE", "DESIGNATION", "CATEGORIE", "GRADE",
            # Mots structurels
            "TRANSIT", "TRANSPORT", "RADES", "DECLARATION", "DOUANES",
            "EXPLOITATION", "ENTREPRISE", "SOCIETE", "PAIE", "SIGNATURE",
            "BULLETIN", "MENSUEL"
        }
        noms = re.findall(r'\b([A-Z]{2,}(?:\s[A-Z]{2,})*)\b', texte)
        candidats = [n for n in noms if not any(t in EXCLURE for t in n.split()) and len(n) > 8]
        if candidats:
            nom_trouve = max(candidats, key=len)

    if nom_trouve:
        # Rejeter le nom s'il contient "&" (label "NOM & PRENOM")
        if '&' in nom_trouve:
            nom_trouve = None
        # Rejeter si c'est un mot-clé structurel (NOM, PRENOM, MATRICULE...)
        STRUCTURAL_LABELS = {"NOM", "PRENOM", "MATRICULE", "DESIGNATION", "RUBRIQUE"}
        if nom_trouve and any(nom_trouve.upper().strip() == lbl for lbl in STRUCTURAL_LABELS):
            nom_trouve = None

    if nom_trouve:
        # Nettoyer "MR" ou "MME"
        for prefix in ["MR ", "MME ", "M "]:
            if nom_trouve.upper().startswith(prefix):
                nom_trouve = nom_trouve[len(prefix):].strip()
        
        # Nettoyer des mots parasites éventuels
        for parasite in ["SERVICES", "FONCTION", "AGENCE", "S.F", "CELEBATAIRE", "CELIBATAIRE", "MATRICULE", "ADRESSE"]:
            if parasite in nom_trouve.upper():
                # Trouver l'index original en ignorant la casse
                idx = nom_trouve.upper().find(parasite)
                nom_trouve = nom_trouve[:idx].strip()
        
        # Séparer le CamelCase (ex: MohamedAli -> Mohamed Ali)
        nom_trouve = re.sub(r'([a-z])([A-Z])', r'\1 \2', nom_trouve)
        
        # Séparer le Nom et le Prénom
        parts = nom_trouve.split()
        if len(parts) >= 2:
            # Si le premier mot est en majuscule et le 2e ne l'est pas (ex: SAAD Mohamed Ali)
            if parts[0].isupper() and not parts[1].isupper():
                resultats["nom"] = parts[0]
                resultats["prenom"] = " ".join(parts[1:])
            # Si le dernier mot est en majuscule (ex: Mohamed Ali SAAD)
            elif parts[-1].isupper() and not parts[-2].isupper():
                resultats["nom"] = parts[-1]
                resultats["prenom"] = " ".join(parts[:-1])
            else:
                # Fallback: le premier mot est le nom
                resultats["nom"] = parts[0]
                resultats["prenom"] = " ".join(parts[1:])
        else:
            resultats["nom"] = nom_trouve
            resultats["prenom"] = ""

    # =======================================================
    # 3. Extraction du Salaire Net
    # =======================================================
    raw = None

    # --- Stratégie 1 : Format direct "NET A PAYER", "SALAIRE NET", "TRAITEMENT NET", "NET VERSE" ---
    match_net_direct = re.search(
        r'(?:net\s*[\w]*\s*[\u00e0a]?\s*payer'
        r'|salaire\s*net(?:\s+imposable)?'
        r'|traitement\s*net'
        r'|net\s*vers[e\u00e9]'
        r'|net\s*mensuel'
        r'|net\s+[\u00e0a]\s+payer)'
        r'\s*[:\-]?\s*([1-9][\d\s.,\u00a0]*[\d])',
        texte, re.IGNORECASE
    )
    if match_net_direct:
        raw = re.sub(r'[^\d.,]', '', match_net_direct.group(1).split()[0])

    # --- Stratégie 2 : Chercher nombre directement après "SAL NET" ou "NET" dans le texte ---
    if not raw:
        # Cherche un montant collé au label NET (même ligne dans le flux OCR)
        match_net_inline = re.search(
            r'(?:SAL\.?\s*NET|NET\s*VERSE|NET\s*MENSUEL)\s+(\d{1,4}[.,]\d{2,3})',
            texte, re.IGNORECASE
        )
        if match_net_inline:
            raw = re.sub(r'[^\d.,]', '', match_net_inline.group(1))

    # --- Stratégie 3 : Format tableau tunisien (SAL NET = dernière colonne) ---
    # Cherche le nombre qui vient APRÈS la séquence AVANCES/IND.NON IMPOS dans la ligne de synthèse
    if not raw and re.search(r'(?:SAL[\s\.]*NET|\bNET\b)', texte, re.IGNORECASE):
        # Trouver le bloc "AVANCES" ou "IND.NON" et prendre le premier grand nombre après
        match_apres_avances = re.search(
            r'(?:AVANCES|IND\.?\s*NON\s*IMPOS|IND\s*NON)\s+([\d.,\s]+?)\s+(\d{1,4}[.,]\d{2,3})',
            texte, re.IGNORECASE
        )
        if match_apres_avances:
            raw = re.sub(r'[^\d.,]', '', match_apres_avances.group(2))

    # --- Stratégie 4 : Fallback — prendre le dernier grand montant (> 500) hors taxes ---
    # Le NET est normalement plus grand que l'IRPP ou la CNSS individuelle
    if not raw:
        nombres = re.findall(r'\b(\d{1,4}[.,]\d{2,3})\b', texte)
        nombres_filtres = [n for n in nombres if float(n.replace(',', '.')) > 500]
        if nombres_filtres:
            raw = nombres_filtres[-1]

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
