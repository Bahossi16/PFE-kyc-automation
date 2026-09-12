import os
import datetime
import io
import uuid
import queue
import threading
import hashlib
import mysql.connector
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
import classification_documents
from classification_documents import (
    convertir_pdf_en_image, extraire_elements_ocr,
    classifier_document, EXTRACTEURS, FACTURES_TYPES
)
from normalisateur_phonetique import filtrer_phonetique_tunisienne
from referentiel_postal import charger_referentiel_postal, normaliser_adresse
from xhtml2pdf import pisa

# Initialisation de Flask
app = Flask(__name__)
app.secret_key = 'uib-kyc-dpo-secret-2025'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 Mo max (traitement en masse)
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =======================================================================
# QUEUE DE TRAITEMENT SÉQUENTIEL (évite la saturation CPU en masse)
# =======================================================================
# Chaque job est un dict :  {id, files: [...], status, results, error, total, done}
JOBS = {}   # job_id -> job_dict
JOB_LOCK = threading.Lock()
WORK_QUEUE = queue.Queue()

def _process_job(job_id):
    """Traite un batch de fichiers séquentiellement dans le thread worker."""
    with JOB_LOCK:
        job = JOBS[job_id]
        job['status'] = 'running'

    results = []
    files_info = job['files']  # liste de (file_path, original_filename)

    for idx, (file_path, original_filename) in enumerate(files_info):
        try:
            with JOB_LOCK:
                JOBS[job_id]['current'] = original_filename
                JOBS[job_id]['done'] = idx

            image_path = file_path
            if file_path.lower().endswith('.pdf'):
                image_path = convertir_pdf_en_image(file_path, output_dir=app.config['UPLOAD_FOLDER'])

            elements_geo = extraire_elements_ocr(image_path)
            if not elements_geo:
                results.append({'filename': original_filename, 'error': 'Aucun texte extrait (OCR vide).'})
                continue

            lignes = [el['text'] for el in elements_geo]
            type_doc, _ = classifier_document(lignes)
            extracteur = classification_documents.EXTRACTEURS.get(type_doc)
            extracted = {}
            if extracteur:
                if type_doc in classification_documents.FACTURES_TYPES:
                    extracted = extracteur(lignes, elements_geo=elements_geo)
                else:
                    extracted = extracteur(lignes)
            else:
                extracted = {'type': type_doc}

            extracted['_type_doc'] = type_doc
            extracted['_filename'] = os.path.basename(file_path)
            extracted['_original_filename'] = original_filename
            results.append(extracted)

        except Exception as e:
            results.append({'filename': original_filename, 'error': str(e)})

    with JOB_LOCK:
        JOBS[job_id]['status'] = 'done'
        JOBS[job_id]['results'] = results
        JOBS[job_id]['done'] = len(files_info)
        JOBS[job_id]['current'] = None


def _worker_loop():
    """Thread daemon qui vide la queue un job à la fois."""
    while True:
        job_id = WORK_QUEUE.get()
        try:
            _process_job(job_id)
        except Exception as e:
            with JOB_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]['status'] = 'error'
                    JOBS[job_id]['error'] = str(e)
        finally:
            WORK_QUEUE.task_done()


# Démarrer le worker en arrière-plan (un seul thread = traitement séquentiel)
_worker_thread = threading.Thread(target=_worker_loop, daemon=True)
_worker_thread.start()


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

# Chargement du référentiel postal UIB au démarrage (une seule fois)
REFERENTIEL_POSTAL = charger_referentiel_postal()
print(f"✅ Référentiel postal UIB chargé : {len(REFERENTIEL_POSTAL)} localités.")

# =======================================================================
# CONFIGURATION MYSQL (XAMPP)
# =======================================================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'cbs_kyc',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db():
    """Retourne une connexion MySQL fraîche, ou None si MySQL est indisponible."""
    try:
        return mysql.connector.connect(**DB_CONFIG, connection_timeout=5)
    except Exception as e:
        print(f"[AVERTISSEMENT] MySQL indisponible : {e}")
        return None


# =======================================================================
# ALGORITHMES DE SIMILARITÉ DE CHAÎNES DE CARACTÈRES
# =======================================================================

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

def string_similarity(s1, s2):
    s1 = s1.strip().upper()
    s2 = s2.strip().upper()
    if not s1 or not s2:
        return 0.0
    dist = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return (1.0 - dist / max_len) * 100

def jaro_similarity(s1, s2):
    s1_len = len(s1)
    s2_len = len(s2)
    if s1_len == 0 and s2_len == 0:
        return 1.0
    if s1_len == 0 or s2_len == 0:
        return 0.0
    match_distance = max(s1_len, s2_len) // 2 - 1
    s1_matches = [False] * s1_len
    s2_matches = [False] * s2_len
    matches = 0
    transpositions = 0
    for i in range(s1_len):
        start = max(0, i - match_distance)
        end = min(s2_len, i + match_distance + 1)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    k = 0
    for i in range(s1_len):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    return (matches / s1_len + matches / s2_len + (matches - transpositions / 2) / matches) / 3.0

def jaro_winkler_similarity(s1, s2):
    s1 = s1.strip().upper()
    s2 = s2.strip().upper()
    if not s1 or not s2:
        return 0.0
    jaro = jaro_similarity(s1, s2)
    prefix_len = 0
    for c1, c2 in zip(s1, s2):
        if c1 == c2:
            prefix_len += 1
        else:
            break
        if prefix_len == 4:
            break
    return (jaro + 0.1 * prefix_len * (1.0 - jaro)) * 100


# =======================================================================
# AUTHENTIFICATION
# =======================================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'agent_username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def superviseur_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'agent_username' not in session:
            return redirect(url_for('login'))
        if session.get('agent_role') != 'superviseur':
            return jsonify({'error': 'Accès refusé. Rôle Superviseur requis.'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'agent_username' in session:
        return redirect(url_for('home'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        if conn is None:
            error = "Base de données indisponible. Démarrez XAMPP."
        else:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM agents WHERE username = %s AND password_hash = %s AND actif = 1",
                (username, password_hash)
            )
            agent = cursor.fetchone()
            conn.close()
            if agent:
                session['agent_username'] = agent['username']
                session['agent_nom'] = agent['nom_complet']
                session['agent_role'] = agent['role']
                return redirect(url_for('home'))
            else:
                error = "Identifiant ou mot de passe incorrect."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =======================================================================
# ROUTES FLASK
# =======================================================================

@app.route('/')
@login_required
def home():
    conn = get_db()
    if conn is None:
        return render_template(
            'index.html',
            clients=[],
            stats={'valide': 0, 'expire': 0, 'alerte': 0, 'total': 0},
            logs=[],
            db_error="Base de données indisponible. Vérifiez que XAMPP/MySQL est démarré."
        )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) as n FROM clients WHERE statut_kyc IN ('Valide', 'Conforme')")
    valide = cursor.fetchone()['n']
    cursor.execute("SELECT COUNT(*) as n FROM clients WHERE date_prochaine_revue < CURDATE()")
    expire = cursor.fetchone()['n']
    cursor.execute("SELECT COUNT(*) as n FROM clients WHERE statut_kyc LIKE 'Alerte%' OR statut_kyc IN ('Anomalie', 'En Opposition')")
    alerte = cursor.fetchone()['n']

    cursor.execute(
        "SELECT l.*, c.nom, c.prenom "
        "FROM kyc_logs l "
        "LEFT JOIN clients c ON l.client_id = c.client_id "
        "ORDER BY l.log_id DESC LIMIT 5"
    )
    logs = cursor.fetchall()
    conn.close()

    return render_template(
        'index.html',
        clients=clients,
        stats={'valide': valide, 'expire': expire, 'alerte': alerte, 'total': len(clients)},
        logs=logs,
        agent_nom=session.get('agent_nom', 'Agent'),
        agent_role=session.get('agent_role', 'agent')
    )

@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    conn.close()
    return jsonify(clients)

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni.'}), 400

    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné.'}), 400

    # -------------------------------------------------------
    # PHASE 1 : Traiter chaque fichier individuellement
    # -------------------------------------------------------
    resultats_docs = []  # Liste des données extraites par doc
    for file in files:
        try:
            # Sécuriser le nom du fichier (quand on upload un dossier, file.filename contient le chemin)
            safe_filename = os.path.basename(file.filename)
            filename = f"doc_{int(datetime.datetime.now().timestamp())}_{safe_filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            image_path = file_path
            if file_path.lower().endswith('.pdf'):
                try:
                    image_path = convertir_pdf_en_image(file_path, output_dir=app.config['UPLOAD_FOLDER'])
                except Exception as e:
                    return jsonify({'error': f"Impossible de convertir le PDF : {str(e)}"}), 422

            elements_geo = extraire_elements_ocr(image_path)
            if not elements_geo:
                return jsonify({'error': f"Échec OCR sur {file.filename}. Aucun texte extrait."}), 422

            lignes = [el['text'] for el in elements_geo]
            type_doc, scores = classifier_document(lignes)

            extracteur = classification_documents.EXTRACTEURS.get(type_doc)
            extracted_data = {}
            if extracteur:
                if type_doc in classification_documents.FACTURES_TYPES:
                    extracted_data = extracteur(lignes, elements_geo=elements_geo)
                else:
                    extracted_data = extracteur(lignes)
            else:
                extracted_data = {'type': type_doc, 'raw_text': " ".join(lignes)}

            extracted_data['_type_doc'] = type_doc
            extracted_data['_filename'] = filename
            extracted_data['_raw_lines'] = lignes
            resultats_docs.append(extracted_data)

        except Exception as e:
            return jsonify({'error': f"Erreur de traitement ({file.filename}) : {str(e)}"}), 500

    # -------------------------------------------------------
    # PHASE 2 : Sélectionner le document "principal"
    # (Priorité: CIN > PASSEPORT > FICHE_DE_PAIE > FACTURE_*)
    # -------------------------------------------------------
    PRIORITE = ['CIN', 'PASSEPORT', 'FICHE_DE_PAIE', 'FACTURE_STEG', 'FACTURE_SONEDE', 'FACTURE_TELECOM']
    doc_principal = None
    doc_secondaire = None

    for p in PRIORITE:
        for d in resultats_docs:
            if d['_type_doc'] == p:
                if doc_principal is None:
                    doc_principal = d
                elif doc_secondaire is None:
                    doc_secondaire = d
                break
        if doc_principal and doc_secondaire:
            break
    if doc_principal is None:
        doc_principal = resultats_docs[0]
    if doc_secondaire is None and len(resultats_docs) > 1:
        doc_secondaire = next((d for d in resultats_docs if d is not doc_principal), None)

    extracted_data = doc_principal
    type_doc = doc_principal['_type_doc']

    # -------------------------------------------------------
    # PHASE 3 : Normalisation phonétique de l'adresse
    # -------------------------------------------------------
    adresse_ocr_brute = extracted_data.get('adresse', '') or ''
    adresse_normalisee = ""
    if adresse_ocr_brute:
        adresse_phonetique = filtrer_phonetique_tunisienne(adresse_ocr_brute)
        adresse_normalisee = normaliser_adresse(adresse_phonetique, REFERENTIEL_POSTAL)
        extracted_data['adresse_normalisee'] = adresse_normalisee
        extracted_data['adresse_phonetique'] = adresse_phonetique

    # -------------------------------------------------------
    # PHASE 4 : Recherche du client dans la base CBS
    # -------------------------------------------------------
    conn = get_db()
    if conn is None:
        return jsonify({
            'extracted': extracted_data,
            'type': type_doc,
            'matching': {
                'status': 'ERREUR_DB',
                'scores': {},
                'cbs_client': None,
                'anomalies': ["Base de données MySQL indisponible. Démarrez XAMPP."],
                'cross_check': None,
            },
            'filename': extracted_data['_filename'],
            'nb_docs': len(resultats_docs),
            'db_error': True
        })
    cursor = conn.cursor(dictionary=True)

    db_client = None
    cin_found = extracted_data.get('cin')
    nom_part = (extracted_data.get('nom') or extracted_data.get('nom_abonne') or "")
    prenom_part = extracted_data.get('prenom') or ""
    nom_found = f"{nom_part} {prenom_part}".strip()

    nom_clean = nom_found.upper()
    for prefix in ["MR ", "MME ", "M ", "STE ", "RES "]:
        if nom_clean.startswith(prefix):
            nom_clean = nom_clean[len(prefix):]

    if cin_found:
        cursor.execute("SELECT * FROM clients WHERE cin = %s", (cin_found,))
        db_client = cursor.fetchone()

    if not db_client and nom_clean:
        cursor.execute("SELECT * FROM clients")
        all_clients = cursor.fetchall()
        best_score = 0
        best_match = None
        for client in all_clients:
            nom_cbs = f"{client['nom']} {client['prenom']}".strip().upper()
            score = jaro_winkler_similarity(nom_clean, nom_cbs)
            if score > best_score and score >= 55:
                best_score = score
                best_match = client
        db_client = best_match

    # -------------------------------------------------------
    # PHASE 5 : Croisement multi-documents (si dossier complet)
    # -------------------------------------------------------
    cross_check = None
    if doc_secondaire is not None and db_client is not None and doc_secondaire.get('_type_doc') != 'INCONNU':
        import re
        nom_cbs_ref_fr = f"{db_client['nom']} {db_client['prenom']}".strip().upper()
        nom_cbs_ref_ar = f"{db_client.get('nom_ar', '')} {db_client.get('prenom_ar', '')}".strip()
        
        # Extraire toutes les valeurs brutes du doc secondaire pour un croisement robuste
        textes_doc2 = [l.strip().upper() for l in doc_secondaire.get('_raw_lines', []) if len(l.strip()) > 2]

        best_cross = 0
        best_bloc = ""
        nom_recherche_final = nom_cbs_ref_fr
        
        for bloc in textes_doc2:
            # Supprimer les préfixes de politesse
            for prefix in ["MR ", "MME ", "M. ", "M "]:
                if bloc.startswith(prefix):
                    bloc = bloc[len(prefix):]
            
            # Choix de la langue pour la comparaison
            if re.search(r'[\u0600-\u06FF]', bloc) and len(nom_cbs_ref_ar) > 1:
                nom_cbs_ref = nom_cbs_ref_ar
            else:
                nom_cbs_ref = nom_cbs_ref_fr
                
            nom_cbs_sorted = " ".join(sorted(nom_cbs_ref.split()))

            # Comparaison directe
            score = jaro_winkler_similarity(bloc, nom_cbs_ref)
            # Comparaison token-sorted (résout les noms à l'ordre inversé)
            bloc_sorted = " ".join(sorted(bloc.split()))
            score_sorted = jaro_winkler_similarity(bloc_sorted, nom_cbs_sorted)
            score = max(score, score_sorted)
            
            if score > best_cross:
                best_cross = score
                best_bloc = bloc
                nom_recherche_final = nom_cbs_ref

        cross_check = {
            'type_doc2': doc_secondaire['_type_doc'],
            'nom_recherche': nom_recherche_final,
            'meilleur_bloc_trouve': best_bloc,
            'score_coherence': round(best_cross, 1),
            'coherent': best_cross >= 70.0,
            'salaire_match': None
        }

        # Vérification optionnelle du salaire
        if doc_secondaire['_type_doc'] == 'FICHE_DE_PAIE' and doc_secondaire.get('salaire_net') and db_client.get('salaire'):
            try:
                sal_doc_str = str(doc_secondaire['salaire_net']).strip().replace(' ', '').replace(',', '.')
                # Gérer le cas "2.500" qui peut signifier 2500 (format tunisien avec . comme séparateur des milliers)
                # Si le nombre est < 10000 avec un point, c'est un séparateur décimal sinon de milliers
                if sal_doc_str.count('.') == 1:
                    parts = sal_doc_str.split('.')
                    if len(parts[1]) == 3:  # ex: 2.500 → 2500
                        sal_doc_str = parts[0] + parts[1]
                sal_doc = float(sal_doc_str)
                sal_cbs = float(db_client['salaire'])
                
                diff_pct = abs(sal_doc - sal_cbs) / max(sal_cbs, 1) * 100
                if diff_pct < 2:   # Tolérance 2% (arrondis)
                    salaire_score = 100.0
                elif diff_pct < 10:  # Tolérance 10%
                    salaire_score = 80.0
                else:
                    salaire_score = 30.0
                
                cross_check['salaire_match'] = {
                    'salaire_doc': doc_secondaire['salaire_net'],
                    'salaire_cbs': float(db_client['salaire']),
                    'score': salaire_score
                }
                
                if salaire_score < 70.0:
                    cross_check['coherent'] = False
            except (ValueError, TypeError):
                pass


    # -------------------------------------------------------
    # PHASE 6 : Évaluation de conformité finale
    # -------------------------------------------------------
    matching_results = {
        'status': 'PAS_DE_MATCH',
        'scores': {},
        'cbs_client': None,
        'anomalies': [],
        'cross_check': cross_check,
        'adresse_pipeline': {
            'ocr_brute': adresse_ocr_brute,
            'apres_phonetique': extracted_data.get('adresse_phonetique', ''),
            'normalisee': adresse_normalisee
        }
    }
    new_statut_kyc = 'Normal'
    client_id = None

    if db_client:
        client_id = db_client['client_id']
        matching_results['cbs_client'] = db_client

        import re
        nom_extrait = nom_clean
        
        # --- Intelligence Bilingue ---
        # Si le texte extrait contient des lettres arabes ET que le CBS possède les noms arabes
        if re.search(r'[\u0600-\u06FF]', nom_extrait) and db_client.get('nom_ar'):
            nom_cbs = f"{db_client['nom_ar']} {db_client['prenom_ar']}".strip()
        else:
            # Par défaut : comparaison en français/latin
            nom_cbs = f"{db_client['nom']} {db_client['prenom']}".strip().upper()

        # Comparaison directe
        score_nom = jaro_winkler_similarity(nom_extrait, nom_cbs)
        
        # Comparaison token-sorted (gère les noms à l'ordre inversé)
        nom_extrait_sorted = " ".join(sorted(nom_extrait.split()))
        nom_cbs_sorted = " ".join(sorted(nom_cbs.split()))
        score_nom_sorted = jaro_winkler_similarity(nom_extrait_sorted, nom_cbs_sorted)
        
        score_nom = max(score_nom, score_nom_sorted)

        matching_results['scores']['nom'] = round(score_nom, 1)


        score_adresse = 100.0
        if type_doc in FACTURES_TYPES and adresse_ocr_brute:
            adresse_cbs = db_client['adresse'].upper().strip()
            
            score_brut = jaro_winkler_similarity(adresse_ocr_brute.upper().strip(), adresse_cbs)
            score_norm = jaro_winkler_similarity(adresse_normalisee, adresse_cbs) if adresse_normalisee else 0.0
            
            score_adresse = max(score_brut, score_norm)
            matching_results['scores']['adresse'] = round(score_adresse, 1)

        # Score de cohérence inter-documents
        if cross_check:
            matching_results['scores']['coherence_dossier'] = cross_check['score_coherence']

        anomalies = []
        if type_doc == 'CIN' and cin_found and cin_found != db_client['cin']:
            anomalies.append("Numéro CIN divergent.")
        if score_nom < 75.0:
            anomalies.append(f"Nom divergent (Similarité : {score_nom:.1f}%).")
        if score_adresse < 70.0 and type_doc in FACTURES_TYPES:
            anomalies.append(f"Adresse de facturation divergente (Similarité : {score_adresse:.1f}%).")
        if cross_check and not cross_check['coherent'] and cross_check['score_coherence'] < 70.0:
            anomalies.append(f"Incohérence du nom entre les documents (Score : {cross_check['score_coherence']:.1f}%).")
        if cross_check and cross_check.get('salaire_match') and cross_check['salaire_match']['score'] < 70.0:
            anomalies.append(f"Salaire divergent (Fiche: {cross_check['salaire_match']['salaire_doc']} vs CBS: {cross_check['salaire_match']['salaire_cbs']}).")
        
        # Vérification du salaire si le document principal est une fiche de paie
        if type_doc == 'FICHE_DE_PAIE' and extracted_data.get('salaire_net') and db_client.get('salaire'):
            try:
                sal_doc_str = str(extracted_data['salaire_net']).strip().replace(' ', '').replace(',', '.')
                sal_doc = float(sal_doc_str)
                sal_cbs = float(db_client['salaire'])
                if abs(sal_doc - sal_cbs) > 10.0:
                    anomalies.append(f"Salaire divergent (Fiche: {sal_doc} DT vs CBS: {sal_cbs} DT).")
            except ValueError:
                anomalies.append(f"Impossible de vérifier le salaire (Format invalide: {extracted_data['salaire_net']}).")

        matching_results['anomalies'] = anomalies

        if not anomalies and score_nom >= 85.0:
            # Vérifier aussi la cohérence du dossier si multi-doc
            if cross_check and not cross_check['coherent']:
                matching_results['status'] = 'ALERTE_INCOHERENCE_DOSSIER'
                new_statut_kyc = 'Alerte Incoherence'
            else:
                matching_results['status'] = 'CONFORME'
                new_statut_kyc = 'Conforme'
                niveau = db_client.get('niveau_risque', 'Faible')
                annees_plus = 1 if niveau == 'Elevé' else 7
                try:
                    new_prochaine_revue = datetime.date.today().replace(year=datetime.date.today().year + annees_plus)
                except ValueError:
                    new_prochaine_revue = datetime.date.today() + datetime.timedelta(days=365*annees_plus)
                cursor.execute(
                    "UPDATE clients SET statut_kyc = %s, date_derniere_revue = %s, date_prochaine_revue = %s WHERE client_id = %s",
                    (new_statut_kyc, datetime.date.today().isoformat(), new_prochaine_revue.isoformat(), client_id)
                )
        else:
            if any("Salaire divergent" in a for a in anomalies):
                matching_results['status'] = 'NON_CONFORME'
                new_statut_kyc = 'Non Conforme'
            elif score_nom >= 70.0:
                matching_results['status'] = 'DIVERGENCE_MINEURE'
                new_statut_kyc = 'Divergence Mineure'
            else:
                matching_results['status'] = 'ALERTE_ECART'
                new_statut_kyc = 'Alerte Ecart'
            cursor.execute(
                "UPDATE clients SET statut_kyc = %s WHERE client_id = %s",
                (new_statut_kyc, client_id)
            )
    else:
        matching_results['status'] = 'ALERTE_NON_TROUVE'
        matching_results['anomalies'] = ["Client introuvable dans le Core Banking System."]
        new_statut_kyc = 'Alerte Non Trouve'

    details_log = f"Extraction: {str(extracted_data)} | Anomalies: {', '.join(matching_results['anomalies'])}"
    cursor.execute(
        "INSERT INTO kyc_logs (client_id, date_revue, document_analyse, statut_resultat, details_anomalies) "
        "VALUES (%s, %s, %s, %s, %s)",
        (client_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), type_doc,
         matching_results['status'], details_log)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'extracted': extracted_data,
        'type': type_doc,
        'matching': matching_results,
        'filename': extracted_data['_filename'],
        'nb_docs': len(resultats_docs)
    })



# =======================================================================
# NOUVELLES ROUTES METIER KYC
# =======================================================================

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM clients")
    total_clients = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as overdue FROM clients WHERE date_prochaine_revue < CURDATE()")
    overdue_clients = cursor.fetchone()['overdue']
    cursor.execute("SELECT statut_kyc, COUNT(*) as count FROM clients GROUP BY statut_kyc")
    statuts = cursor.fetchall()
    conn.close()
    return jsonify({'total': total_clients, 'overdue': overdue_clients, 'statuts': statuts})

@app.route('/api/action/opposition/<client_id>', methods=['POST'])
def mise_en_opposition(client_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET statut_kyc = 'En Opposition' WHERE client_id = %s", (client_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Client mis en opposition KYC.'})

@app.route('/api/generate_pdf/<type_doc>/<client_id>', methods=['GET'])
def generate_pdf(type_doc, client_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients WHERE client_id = %s", (client_id,))
    client = cursor.fetchone()
    conn.close()
    if not client:
        return "Client introuvable", 404
    html = ""
    if type_doc == "relance":
        html = f"""
        <html>
        <head><style>body {{ font-family: Helvetica; font-size: 12pt; line-height: 1.5; }}</style></head>
        <body>
            <div style="text-align: right;">Tunis, le {datetime.date.today().strftime('%d/%m/%Y')}</div>
            <h2>Union Internationale de Banques (UIB)</h2>
            <p><strong>A l'attention de :</strong> {client['prenom']} {client['nom']}</p>
            <p><strong>Adresse :</strong> {client['adresse']}</p>
            <hr>
            <h3>Objet : 1ere Relance - Mise a jour de votre dossier KYC</h3>
            <p>Madame, Monsieur,</p>
            <p>Dans le cadre de nos obligations reglementaires (Circulaire BCT et politique interne UIB), nous sommes tenus de maintenir a jour la connaissance de nos clients.</p>
            <p>Nous avons constate que votre dossier necessite une actualisation. Afin d'eviter la mise en opposition de votre compte dans un delai de 15 jours, nous vous prions de bien vouloir vous presenter a votre agence muni de vos justificatifs d'identite recents.</p>
            <p>Comptant sur votre comprehension,<br>La Direction.</p>
        </body>
        </html>
        """
    elif type_doc == "checklist":
        html = f"""
        <html>
        <head><style>body {{ font-family: Helvetica; font-size: 11pt; }} table {{ width: 100%; border-collapse: collapse; margin-top:20px; }} td, th {{ border: 1px solid black; padding: 8px; text-align:left; }}</style></head>
        <body>
            <h2>Compte Rendu de Revue KYC - CERTIFICATION</h2>
            <p><strong>ID Client :</strong> {client['client_id']}</p>
            <p><strong>Nom & Prenom :</strong> {client['nom']} {client['prenom']}</p>
            <p><strong>Niveau de Risque :</strong> {client.get('niveau_risque', 'Faible')}</p>
            <p><strong>Prochaine Revue Prevue :</strong> {client.get('date_prochaine_revue', 'Non definie')}</p>
            <table>
                <tr><th>Point de controle</th><th>Statut de Conformite OCR</th></tr>
                <tr><td>Piece d'identite</td><td>Validee par l'Intelligence Artificielle</td></tr>
                <tr><td>Rapprochement CBS</td><td>Conforme (>85% de similarite)</td></tr>
            </table>
            <br><br><br>
            <p>Signature de l'analyste / gestionnaire : _________________________</p>
        </body>
        </html>
        """
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    if pisa_status.err:
        return "Erreur lors de la generation du PDF", 500
    pdf_buffer.seek(0)
    return send_file(pdf_buffer, as_attachment=True,
                     download_name=f"{type_doc}_{client['client_id']}.pdf",
                     mimetype='application/pdf')


# =======================================================================
# ROUTES : TRAITEMENT EN MASSE (Batch asynchrone séquentiel)
# =======================================================================

@app.route('/api/batch_upload', methods=['POST'])
def batch_upload():
    """
    Reçoit N fichiers, les enregistre, crée un job et le met en queue.
    Retourne immédiatement avec le job_id pour suivre la progression.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni.'}), 400

    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné.'}), 400

    job_id = str(uuid.uuid4())
    saved_files = []

    for file in files:
        safe_name = os.path.basename(file.filename)
        fname = f"batch_{job_id[:8]}_{int(datetime.datetime.now().timestamp())}_{safe_name}"
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(fpath)
        saved_files.append((fpath, safe_name))

    with JOB_LOCK:
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',   # pending | running | done | error
            'files': saved_files,
            'total': len(saved_files),
            'done': 0,
            'current': None,
            'results': [],
            'error': None
        }

    WORK_QUEUE.put(job_id)
    return jsonify({'job_id': job_id, 'total': len(saved_files), 'status': 'pending'})


@app.route('/api/batch_status/<job_id>', methods=['GET'])
def batch_status(job_id):
    """
    Retourne l'état d'avancement du job.
    Quand status == 'done', retourne aussi les résultats.
    """
    with JOB_LOCK:
        job = JOBS.get(job_id)

    if not job:
        return jsonify({'error': 'Job introuvable.'}), 404

    response = {
        'job_id': job_id,
        'status': job['status'],
        'total': job['total'],
        'done': job['done'],
        'current': job['current'],
    }
    if job['status'] == 'done':
        response['results'] = job['results']
    if job['status'] == 'error':
        response['error'] = job['error']
    return jsonify(response)


if __name__ == '__main__':
    print("Application Flask démarrée — Base : MySQL XAMPP (cbs_kyc)")
    print("Accès : http://127.0.0.1:5000")
    app.run(debug=False, port=5000)
