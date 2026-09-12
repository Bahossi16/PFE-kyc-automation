"""
=======================================================================
  CUSTOM FAKER PROVIDER - Données Tunisiennes (Latin/Français)
  Projet PFE : Automatisation KYC
  -----------------------------------------------------------------------
  Remplace Faker('fr_FR') par des données réalistes tunisiennes :
  - Noms/prénoms tunisiens translittérés en caractères latins
  - Adresses tunisiennes réalistes (villes, rues, codes postaux)
=======================================================================
"""
from faker.providers import BaseProvider
import random


# -----------------------------------------------------------------------
# NOMS TUNISIENS (Translittérés en latin)
# -----------------------------------------------------------------------
NOMS_TUNISIENS = [
    "BEN ALI", "TRABELSI", "GHARBI", "RIAHI", "MANSOURI",
    "CHAABANE", "HAMDI", "JEBALI", "MBAREK", "KHEMIRI",
    "ZAIDI", "MARZOUKI", "AYARI", "TURKI", "JAZIRI",
    "AMRI", "FARHAT", "GUESMI", "HAMZAOUI", "BELHAJ",
    "BEN SALAH", "DRIDI", "HAMMAMI", "HADDAD", "LABIDI",
    "MEJRI", "OUALI", "REJEB", "SAIDI", "SELMI",
    "TOUNSI", "ZOUARI", "BOUZIDI", "CHERNI", "DALY",
    "ELLOUMI", "FERCHICHI", "GHANDRI", "HAMDOUNI", "JRAD",
    "KHLIFI", "LAABIDI", "MATHLOUTHI", "NASR", "OTHMANI",
    "FERCHICHI", "BOUGHANMI", "CHAKER", "TLILI", "YOUSFI",
    "ABIDI", "BACCAR", "CHAHED", "DAOUD", "ESSEFI",
    "FAKHFAKH", "GUEDDICHE", "HAMROUNI", "IDOUDI", "JARBOUI",
    "KARRAY", "LIMAM", "MISSAOUI", "NAFFATI", "OMRI",
    "FERJANI", "BENZINA", "CHOUARI", "DIMRI", "ENNOURI",
    "FEHRI", "GARGOURI", "HACHICHA", "JALLOULI", "KAMMOUN",
    "LOUKIL", "MAKHLOUF", "NABLI", "OUESLATI", "RHOUMA",
    "SNOUSSI", "TOUATI", "BRAHIM", "CHAABOUNI", "DHAHRI",
    "ELLAFI", "FOURATI", "GHORBALI", "HADJ SALEM", "JOUINI",
    "KAROUI", "LETAIEF", "MADOURI", "NASRAOUI", "POURI",
    "SALHI", "TOUMI", "BALI", "CHATTI", "DHOUIB",
]

PRENOMS_TUNISIENS_MASCULINS = [
    "AHMED", "MOHAMED", "ALI", "OMAR", "YOUSSEF",
    "KARIM", "SAMI", "HATEM", "WALID", "RIADH",
    "HEDI", "SLIM", "IMED", "NIZAR", "FARES",
    "ANIS", "CHOKRI", "LOTFI", "MOUNIR", "RAMZI",
    "BILEL", "MEHDI", "MAHER", "ISSAM", "SOFIEN",
    "SABER", "HABIB", "TAREK", "ZIED", "KHALED",
    "WAEL", "AYMEN", "MONTASSAR", "HAZEM", "ADEL",
    "HASSEN", "MOKHTAR", "NABIL", "AMINE", "FETHI",
    "JAMEL", "KAIS", "LASMAR", "MOEZ", "NAIM",
    "OUSSAMA", "RACHID", "SALAH", "TAOUFIK", "WASSIM",
    "ABDELAZIZ", "BOUBAKER", "CHIHEB", "DHIA", "ELYES",
    "FAROUK", "GHASSEN", "HICHEM", "IYED", "JAWHER",
    "KHALIL", "LASSAD", "MAROUANE", "NIDHAL", "OUSAMA",
    "RADHOUAN", "SEIFEDDIN", "TAIEB", "YACINE", "ZEINEDDINE",
]

PRENOMS_TUNISIENS_FEMININS = [
    "FATMA", "AMINA", "SONIA", "INES", "LEILA",
    "RIMA", "NADIA", "OLFA", "SIHEM", "SALWA",
    "ASMA", "HANEN", "EMNA", "RIM", "IMEN",
    "SARRA", "SABRINE", "DORRA", "WAFA", "INSAF",
    "AMEL", "BESMA", "CHAHINEZ", "DONIA", "EYA",
    "FERIELLE", "GHOFRANE", "HAJER", "ICHRAK", "JIHENE",
    "KHAWLA", "LILIA", "MERIEM", "NARJES", "OLFA",
    "RANIA", "SOUHA", "TAKWA", "YASMINE", "ZAINEB",
    "AIDA", "BOUTHEINA", "CYRINE", "DORSAF", "EMINE",
    "FADHILA", "GHADA", "HELA", "ILHEM", "JOUIDA",
    "KHEDIJA", "LOBNA", "MANEL", "NAWRES", "OMAYMA",
    "RADHIA", "SAWSEN", "THOURAYA", "WIDED", "ZOUHOUR",
]

# -----------------------------------------------------------------------
# ADRESSES TUNISIENNES RÉALISTES
# -----------------------------------------------------------------------

# Villes tunisiennes avec codes postaux
VILLES_TUNISIENNES = [
    ("TUNIS", "1000"),
    ("ARIANA", "2080"),
    ("BEN AROUS", "2013"),
    ("LA MARSA", "2078"),
    ("SFAX", "3000"),
    ("SOUSSE", "4000"),
    ("MONASTIR", "5000"),
    ("BIZERTE", "7000"),
    ("NABEUL", "8000"),
    ("GABES", "6000"),
    ("KAIROUAN", "3100"),
    ("GAFSA", "2100"),
    ("HAMMAMET", "8050"),
    ("DJERBA", "4180"),
    ("MAHDIA", "5100"),
    ("BEJA", "9000"),
    ("JENDOUBA", "8100"),
    ("KASSERINE", "1200"),
    ("SIDI BOUZID", "9100"),
    ("TOZEUR", "2200"),
    ("KEBILI", "4200"),
    ("TATAOUINE", "3200"),
    ("MEDENINE", "4100"),
    ("SILIANA", "6100"),
    ("ZAGHOUAN", "1100"),
    ("MANOUBA", "2010"),
    ("LA GOULETTE", "2060"),
    ("CARTHAGE", "2016"),
    ("SIDI BOU SAID", "2026"),
    ("EL AOUINA", "1001"),
]

# Types de voies
TYPES_VOIES = [
    "RUE", "AVENUE", "BOULEVARD", "CITE", "IMPASSE"
]

# Noms de rues tunisiennes
NOMS_RUES = [
    "HABIB BOURGUIBA", "DE LA REPUBLIQUE", "IBN KHALDOUN",
    "DE CARTHAGE", "DU 7 NOVEMBRE", "DE L'INDEPENDENCE",
    "FARHAT HACHED", "MONGI SLIM", "BECHIR SFAR",
    "ABOU EL KACEM CHEBBI", "HEDI CHAKER", "TAHAR SFAR",
    "DE LA LIBERTE", "DU PEUPLE", "DE LA PAIX",
    "SALAH BEN YOUSSEF", "TAHAR HADDAD", "BEIT EL HIKMA",
    "DU LAC", "DES ORANGERS", "DES ROSES", "DES JASMINS",
    "MOKHTAR ATTIA", "HAFSIA", "HALFAOUINE",
    "DE FRANCE", "D'ALGERIE", "DE LIBYE",
    "ALI BACH HAMBA", "SALAH EDDINE EL AYYOUBI",
    "OKBA IBN NAFAA", "SIDI MEHREZ", "SIDI MAHROUS",
    "DE LA MEDINA", "DU BARDO", "DE L'ARIANA",
    "DE SFAX", "DE SOUSSE", "DE BIZERTE",
    "DU 20 MARS", "DU 14 JANVIER", "DU 9 AVRIL",
]


class TunisianProvider(BaseProvider):
    """Custom Faker Provider pour les données tunisiennes en latin."""

    def tunisian_last_name(self):
        """Retourne un nom de famille tunisien."""
        return self.random_element(NOMS_TUNISIENS)

    def tunisian_first_name_male(self):
        """Retourne un prénom masculin tunisien."""
        return self.random_element(PRENOMS_TUNISIENS_MASCULINS)

    def tunisian_first_name_female(self):
        """Retourne un prénom féminin tunisien."""
        return self.random_element(PRENOMS_TUNISIENS_FEMININS)

    def tunisian_first_name(self):
        """Retourne un prénom tunisien aléatoire (masculin ou féminin)."""
        if self.random_int(0, 1) == 0:
            return self.tunisian_first_name_male()
        return self.tunisian_first_name_female()

    def tunisian_full_name(self):
        """Retourne nom + prénom tunisien complet."""
        return f"{self.tunisian_last_name()} {self.tunisian_first_name()}"

    def tunisian_city(self):
        """Retourne une ville tunisienne."""
        ville, _ = self.random_element(VILLES_TUNISIENNES)
        return ville

    def tunisian_postcode(self):
        """Retourne un code postal tunisien."""
        _, code = self.random_element(VILLES_TUNISIENNES)
        return code

    def tunisian_city_with_postcode(self):
        """Retourne ville + code postal tunisien."""
        ville, code = self.random_element(VILLES_TUNISIENNES)
        return ville, code

    def tunisian_street_address(self):
        """Retourne une adresse de rue tunisienne réaliste."""
        numero = self.random_int(1, 150)
        type_voie = self.random_element(TYPES_VOIES)
        nom_rue = self.random_element(NOMS_RUES)
        return f"{numero} {type_voie} {nom_rue}"

    def tunisian_address(self):
        """Retourne une adresse complète tunisienne (rue + ville)."""
        rue = self.tunisian_street_address()
        ville, code = self.tunisian_city_with_postcode()
        return f"{rue} {code} {ville}"

    def tunisian_address_steg(self):
        """
        Format simplifié pour les factures STEG (une seule ligne courte).
        Ex: '15 RUE HABIB BOURGUIBA 1000 TUNIS'
        """
        numero = self.random_int(1, 150)
        rue = self.random_element(NOMS_RUES)
        ville, code = self.tunisian_city_with_postcode()
        return f"{numero} RUE {rue} {code} {ville}"

    def tunisian_cin(self):
        """Retourne un numéro CIN tunisien (8 chiffres)."""
        return f"{self.random_int(0, 19):02d}{self.random_int(100000, 999999)}"

    def tunisian_email(self, nom, prenom):
        """Retourne un email tunisien basé sur le nom/prénom."""
        domains = ["gmail.com", "yahoo.fr", "outlook.com", "topnet.tn", "gnet.tn"]
        nom_clean = nom.lower().replace(" ", "").replace("-", "")
        prenom_clean = prenom.lower().replace(" ", "").replace("-", "")
        domain = self.random_element(domains)
        return f"{prenom_clean}.{nom_clean}@{domain}"

    def tunisian_salary(self, niveau_risque="Faible"):
        """Retourne un salaire réaliste tunisien en dinars."""
        if niveau_risque == "Elevé":
            return round(random.uniform(3000, 8000), 3)
        elif niveau_risque == "Moyen":
            return round(random.uniform(1500, 3000), 3)
        else:
            return round(random.uniform(800, 1500), 3)


# -----------------------------------------------------------------------
# Usage facile : instanciation directe
# -----------------------------------------------------------------------
from faker import Faker as FakerBase

def get_tunisian_faker():
    """
    Retourne un objet Faker enrichi du provider tunisien.
    Usage :
        from tunisian_faker_provider import get_tunisian_faker
        fake = get_tunisian_faker()
        nom = fake.tunisian_last_name()
        adresse = fake.tunisian_address()
    """
    fake = FakerBase()
    fake.add_provider(TunisianProvider)
    return fake


# -----------------------------------------------------------------------
# Test rapide
# -----------------------------------------------------------------------
if __name__ == "__main__":
    fake = get_tunisian_faker()
    print("=== Test du Custom Provider Tunisien ===")
    for i in range(5):
        nom = fake.tunisian_last_name()
        prenom = fake.tunisian_first_name()
        adresse = fake.tunisian_address()
        adresse_steg = fake.tunisian_address_steg()
        email = fake.tunisian_email(nom, prenom)
        print(f"  Nom complet : {nom} {prenom}")
        print(f"  Adresse     : {adresse}")
        print(f"  Adresse STEG: {adresse_steg}")
        print(f"  Email       : {email}")
        print()
