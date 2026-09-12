"""
=======================================================================
  LARGE-SCALE EVALUATION SCRIPT - Phase 4 CRISP-DM
  Projet PFE : Automatisation KYC
  Description : Evaluation sur 120 documents synthetiques (30 par type)
                via l'API Flask de l'application KYC
=======================================================================
"""

import os
import sys
import json
import time
import requests
import random

# -----------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------
DATASET_DIR = r"D:\PFE\dataset_synthetique_masse"
API_URL     = "http://127.0.0.1:5000/api/upload"
SAMPLE_SIZE = 30  # 30 documents par type

# Classification des fichiers par type
CATEGORIES = {
    "CIN (Arabic)"  : lambda f: f.startswith("cin_mass"),
    "Payslip (T1)"  : lambda f: f.startswith("paie_mass") or (f.startswith("paie2_mass_exist")),
    "Payslip (T2)"  : lambda f: f.startswith("paie2_mass_new"),
    "STEG Bill"     : lambda f: f.startswith("steg_mass"),
}

# -----------------------------------------------------------------------
# Fonctions utilitaires
# -----------------------------------------------------------------------
def get_files_by_category(directory, category_filters, n=30):
    """Renvoie un echantillon aleatoire de n fichiers par categorie."""
    all_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    result = {}
    for cat_name, filter_fn in category_filters.items():
        matching = [f for f in all_files if filter_fn(f)]
        sample = random.sample(matching, min(n, len(matching)))
        result[cat_name] = sample
        print(f"  {cat_name:<18}: {len(matching):>4} fichiers disponibles | echantillon : {len(sample)}")
    return result

def call_api(filepath):
    """Envoie un fichier a l'API Flask et retourne le resultat JSON."""
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'image/jpeg')}
            resp  = requests.post(API_URL, files=files, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "TIMEOUT"}
    except requests.exceptions.ConnectionError:
        return {"error": "CONNECTION_REFUSED"}
    except Exception as e:
        return {"error": str(e)}

def classify_status(result):
    """Convertit le statut API en : Validated / Suspect / Anomaly / Error."""
    if "error" in result:
        return "Error"
    status = result.get("matching", {}).get("status", "INCONNU")
    if status == "CONFORME":
        return "Validated"
    elif "DIVERGENCE" in status:
        return "Suspect"
    elif status in ("ALERTE_NON_TROUVE", "PAS_DE_MATCH", "ERREUR_DB", "INCONNU"):
        return "Anomaly"
    elif "ALERTE" in status:
        return "Anomaly"
    else:
        return "Anomaly"

# -----------------------------------------------------------------------
# EVALUATION PRINCIPALE
# -----------------------------------------------------------------------
def run_evaluation():
    print("=" * 65)
    print("  LARGE-SCALE EVALUATION - KYC Pipeline")
    print("  Sample: 30 documents per type | Total: 120 documents")
    print("=" * 65)

    # 1. Verifier que le serveur Flask tourne
    try:
        ping = requests.get("http://127.0.0.1:5000", timeout=5)
        print("\n[OK] Serveur Flask accessible.\n")
    except Exception:
        print("\n[ERREUR] Le serveur Flask n'est pas accessible sur http://127.0.0.1:5000")
        print("Veuillez demarrer l'application avec : .\\venv\\Scripts\\python.exe app.py\n")
        sys.exit(1)

    # 2. Charger l'echantillon
    print("[1/3] Selection des fichiers...")
    samples = get_files_by_category(DATASET_DIR, CATEGORIES, n=SAMPLE_SIZE)

    # 3. Lancer l'evaluation
    print("\n[2/3] Lancement de l'evaluation (patience, ~2-4s par doc)...")
    print("-" * 65)

    all_results = {}
    grand_total = {"Validated": 0, "Suspect": 0, "Anomaly": 0, "Error": 0, "total": 0}

    for cat_name, files in samples.items():
        cat_results = {"Validated": 0, "Suspect": 0, "Anomaly": 0, "Error": 0, "total": len(files)}
        timings = []

        print(f"\n  Traitement : {cat_name}")
        for i, fname in enumerate(files):
            fpath = os.path.join(DATASET_DIR, fname)
            t0    = time.time()
            data  = call_api(fpath)
            elapsed = time.time() - t0
            timings.append(elapsed)

            verdict = classify_status(data)
            cat_results[verdict] += 1

            bar = "=" * (i + 1) + "-" * (len(files) - i - 1)
            print(f"  [{bar}] {i+1:>2}/{len(files)} | {verdict:<12} | {elapsed:.1f}s | {fname[:40]}", end="\r")

        print()  # saut de ligne apres la barre
        all_results[cat_name] = cat_results
        for k in ["Validated", "Suspect", "Anomaly", "Error"]:
            grand_total[k] += cat_results[k]
        grand_total["total"] += cat_results["total"]

        automation_rate = (cat_results["Validated"] / cat_results["total"] * 100) if cat_results["total"] > 0 else 0
        avg_time = sum(timings) / len(timings) if timings else 0
        print(f"    --> Validated: {cat_results['Validated']}  |  Suspect: {cat_results['Suspect']}  |  Anomaly: {cat_results['Anomaly']}  |  Errors: {cat_results['Error']}")
        print(f"    --> Automation Rate: {automation_rate:.1f}%  |  Avg. Processing Time: {avg_time:.1f}s/doc")

    # 4. Afficher le tableau final
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
    print("=" * 65)
    print("\nCopier ces resultats dans le tableau LaTeX (tab:large_scale_results) du Chapitre 3.")

    # 5. Sauvegarder les resultats en JSON
    output_path = r"D:\PFE\data_understanding_output\large_scale_eval_results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"summary": all_results, "grand_total": grand_total}, f, indent=2)
    print(f"\nResultats sauvegardes dans : {output_path}")

if __name__ == "__main__":
    run_evaluation()
