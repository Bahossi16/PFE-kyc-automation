"""
=======================================================================
  LARGE-SCALE EVALUATION SCRIPT - LOCAL (Bypassing Flask)
  Projet PFE : Automatisation KYC
=======================================================================
"""
import os
import sys
import json
import time
import random
import re
import mysql.connector

# Importer les modules locaux de l'application
from classification_documents import extraire_elements_ocr, classifier_document, EXTRACTEURS, FACTURES_TYPES
from normalisateur_phonetique import filtrer_phonetique_tunisienne
from referentiel_postal import charger_referentiel_postal, normaliser_adresse

DATASET_DIR = r"D:\PFE\dataset_synthetique_masse"
SAMPLE_SIZE = 30  # documents par type

CATEGORIES = {
    "CIN (Arabic)"  : lambda f: f.startswith("cin_mass"),
    "Payslip (T1)"  : lambda f: f.startswith("paie_mass") or f.startswith("paie2_mass_exist"),
    "Payslip (T2)"  : lambda f: f.startswith("paie2_mass_new"),
    "STEG Bill"     : lambda f: f.startswith("steg_mass"),
}

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'cbs_kyc',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

REFERENTIEL_POSTAL = charger_referentiel_postal()

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def jaro_similarity(s1, s2):
    s1_len = len(s1)
    s2_len = len(s2)
    if s1_len == 0 and s2_len == 0: return 1.0
    if s1_len == 0 or s2_len == 0: return 0.0
    match_distance = max(s1_len, s2_len) // 2 - 1
    s1_matches = [False] * s1_len
    s2_matches = [False] * s2_len
    matches = 0
    transpositions = 0
    for i in range(s1_len):
        start = max(0, i - match_distance)
        end = min(s2_len, i + match_distance + 1)
        for j in range(start, end):
            if s2_matches[j]: continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
    if matches == 0: return 0.0
    k = 0
    for i in range(s1_len):
        if not s1_matches[i]: continue
        while not s2_matches[k]: k += 1
        if s1[i] != s2[k]: transpositions += 1
        k += 1
    return (matches / s1_len + matches / s2_len + (matches - transpositions / 2) / matches) / 3.0

def jaro_winkler_similarity(s1, s2):
    s1 = s1.strip().upper()
    s2 = s2.strip().upper()
    if not s1 or not s2: return 0.0
    jaro = jaro_similarity(s1, s2)
    prefix_len = 0
    for c1, c2 in zip(s1, s2):
        if c1 == c2: prefix_len += 1
        else: break
        if prefix_len == 4: break
    return (jaro + 0.1 * prefix_len * (1.0 - jaro)) * 100

def process_document(image_path, db_conn):
    try:
        # OCR
        elements_geo = extraire_elements_ocr(image_path)
        if not elements_geo:
            return "Error", "OCR vide"
        lignes = [el['text'] for el in elements_geo]
        type_doc, _ = classifier_document(lignes)
        
        extracteur = EXTRACTEURS.get(type_doc)
        if extracteur:
            if type_doc in FACTURES_TYPES:
                extracted = extracteur(lignes, elements_geo=elements_geo)
            else:
                extracted = extracteur(lignes)
        else:
            return "Error", "Type non supporte"
            
        cin_found = extracted.get('cin')
        nom_clean = extracted.get('nom', '').strip()
        adresse_ocr_brute = extracted.get('adresse', '')
        
        adresse_normalisee = ""
        if type_doc in FACTURES_TYPES and adresse_ocr_brute:
            adr_phon = filtrer_phonetique_tunisienne(adresse_ocr_brute)
            extracted['adresse_phonetique'] = adr_phon
            adresse_normalisee = normaliser_adresse(adr_phon, REFERENTIEL_POSTAL)

        # Base de donnees
        cursor = db_conn.cursor(dictionary=True)
        db_client = None
        
        # Pour les CIN generes, le nom du fichier contient souvent l'id ou on l'extrait
        # En theorie on match par CIN
        if cin_found:
            cursor.execute("SELECT * FROM clients WHERE cin = %s", (cin_found,))
            db_client = cursor.fetchone()
            
        if not db_client and nom_clean:
            cursor.execute("SELECT * FROM clients")
            all_clients = cursor.fetchall()
            best_score = 0
            best_match = None
            for client in all_clients:
                nom_cbs_fr = f"{client['nom']} {client['prenom']}".strip().upper()
                nom_cbs_ar = f"{client.get('nom_ar','')} {client.get('prenom_ar','')}".strip()
                
                # Check FR
                score = jaro_winkler_similarity(nom_clean, nom_cbs_fr)
                # Check AR if arabic text
                if re.search(r'[\u0600-\u06FF]', nom_clean) and nom_cbs_ar:
                    score_ar = jaro_winkler_similarity(nom_clean, nom_cbs_ar)
                    score = max(score, score_ar)
                    
                if score > best_score and score >= 55:
                    best_score = score
                    best_match = client
            db_client = best_match

        if not db_client:
            return "Anomaly", "Client introuvable en base"

        # Matching Logic
        anomalies = []
        
        # Intelligence bilingue
        if re.search(r'[\u0600-\u06FF]', nom_clean) and db_client.get('nom_ar'):
            nom_cbs = f"{db_client['nom_ar']} {db_client['prenom_ar']}".strip()
        else:
            nom_cbs = f"{db_client['nom']} {db_client['prenom']}".strip().upper()

        score_nom = jaro_winkler_similarity(nom_clean, nom_cbs)
        score_nom_sorted = jaro_winkler_similarity(" ".join(sorted(nom_clean.split())), " ".join(sorted(nom_cbs.split())))
        score_nom = max(score_nom, score_nom_sorted)

        if type_doc == 'CIN' and cin_found and cin_found != db_client['cin']:
            anomalies.append("Numéro CIN divergent")
        if score_nom < 75.0:
            anomalies.append(f"Nom divergent ({score_nom:.1f}%)")
            
        score_adresse = 100.0
        if type_doc in FACTURES_TYPES and adresse_ocr_brute:
            adresse_cbs = db_client['adresse'].upper().strip()
            score_brut = jaro_winkler_similarity(adresse_ocr_brute.upper().strip(), adresse_cbs)
            score_norm = jaro_winkler_similarity(adresse_normalisee, adresse_cbs) if adresse_normalisee else 0.0
            score_adresse = max(score_brut, score_norm)
            if score_adresse < 70.0:
                anomalies.append(f"Adresse divergente ({score_adresse:.1f}%)")
                
        if type_doc == 'FICHE_DE_PAIE' and extracted.get('salaire_net') and db_client.get('salaire'):
            try:
                sal_doc = float(str(extracted['salaire_net']).strip().replace(' ', '').replace(',', '.'))
                sal_cbs = float(db_client['salaire'])
                if abs(sal_doc - sal_cbs) > 10.0:
                    anomalies.append(f"Salaire divergent ({sal_doc} vs {sal_cbs})")
            except:
                pass

        if not anomalies and score_nom >= 85.0:
            return "Validated", ""
        elif any("Salaire divergent" in a for a in anomalies):
            return "Anomaly", ", ".join(anomalies)
        elif score_nom >= 70.0:
            return "Suspect", ", ".join(anomalies)
        else:
            return "Anomaly", ", ".join(anomalies)

    except Exception as e:
        return "Error", str(e)


def run_evaluation():
    print("=" * 65)
    print("  LARGE-SCALE EVALUATION - DIRECT LOCAL RUN")
    print("=" * 65)

    try:
        db_conn = get_db()
    except Exception as e:
        print(f"Erreur DB : {e}")
        return

    all_files = [f for f in os.listdir(DATASET_DIR) if os.path.isfile(os.path.join(DATASET_DIR, f))]
    samples = {}
    for cat_name, filter_fn in CATEGORIES.items():
        matching = [f for f in all_files if filter_fn(f)]
        samples[cat_name] = random.sample(matching, min(SAMPLE_SIZE, len(matching)))

    all_results = {}
    grand_total = {"Validated": 0, "Suspect": 0, "Anomaly": 0, "Error": 0, "total": 0}

    for cat_name, files in samples.items():
        cat_results = {"Validated": 0, "Suspect": 0, "Anomaly": 0, "Error": 0, "total": len(files)}
        print(f"\n  Traitement : {cat_name}")
        for i, fname in enumerate(files):
            fpath = os.path.join(DATASET_DIR, fname)
            status, reason = process_document(fpath, db_conn)
            cat_results[status] += 1
            print(f"    {i+1}/{len(files)} | {status:<10} | {fname} -> {reason}", flush=True)
            
        all_results[cat_name] = cat_results
        for k in ["Validated", "Suspect", "Anomaly", "Error"]:
            grand_total[k] += cat_results[k]
        grand_total["total"] += cat_results["total"]

    print("\n" + "=" * 65)
    print("[3/3] TABLEAU RECAPITULATIF FINAL")
    print("=" * 65)
    print(f"{'Document Type':<20} {'Sample':>7} {'Validated':>10} {'Suspect':>8} {'Anomaly':>8} {'Rate':>8}")
    print("-" * 65)
    for cat, res in all_results.items():
        rate = res["Validated"] / res["total"] * 100 if res["total"] > 0 else 0
        print(f"{cat:<20} {res['total']:>7} {res['Validated']:>10} {res['Suspect']:>8} {res['Anomaly']:>8} {rate:>7.1f}%")
    print("-" * 65)
    total_rate = grand_total["Validated"] / grand_total["total"] * 100 if grand_total["total"] > 0 else 0
    print(f"{'TOTAL':<20} {grand_total['total']:>7} {grand_total['Validated']:>10} {grand_total['Suspect']:>8} {grand_total['Anomaly']:>8} {total_rate:>7.1f}%")

if __name__ == "__main__":
    run_evaluation()

    with open('D:\PFE\data_understanding_output\eval_final.json', 'w') as f:
        json.dump(all_results, f)
