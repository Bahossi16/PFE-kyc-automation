import os
import sys
import re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def charger_referentiel_postal(dossier="d:\\PFE\\nouv_f"):
    referentiel = {}
    
    # Fichier 1 : CRM_POSTAL (1).TXT
    crm_path = os.path.join(dossier, "CRM_POSTAL (1).TXT")
    if os.path.exists(crm_path):
        with open(crm_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4:
                    # Le code postal semble être le 3ème élément
                    code_postal = parts[2]
                    # Le nom de la localité est tout le reste
                    localite = " ".join(parts[3:]).strip()
                    if code_postal.isdigit() and len(code_postal) == 4:
                        referentiel[code_postal] = localite
                        
    # Fichier 2 : R_CPOSTAL.TXT
    r_cpostal_path = os.path.join(dossier, "R_CPOSTAL.TXT")
    if os.path.exists(r_cpostal_path):
        with open(r_cpostal_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if len(line) > 8:
                    # Format: 20082083CITE EL GHEZALA
                    code_postal = line[4:8]
                    localite = line[8:].strip()
                    if code_postal.isdigit() and len(code_postal) == 4:
                        referentiel[code_postal] = localite
                        
    print(f"✅ Référentiel postal chargé : {len(referentiel)} localités uniques.")
    return referentiel

def normaliser_adresse(adresse_brute, referentiel):
    """
    Normalise l'adresse en détectant d'abord le code postal, puis en cherchant le nom de la ville.
    Format de sortie : "ADRESSE NETTOYEE, VILLE (CODE POSTAL)"
    """
    if not adresse_brute:
        return ""
        
    adresse_brute_upper = adresse_brute.upper()
    
    # 1. Recherche prioritaire par nom de ville (on cherche le nom le plus long qui matche)
    meilleure_ville = None
    meilleur_code = None
    max_len = 0
    
    for code, ville in referentiel.items():
        ville_clean = ville.split(":")[0].strip()
        
        # Ignorer les mots trop courts pour éviter les faux positifs (ex: "TUN" ou "CITE")
        if len(ville_clean) > 4 and ville_clean in adresse_brute_upper:
            if len(ville_clean) > max_len:
                max_len = len(ville_clean)
                meilleure_ville = ville_clean
                meilleur_code = code
                
    if meilleure_ville:
        # Nettoyer la ville de l'adresse brute pour ne pas la répéter
        adresse_propre = re.sub(rf'\b{meilleure_ville}\b', '', adresse_brute_upper).strip()
        adresse_propre = re.sub(r'[,.\-\s]+$', '', adresse_propre).strip()
        
        if adresse_propre:
            return f"{adresse_propre}, {meilleure_ville} ({meilleur_code})"
        else:
             return f"{meilleure_ville} ({meilleur_code})"

    # 2. Fallback : Recherche par code postal (4 chiffres exacts)
    # On ne fait ça que si aucune ville n'a été trouvée (pour ne pas confondre un n° de rue avec un CP)
    codes_postaux_trouves = re.findall(r'\b\d{4}\b', adresse_brute)
    for cp in codes_postaux_trouves:
        if cp in referentiel:
            ville = referentiel[cp].split(":")[0].strip()
            
            adresse_propre = re.sub(rf'\b{cp}\b', '', adresse_brute_upper).strip()
            adresse_propre = re.sub(r'[,.\-\s]+$', '', adresse_propre).strip()
            
            if adresse_propre:
                return f"{adresse_propre}, {ville} ({cp})"
            else:
                return f"{ville} ({cp})"
             
    return adresse_brute

if __name__ == "__main__":
    ref = charger_referentiel_postal()
    
    # Tests de normalisation
    adresses_test = [
        "23 RUE HABIB BOURGUIBA 2036",
        "RUE DE LA REPUBLIQUE LA SOUKRA",
        "APPARTEMENT 5 CITE EL GHEZALA ARIANA"
    ]
    
    print("\n--- TESTS DE NORMALISATION ---")
    for addr in adresses_test:
        norm = normaliser_adresse(addr, ref)
        print(f"Original : {addr}")
        print(f"Normalisé: {norm}\n")
