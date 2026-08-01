# Architecture Globale et Conceptuelle du Projet PFE KYC

Ce document détaille l'architecture logicielle, les diagrammes de conception (UML) et le flux de traitement de notre solution d'automatisation de la revue KYC.

---

## 1. Choix d'Outils de Modélisation dans Antigravity

Pour concevoir et éditer des diagrammes dans votre environnement de développement :
1.  **Mermaid (Intégré aux fichiers Markdown) [Recommandé] :** Permet de générer des diagrammes UML (Classes, Séquences, Cas d'utilisation, Architecture) directement à partir de texte. Les diagrammes s'affichent automatiquement de manière visuelle dans votre éditeur de code et dans le rapport final de PFE.
2.  **Excalidraw (Serveur MCP) :** Pour concevoir des schémas d'architecture personnalisés sous forme de croquis à main levée à l'aide des outils du MCP `excalidraw`.
3.  **Generate Image (`generate_image`) :** Pour concevoir des maquettes graphiques d'interfaces utilisateurs si nécessaire.

---

## 2. Diagramme de Cas d'Utilisation (Use Case Diagram)

Ce diagramme montre les interactions entre l'Agent Back-Office (utilisateur), le pipeline automatique et le Core Banking System (CBS).

```mermaid
flowchart LR
    subgraph Acteurs
        Agent["👤 Agent Back-Office"]
        CBS[("🏦 Core Banking System")]
        System["📁 Système de Fichiers"]
    end

    subgraph Secteur["Système de Revue KYC Automatisée"]
        UC_Ingest(["📥 Déposer les documents (Batch)"])
        UC_Run(["⚙️ Lancer la revue KYC en masse"])
        UC_OCR(["🔍 Extraire les données (OCR)"])
        UC_Clean(["🧹 Nettoyer & Structurer"])
        UC_Match(["📊 Comparer avec le CBS"])
        UC_Report(["📄 Générer le rapport d'écarts"])
        UC_Update(["💾 Mettre à jour le statut KYC"])
    end

    Agent --> UC_Ingest
    Agent --> UC_Run
    Agent --> UC_Report

    UC_Run -.->|include| UC_OCR
    UC_OCR -.->|include| UC_Clean
    UC_Clean -.->|include| UC_Match
    UC_Match -.->|include| UC_Report
    UC_Match -.->|include| UC_Update

    UC_Match --> CBS
    UC_Update --> CBS
    UC_OCR --> System
```

---

## 3. Diagramme de Séquence (Sequence Diagram)

Ce diagramme montre l'échange de messages et le flux de données chronologique entre les différents modules lors de la revue d'un dossier.

```mermaid
sequenceDiagram
    autonumber
    actor Agent as Agent Back-Office
    participant Pipeline as KYCPipeline
    participant OCR as OCRScanner
    participant Cleanser as DataCleanser
    participant DB as DatabaseManager (CBS)
    participant Matcher as SimilarityMatcher
    participant RepGen as ReportGenerator

    Agent->>Pipeline: Executer le pipeline (Dossier Images)
    Pipeline->>OCR: extract_text(image_path)
    Note over OCR: Analyse sur CPU (PaddleOCR/Tesseract)
    OCR-->>Pipeline: texte_brut (list[str])

    Pipeline->>Cleanser: clean_and_extract(texte_brut)
    Note over Cleanser: Extraction par Regex (CIN 8 chiffres, Noms, Adresses)
    Cleanser-->>Pipeline: donnees_extraites (dict)

    Pipeline->>DB: get_client_by_cin(cin_extrait)
    DB-->>Pipeline: donnees_cbs (dict)

    Pipeline->>Matcher: match_client(donnees_extraites, donnees_cbs)
    Note over Matcher: Calcul des distances (Levenshtein, Jaro-Winkler)
    Matcher-->>Pipeline: score_matching (dict : scores + decision)

    alt Match Parfait (Score >= Seuil)
        Pipeline->>DB: update_kyc_status(client_id, "VALIDÉ")
    else Écart Détecté ou Non Trouvé (Score < Seuil)
        Pipeline->>DB: update_kyc_status(client_id, "ALERTE_ÉCART")
        Pipeline->>RepGen: log_anomaly(client_id, anomalies_detectees)
    end

    Pipeline-->>Agent: Revue terminée (Génération du Rapport d'Écarts)
```

---

## 4. Diagramme de Classes (Class Diagram)

Modélisation orientée objet du code Python du MVP pour garantir sa modularité et sa maintenabilité (Clean Architecture).

```mermaid
classDiagram
    class KYCPipeline {
        -ocr_scanner: OCRScanner
        -data_cleanser: DataCleanser
        -db_manager: DatabaseManager
        -matcher: SimilarityMatcher
        -report_generator: ReportGenerator
        +run_batch(dossier_images: String) void
        +process_single_client(image_path: String) void
    }

    class OCRScanner {
        <<interface>>
        +extract_text(image_path: String)* list~String~
    }

    class PaddleOCRScanner {
        -reader: PaddleOCR
        +extract_text(image_path: String) list~String~
    }

    class TesseractOCRScanner {
        -tesseract_path: String
        +extract_text(image_path: String) list~String~
    }

    class DataCleanser {
        +clean_text(raw_lines: list~String~) list~String~
        +extract_cin(text: String) String
        +extract_name(lines: list~String~) String
        +extract_address(lines: list~String~) String
    }

    class DatabaseManager {
        -connection: MySQLConnection
        +connect() void
        +get_client_by_cin(cin: String) dict
        +update_kyc_status(client_id: String, status: String) void
        +disconnect() void
    }

    class SimilarityMatcher {
        -seuil_nom: float
        -seuil_adresse: float
        +levenshtein_distance(s1: String, s2: String) int
        +jaro_winkler_similarity(s1: String, s2: String) float
        +match_client(extracted: dict, cbs_data: dict) dict
    }

    class ReportGenerator {
        -anomalies: list~dict~
        +log_anomaly(client_id: String, details: dict) void
        +export_to_excel(output_path: String) void
    }

    OCRScanner <|.. PaddleOCRScanner : implements
    OCRScanner <|.. TesseractOCRScanner : implements
    KYCPipeline --> OCRScanner : uses
    KYCPipeline --> DataCleanser : uses
    KYCPipeline --> DatabaseManager : uses
    KYCPipeline --> SimilarityMatcher : uses
    KYCPipeline --> ReportGenerator : uses
```

---

## 5. Architecture Technique Logique (N-Tier)

La solution suit une architecture en 3 couches (On-Premise) :

1.  **Couche Présentation / Commande (Interface) :**
    *   Script en ligne de commande (`pipeline_kyc.py`) permettant de lancer les revues en lot ou à l'unité.
    *   Génération de rapports Excel/PDF finaux pour les équipes de conformité Back-Office.
2.  **Couche Métier / Traitement (Logic/Processing Layer) :**
    *   **Moteur OCR (PaddleOCR) :** Tourne sur CPU local pour extraire le texte.
    *   **Module de Cleansing (Regex) :** Extrait et structure les variables KYC tunisiennes.
    *   **Module de Matching :** Calcule les écarts de similarité de chaînes de caractères.
3.  **Couche d'Accès aux Données (Storage/Database Layer) :**
    *   **MySQL Database (Core Banking System simulé) :** Stocke les tables clients, comptes, et statuts KYC.

---

## 6. Schéma Visuel de l'Architecture Technique

Voici une représentation visuelle de l'architecture technique en 3 couches (On-Premise, optimisée CPU) conçue pour ce projet :

![Architecture Technique KYC en 3 couches](C:/Users/bahae/.gemini/antigravity/brain/e35d5f8a-4fec-411f-a99a-7f6fa81e8e12/kyc_system_architecture_1781829272735.png)
