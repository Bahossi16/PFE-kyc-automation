import re

def filtrer_phonetique_tunisienne(adresse_brute):
    """
    Traduit les variations orthographiques de l'adresse brute extraite par l'OCR 
    vers l'orthographe standard utilisée par le Core Banking System (CBS) de l'UIB.
    """
    if not adresse_brute:
        return ""
        
    adresse_nettoyee = adresse_brute.upper()
    
    # Dictionnaire des synonymes et variations phonétiques
    # Format: "MOT_A_REMPLACER": "MOT_OFFICIEL_CBS"
    synonymes = {
        r"\bDJEBEL\b": "JBEL",
        r"\bDJELLOUD\b": "JLOUD",
        r"\bSIDI\b": "SDI",
        r"\bCITE\b": "CT",
        r"\bBOU\b": "ABOU" # Exemple hypothétique si la banque utilise ABOU
    }
    
    # Remplacement via expressions régulières pour cibler des mots exacts (\b)
    for motif, remplacement in synonymes.items():
        adresse_nettoyee = re.sub(motif, remplacement, adresse_nettoyee)
        
    # Nettoyage des doubles espaces et caractères inutiles
    adresse_nettoyee = re.sub(r"[,;:\.]", " ", adresse_nettoyee)
    adresse_nettoyee = re.sub(r"\s+", " ", adresse_nettoyee).strip()
    
    return adresse_nettoyee

if __name__ == "__main__":
    # Test
    test_str = "7 BIS R 9062 RDC, DJEBEL DJELLOUD"
    print(f"Original  : {test_str}")
    print(f"Phonétique: {filtrer_phonetique_tunisienne(test_str)}")
