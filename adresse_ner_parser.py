import re

def jaro_winkler_standalone(s1, s2):
    """
    Copie légère de Jaro-Winkler pour éviter les imports circulaires.
    Si les chaînes sont vides, on retourne 0.
    """
    if not s1 or not s2:
        return 0.0
    s1, s2 = s1.upper().strip(), s2.upper().strip()
    if s1 == s2:
        return 100.0

    len1, len2 = len(s1), len(s2)
    max_dist = max(len1, len2) // 2 - 1
    match = 0
    hash_s1 = [0] * len1
    hash_s2 = [0] * len2

    for i in range(len1):
        for j in range(max(0, i - max_dist), min(len2, i + max_dist + 1)):
            if s1[i] == s2[j] and hash_s2[j] == 0:
                hash_s1[i] = 1
                hash_s2[j] = 1
                match += 1
                break

    if match == 0:
        return 0.0

    t = 0
    point = 0
    for i in range(len1):
        if hash_s1[i]:
            while hash_s2[point] == 0:
                point += 1
            if s1[i] != s2[point]:
                t += 1
            point += 1
    t /= 2

    match = float(match)
    jaro = (match / len1 + match / len2 + (match - t) / match) / 3.0

    # Prefix scale (Winkler)
    prefix = 0
    for i in range(min(4, min(len1, len2))):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    jw = jaro + (prefix * 0.1 * (1 - jaro))
    return jw * 100.0


def parser_adresse_ner(adresse):
    """
    Parseur NER Rule-Based pour une adresse tunisienne.
    Extrait : numero, type_voie, nom_voie, code_postal, ville
    """
    adresse = adresse.upper().strip()
    entites = {
        "numero": "",
        "type_voie": "",
        "nom_voie": "",
        "code_postal": "",
        "ville": ""
    }

    # 1. Extraction Code Postal (4 chiffres)
    match_cp = re.search(r'\b(\d{4})\b', adresse)
    if match_cp:
        entites["code_postal"] = match_cp.group(1)
        # La ville est généralement le mot (ou les mots) qui suivent le code postal
        morceau_fin = adresse[match_cp.end():].strip()
        # On nettoie la ville des ponctuations
        entites["ville"] = re.sub(r'[^A-Z\s]', '', morceau_fin).strip()
        
        # On retire la partie CP + Ville de l'adresse pour parser le reste
        adresse = adresse[:match_cp.start()].strip()
    
    # 2. Extraction Numéro
    match_num = re.search(r'^\b(\d{1,4}[A-Z]?)\b', adresse)
    if match_num:
        entites["numero"] = match_num.group(1)
        adresse = adresse[match_num.end():].strip()

    # 3. Extraction Type de Voie
    types_communs = r'\b(RUE|AVENUE|AV|BOULEVARD|BLVD|CITE|IMPASSE|ROUTE|CHEMIN|AV\.|R\.|BVD)\b'
    match_type = re.search(types_communs, adresse)
    if match_type:
        entites["type_voie"] = match_type.group(1)
        entites["nom_voie"] = adresse[match_type.end():].strip()
    else:
        entites["nom_voie"] = adresse.strip()
        
    # Nettoyage
    for k in entites:
        entites[k] = re.sub(r'[^\w\s]', '', entites[k]).strip()
        
    return entites


def comparer_adresses_ner(adr_ocr, adr_cbs):
    """
    Compare deux adresses en utilisant la décomposition NER et pondération.
    - Ville : 40%
    - Nom voie : 30%
    - Code Postal : 20%
    - Numero : 10%
    """
    if not adr_ocr or not adr_cbs:
        return 0.0
        
    ner_ocr = parser_adresse_ner(adr_ocr)
    ner_cbs = parser_adresse_ner(adr_cbs)
    
    # Calcul des scores par composant
    score_ville = jaro_winkler_standalone(ner_ocr["ville"], ner_cbs["ville"]) if ner_cbs["ville"] else 0.0
    score_voie = jaro_winkler_standalone(ner_ocr["nom_voie"], ner_cbs["nom_voie"]) if ner_cbs["nom_voie"] else 0.0
    
    # Exact match pour le code postal et numéro car ce sont des chiffres/identifiants courts
    score_cp = 100.0 if (ner_ocr["code_postal"] and ner_ocr["code_postal"] == ner_cbs["code_postal"]) else 0.0
    score_num = 100.0 if (ner_ocr["numero"] and ner_ocr["numero"] == ner_cbs["numero"]) else 0.0
    
    # Si la CBS n'a pas pu être parsée proprement, on fait un fallback sur la string brute
    if not ner_cbs["ville"] and not ner_cbs["code_postal"] and not ner_cbs["nom_voie"]:
        return jaro_winkler_standalone(adr_ocr, adr_cbs)

    # Répartition des poids dynamique en fonction de ce qui existe dans la base CBS
    poids_total = 0
    score_final = 0
    
    if ner_cbs["ville"]:
        poids_total += 40
        score_final += score_ville * 0.40
    if ner_cbs["nom_voie"]:
        poids_total += 30
        score_final += score_voie * 0.30
    if ner_cbs["code_postal"]:
        poids_total += 20
        score_final += score_cp * 0.20
    if ner_cbs["numero"]:
        poids_total += 10
        score_final += score_num * 0.10
        
    if poids_total == 0:
        return jaro_winkler_standalone(adr_ocr, adr_cbs)
        
    return (score_final / (poids_total / 100))
