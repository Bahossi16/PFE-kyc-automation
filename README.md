# KYC Review Automation via Artificial Intelligence
### Design and Deployment of an On-Premise Platform at UIB (Société Générale Group)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PaddleOCR](https://img.shields.io/badge/OCR-PaddleOCR%20PP--OCRv3-green.svg)](https://github.com/PaddlePaddle/PaddleOCR)
[![OpenCV](https://img.shields.io/badge/Vision-OpenCV-orange.svg)](https://opencv.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-black.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Executive Summary

This repository contains the full source code and engineering assets for an **On-Premise AI-powered KYC (Know Your Customer) Review Automation Platform**, designed and deployed for **Union Internationale de Banques (UIB - Société Générale Group)**.

The platform addresses a critical operational bottleneck in periodic KYC remediation by replacing manual document inspection with an automated neuro-symbolic pipeline combining **Computer Vision (OpenCV)**, **Bilingual OCR (PaddleOCR)**, and **Fuzzy String Matching (Jaro-Winkler)**.

### 🎯 Key Performance Indicators (Evaluated on n=120 documents)
- **48.3% Global Straight-Through Processing (STP)** (86.7% on Tunisian National IDs).
- **44 seconds** average end-to-end processing time per document on standard CPU.
- **20x Speedup factor** compared to the historical 15-minute manual review.
- **100% On-Premise & Air-Gapped**, fully compliant with Tunisian banking secrecy laws and Central Bank of Tunisia (BCT) regulations.
- **Zero Software License Cost**, leveraging a robust open-source stack.

---

## 🏗️ Architecture Overview

The system is organized into a modular **3-Tier Architecture**:
1. **Presentation Layer**: Interactive Web Dashboard (HTML5, CSS3, JavaScript) featuring single/batch document upload, live execution logs, and an interactive decision cockpit.
2. **Business Logic Layer**: Python/Flask application orchestrating the 5-stage AI pipeline.
3. **Data Layer**: Relational database (MySQL) interfacing with Core Banking System (CBS) profiles and storing full audit trails.

### The 5-Stage AI Pipeline:
1. **Document Ingestion**: Accepts PDF, PNG, and JPG formats.
2. **OpenCV Preprocessing**: Cubic upscaling, Grayscale conversion, Adaptive Gaussian Thresholding (removes plastic glare), and Bilateral Filtering.
3. **Bilingual OCR Inference**: PaddleOCR PP-OCRv3 extracts bidirectional Arabic and French text blocks.
4. **Entity Extraction**: Rule-based regular expressions targeting ID numbers, names, addresses, and net salaries.
5. **Fuzzy Reconciliation**: Jaro-Winkler metric with three deterministic confidence tiers:
   - >= 85%: **Validated** (Automated Straight-Through Processing).
   - 70% - 85%: **Suspect** (Flagged for human visual inspection).
   - < 70%: **Anomaly** (Blocking rejection).

---

## 📂 Project Structure

```text
.
├── app.py                         # Main Flask application & worker queue
├── classification_documents.py     # OCR inference & targeted field extractors
├── normalisateur_phonetique.py     # Tunisian dialect phonetic normalizer
├── referentiel_postal.py          # Postal code & locality matching module
├── generate_eda_plots_en.py       # EDA data visualization generator
├── nouv_f/                        # Official Tunisian postal reference tables
├── templates/                     # Web templates (Dashboard, Login, Review)
├── static/                        # CSS, branding assets, and JS scripts
├── docs/
│   ├── assets/                    # Architecture and UML diagrams
│   └── eda_charts/                # Exploratory Data Analysis figures
├── requirements.txt               # Python package dependencies
└── README.md                      # Project documentation
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.10+
- MySQL Server (e.g., via XAMPP or native service)

### 2. Setup Environment
```bash
# Clone the repository
git clone https://github.com/Bahossi16/PFE-kyc-automation.git
cd PFE-kyc-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration
Ensure MySQL is running and update credentials in `app.py` under `DB_CONFIG`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'cbs_kyc'
}
```

### 4. Run the Application
```bash
python app.py
```
Access the application at `http://localhost:5000`.

---

## 👤 Author & Academic Supervision

- **Author**: Baha Eddine M'BARKI
- **Host Institution**: Union Internationale de Banques (UIB - Société Générale Group)
- **Academic Supervision**: IHEC Carthage / ESPRIT
