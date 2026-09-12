"""
=======================================================================
  BENCHMARK FINAL : Temps de traitement + Precision du matching
  Projet PFE : Automatisation KYC - UIB
=======================================================================
"""
import os, sys, time, random, re, statistics
import mysql.connector
from classification_documents import (
    extraire_elements_ocr, classifier_document,
    EXTRACTEURS, FACTURES_TYPES, convertir_pdf_en_image
)
from normalisateur_phonetique import filtrer_phonetique_tunisienne
from referentiel_postal import charger_referentiel_postal, normaliser_adresse

DATASET_DIR = r"D:\PFE\dataset_synthetique_masse"
SAMPLE_PER_TYPE = 5   # 5 documents par type = 20 au total (rapide)

DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '',
    'database': 'cbs_kyc', 'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}
REFERENTIEL_POSTAL = charger_referentiel_postal()

CATEGORIES = {
    "CIN (Arabe)"  : lambda f: f.startswith("cin_mass"),
    "Fiche Paie T1": lambda f: f.startswith("paie_mass"),
    "Fiche Paie T2": lambda f: f.startswith("paie2_mass"),
    "Facture STEG" : lambda f: f.startswith("steg_mass"),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def jaro_sim(s1, s2):
    s1_len, s2_len = len(s1), len(s2)
    if s1_len == 0 and s2_len == 0: return 1.0
    if s1_len == 0 or s2_len == 0: return 0.0
    md = max(s1_len, s2_len) // 2 - 1
    s1m, s2m = [False]*s1_len, [False]*s2_len
    matches = trans = 0
    for i in range(s1_len):
        for j in range(max(0,i-md), min(s2_len,i+md+1)):
            if s2m[j] or s1[i] != s2[j]: continue
            s1m[i] = s2m[j] = True; matches += 1; break
    if matches == 0: return 0.0
    k = 0
    for i in range(s1_len):
        if not s1m[i]: continue
        while not s2m[k]: k += 1
        if s1[i] != s2[k]: trans += 1
        k += 1
    return (matches/s1_len + matches/s2_len + (matches - trans/2)/matches) / 3.0

def jw(s1, s2):
    s1, s2 = s1.strip().upper(), s2.strip().upper()
    if not s1 or not s2: return 0.0
    j = jaro_sim(s1, s2)
    p = sum(1 for a,b in zip(s1,s2) if a==b and list(s1).index(a) < 4)
    p = min(p, 4)
    return (j + 0.1*p*(1-j)) * 100

def process(image_path, db_conn):
    elements_geo = extraire_elements_ocr(image_path)
    if not elements_geo:
        return None, None, "OCR vide", 0.0
    lignes = [el['text'] for el in elements_geo]
    type_doc, _ = classifier_document(lignes)
    extracteur = EXTRACTEURS.get(type_doc)
    if not extracteur:
        return None, None, "Type inconnu", 0.0
    extracted = extracteur(lignes, elements_geo=elements_geo) if type_doc in FACTURES_TYPES else extracteur(lignes)
    cin_found = extracted.get('cin')
    nom_clean = (extracted.get('nom','') or '').strip().upper()
    cursor = db_conn.cursor(dictionary=True)
    db_client = None
    if cin_found:
        cursor.execute("SELECT * FROM clients WHERE cin = %s", (cin_found,))
        db_client = cursor.fetchone()
    if not db_client and nom_clean:
        cursor.execute("SELECT * FROM clients")
        best, bm = 0, None
        for c in cursor.fetchall():
            s = jw(nom_clean, f"{c['nom']} {c['prenom']}".upper())
            if s > best and s >= 55: best, bm = s, c
        db_client = bm
    if not db_client:
        return type_doc, None, "Client introuvable", 0.0
    nom_cbs = f"{db_client['nom']} {db_client['prenom']}".upper()
    score = jw(nom_clean, nom_cbs)
    status = "Conforme" if score >= 85 else ("Divergence Mineure" if score >= 70 else "Alerte")
    return type_doc, db_client, status, score

def run():
    print("="*65)
    print("  BENCHMARK FINAL : Precision + Temps de traitement")
    print("="*65)
    try:
        db_conn = get_db()
        print("  Base MySQL : Connexion OK\n")
    except Exception as e:
        print(f"ERREUR DB : {e}"); return

    all_files = [f for f in os.listdir(DATASET_DIR) if os.path.isfile(os.path.join(DATASET_DIR, f))]
    samples = {}
    for cat, fn in CATEGORIES.items():
        matching = [f for f in all_files if fn(f)]
        samples[cat] = random.sample(matching, min(SAMPLE_PER_TYPE, len(matching)))

    total_times = []
    summary = {}

    for cat, files in samples.items():
        print(f"--- {cat} ({len(files)} docs) ---")
        res = {"Conforme":0, "Divergence Mineure":0, "Alerte":0, "Erreur":0, "temps":[]}
        for fname in files:
            fpath = os.path.join(DATASET_DIR, fname)
            t0 = time.time()
            try:
                type_doc, client, status, score = process(fpath, db_conn)
                elapsed = time.time() - t0
                res[status] += 1
                res["temps"].append(elapsed)
                total_times.append(elapsed)
                client_str = f"{client['nom']} {client['prenom']}" if client else "NON TROUVE"
                print(f"  {fname[:35]:<35} | {status:<20} | {score:5.1f}% | {elapsed:.1f}s")
            except Exception as e:
                elapsed = time.time() - t0
                res["Erreur"] += 1
                print(f"  {fname[:35]:<35} | ERREUR               | {str(e)[:30]}")
        summary[cat] = res
        moy = statistics.mean(res["temps"]) if res["temps"] else 0
        print(f"  Temps moyen : {moy:.1f}s\n")

    print("="*65)
    print("  RESULTATS GLOBAUX")
    print("="*65)
    print(f"{'Type':<20} {'Docs':>5} {'Conforme':>9} {'Div.Min':>8} {'Alerte':>7} {'Taux%':>7} {'Moy(s)':>7}")
    print("-"*65)
    grand = {"Conforme":0,"Divergence Mineure":0,"Alerte":0,"Erreur":0,"n":0}
    for cat, r in summary.items():
        n = len(samples[cat])
        rate = r["Conforme"]/n*100 if n else 0
        moy = statistics.mean(r["temps"]) if r["temps"] else 0
        print(f"{cat:<20} {n:>5} {r['Conforme']:>9} {r['Divergence Mineure']:>8} {r['Alerte']:>7} {rate:>6.1f}% {moy:>6.1f}s")
        for k in ["Conforme","Divergence Mineure","Alerte"]: grand[k]+=r[k]
        grand["n"]+=n
    print("-"*65)
    total_rate = grand["Conforme"]/grand["n"]*100 if grand["n"] else 0
    moy_tot = statistics.mean(total_times) if total_times else 0
    print(f"{'TOTAL':<20} {grand['n']:>5} {grand['Conforme']:>9} {grand['Divergence Mineure']:>8} {grand['Alerte']:>7} {total_rate:>6.1f}% {moy_tot:>6.1f}s")
    print()
    print(f"  Temps MIN    : {min(total_times):.1f}s")
    print(f"  Temps MAX    : {max(total_times):.1f}s")
    print(f"  Temps MOYEN  : {moy_tot:.1f}s")
    print(f"  Taux Conforme global : {total_rate:.1f}%")
    print("="*65)
    db_conn.close()

if __name__ == "__main__":
    run()
