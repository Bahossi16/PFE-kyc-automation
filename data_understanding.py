"""
=======================================================================
  DATA UNDERSTANDING - Phase 2 CRISP-DM
  Projet PFE : Automatisation KYC
  Description : Analyse complète du jeu de données synthétique généré
=======================================================================
"""

import os
import re
import math
import datetime
from collections import Counter

import matplotlib
matplotlib.use('Agg')  # Pas besoin d'affichage graphique
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import numpy as np
import mysql.connector
from PIL import Image

# -----------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------
DATASET_DIR   = r"D:\PFE\dataset_synthetique_masse"
DATA_DIR      = r"D:\PFE\data"
OUTPUT_DIR    = r"D:\PFE\data_understanding_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DB_CONFIG = dict(host='localhost', user='root', password='', database='cbs_kyc')

# Couleurs cohérentes pour tout le rapport
COLORS = {
    'cin'   : '#4E79A7',
    'paie1' : '#F28E2B',
    'paie2' : '#E15759',
    'steg'  : '#76B7B2',
    'grid'  : '#F0F0F0',
    'text'  : '#333333',
}

# -----------------------------------------------------------------------
# 1. ANALYSE DU DOSSIER : Compter les documents par type
# -----------------------------------------------------------------------
def analyse_dossier(directory):
    """Classifie chaque fichier du dossier par type de document."""
    counts = {'CIN': 0, 'Fiche de Paie (T1)': 0, 'Fiche de Paie (T2)': 0, 'Facture STEG': 0}
    tailles_ko = {'CIN': [], 'Fiche de Paie (T1)': [], 'Fiche de Paie (T2)': [], 'Facture STEG': []}
    dims = {'CIN': [], 'Fiche de Paie (T1)': [], 'Fiche de Paie (T2)': [], 'Facture STEG': []}

    if not os.path.isdir(directory):
        print(f"[ERREUR] Dossier introuvable : {directory}")
        return counts, tailles_ko, dims

    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue

        size_ko = os.path.getsize(fpath) / 1024

        if fname.startswith('cin_mass'):
            key = 'CIN'
        elif fname.startswith('paie_mass') or fname.startswith('paie2_mass_exist'):
            key = 'Fiche de Paie (T1)'
        elif fname.startswith('paie2_mass_new'):
            key = 'Fiche de Paie (T2)'
        elif fname.startswith('steg_mass'):
            key = 'Facture STEG'
        else:
            continue

        counts[key] += 1
        tailles_ko[key].append(size_ko)

        try:
            with Image.open(fpath) as img:
                dims[key].append(img.size)
        except Exception:
            pass

    return counts, tailles_ko, dims

# -----------------------------------------------------------------------
# 2. ANALYSE DE LA BASE DE DONNÉES
# -----------------------------------------------------------------------
def analyse_db():
    """Interroge MySQL pour obtenir des stats sur les clients."""
    stats = {}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as total FROM clients")
        stats['total_clients'] = cursor.fetchone()['total']

        cursor.execute("SELECT niveau_risque, COUNT(*) as nb FROM clients GROUP BY niveau_risque")
        stats['risque'] = {r['niveau_risque']: r['nb'] for r in cursor.fetchall()}

        cursor.execute("SELECT statut_kyc, COUNT(*) as nb FROM clients GROUP BY statut_kyc")
        stats['statut'] = {r['statut_kyc']: r['nb'] for r in cursor.fetchall()}

        cursor.execute("SELECT MIN(salaire) as min_s, MAX(salaire) as max_s, AVG(salaire) as avg_s FROM clients")
        sal = cursor.fetchone()
        stats['salaire'] = {
            'min': float(sal['min_s'] or 0),
            'max': float(sal['max_s'] or 0),
            'avg': float(sal['avg_s'] or 0),
        }

        cursor.execute("""
            SELECT salaire FROM clients WHERE salaire IS NOT NULL
        """)
        stats['salaires_list'] = [float(r['salaire']) for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as nb FROM clients WHERE nom_ar IS NOT NULL AND nom_ar != ''")
        stats['bilingues'] = cursor.fetchone()['nb']

        conn.close()
    except Exception as e:
        print(f"[INFO] Connexion MySQL échouée : {e}")
        stats = {
            'total_clients': 'N/A', 'risque': {}, 'statut': {},
            'salaire': {'min': 0, 'max': 0, 'avg': 0},
            'salaires_list': [], 'bilingues': 0
        }
    return stats

# -----------------------------------------------------------------------
# 3. GRAPHIQUE 1 : Répartition des documents (Pie + Bar)
# -----------------------------------------------------------------------
def plot_repartition(counts, output_path):
    labels  = list(counts.keys())
    values  = list(counts.values())
    total   = sum(values)
    couleurs = [COLORS['cin'], COLORS['paie1'], COLORS['paie2'], COLORS['steg']]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('white')
    fig.suptitle(
        f'Répartition du Jeu de Données Synthétique\n(Total : {total:,} documents)',
        fontsize=15, fontweight='bold', color=COLORS['text'], y=1.01
    )

    # -- Pie chart --
    wedges, texts, autotexts = ax1.pie(
        values, labels=None, colors=couleurs,
        autopct='%1.1f%%', startangle=140,
        wedgeprops=dict(linewidth=1.5, edgecolor='white'),
        textprops=dict(fontsize=11)
    )
    for at in autotexts:
        at.set_fontweight('bold')
        at.set_color('white')
        at.set_fontsize(12)

    legend_labels = [f"{l}  ({v:,})" for l, v in zip(labels, values)]
    ax1.legend(wedges, legend_labels, loc='lower center',
               bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=10)
    ax1.set_title('Distribution par type', fontsize=12, fontweight='bold', pad=12)

    # -- Bar chart --
    bars = ax2.bar(labels, values, color=couleurs, edgecolor='white', linewidth=1.2, width=0.55)
    ax2.set_facecolor(COLORS['grid'])
    ax2.yaxis.grid(True, color='white', linewidth=1.2)
    ax2.set_axisbelow(True)
    ax2.set_ylabel('Nombre de documents', fontsize=11)
    ax2.set_title('Quantité par type de document', fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', labelsize=10)
    ax2.spines[['top','right','left','bottom']].set_visible(False)

    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                 f'{val:,}', ha='center', va='bottom', fontsize=11, fontweight='bold',
                 color=COLORS['text'])

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  --> Graphique sauvegarde : {output_path}")

# -----------------------------------------------------------------------
# 4. GRAPHIQUE 2 : Taille des fichiers par type
# -----------------------------------------------------------------------
def plot_tailles(tailles_ko, output_path):
    data_filtered = {k: v for k, v in tailles_ko.items() if v}
    if not data_filtered:
        print("  [INFO] Aucune donnée de taille disponible.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['grid'])

    couleurs = [COLORS['cin'], COLORS['paie1'], COLORS['paie2'], COLORS['steg']]
    keys     = list(data_filtered.keys())
    vals     = [data_filtered[k] for k in keys]
    cols     = couleurs[:len(keys)]

    bp = ax.boxplot(vals, patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5))

    for patch, color in zip(bp['boxes'], cols):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax.set_xtickticklabels = None
    ax.set_xticklabels(keys, fontsize=11)
    ax.set_ylabel('Taille (Ko)', fontsize=11)
    ax.set_title('Distribution de la taille des fichiers par type de document',
                 fontsize=13, fontweight='bold', pad=12)
    ax.yaxis.grid(True, color='white', linewidth=1.2)
    ax.set_axisbelow(True)
    ax.spines[['top','right','left','bottom']].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  --> Graphique sauvegarde : {output_path}")

# -----------------------------------------------------------------------
# 5. GRAPHIQUE 3 : Répartition du niveau de risque
# -----------------------------------------------------------------------
def plot_risque(risque_dict, output_path):
    if not risque_dict:
        print("  [INFO] Données de risque non disponibles (DB hors ligne).")
        return

    labels  = list(risque_dict.keys())
    values  = list(risque_dict.values())
    risk_colors = {'Faible': '#59A14F', 'Moyen': '#F28E2B', 'Elevé': '#E15759', 'Élevé': '#E15759'}
    couleurs = [risk_colors.get(l, '#999999') for l in labels]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['grid'])

    bars = ax.bar(labels, values, color=couleurs, edgecolor='white', linewidth=1.5, width=0.45)
    ax.yaxis.grid(True, color='white', linewidth=1.2)
    ax.set_axisbelow(True)
    ax.set_ylabel('Nombre de clients', fontsize=11)
    ax.set_title('Répartition des clients par Niveau de Risque KYC',
                 fontsize=13, fontweight='bold', pad=12)
    ax.spines[['top','right','left','bottom']].set_visible(False)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{val:,}', ha='center', va='bottom', fontsize=12, fontweight='bold',
                color=COLORS['text'])

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  --> Graphique sauvegarde : {output_path}")

# -----------------------------------------------------------------------
# 6. GRAPHIQUE 4 : Distribution des salaires
# -----------------------------------------------------------------------
def plot_salaires(salaires_list, output_path):
    if not salaires_list:
        print("  [INFO] Données de salaires non disponibles.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('white')
    fig.suptitle('Analyse des Salaires des Clients dans le CBS',
                 fontsize=14, fontweight='bold', y=1.01)

    # Histogramme
    ax1.set_facecolor(COLORS['grid'])
    n, bins, patches = ax1.hist(salaires_list, bins=25, color=COLORS['paie1'],
                                 edgecolor='white', linewidth=0.8)
    ax1.yaxis.grid(True, color='white', linewidth=1.2)
    ax1.set_axisbelow(True)
    ax1.set_xlabel('Salaire Net (DT)', fontsize=11)
    ax1.set_ylabel('Nombre de clients', fontsize=11)
    ax1.set_title('Histogramme des salaires', fontsize=12, fontweight='bold')
    ax1.axvline(np.mean(salaires_list), color='red', linewidth=2,
                linestyle='--', label=f'Moyenne : {np.mean(salaires_list):.0f} DT')
    ax1.legend(fontsize=10)
    ax1.spines[['top','right','left','bottom']].set_visible(False)

    # Box plot
    ax2.set_facecolor(COLORS['grid'])
    bp = ax2.boxplot(salaires_list, patch_artist=True, vert=True,
                     medianprops=dict(color='black', linewidth=2.5))
    bp['boxes'][0].set_facecolor(COLORS['paie1'])
    bp['boxes'][0].set_alpha(0.7)
    ax2.yaxis.grid(True, color='white', linewidth=1.2)
    ax2.set_axisbelow(True)
    ax2.set_title('Box-Plot des salaires', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Salaire Net (DT)', fontsize=11)
    ax2.set_xticklabels(['Salaires'])
    ax2.spines[['top','right','left','bottom']].set_visible(False)

    # Annotations stats
    stats_text = (
        f"Min   : {min(salaires_list):.0f} DT\n"
        f"Max   : {max(salaires_list):.0f} DT\n"
        f"Moy   : {np.mean(salaires_list):.0f} DT\n"
        f"Méd   : {np.median(salaires_list):.0f} DT\n"
        f"Écart : {np.std(salaires_list):.0f} DT"
    )
    ax2.text(1.35, np.median(salaires_list), stats_text,
             fontsize=10, va='center', ha='left',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF9C4', edgecolor='gray'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  --> Graphique sauvegarde : {output_path}")

# -----------------------------------------------------------------------
# 7. TABLEAU RÉCAPITULATIF FINAL (figure Matplotlib)
# -----------------------------------------------------------------------
def plot_tableau_recap(counts, db_stats, tailles_ko, output_path):
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor('white')
    ax.axis('off')

    types   = list(counts.keys())
    couleurs = [COLORS['cin'], COLORS['paie1'], COLORS['paie2'], COLORS['steg']]

    col_labels = ['Type de Document', 'Quantité', 'Taille moy. (Ko)', 'Format', 'Langue']
    rows = []
    formats_info = {
        'CIN'               : ('PNG / JPG', 'Arabe'),
        'Fiche de Paie (T1)': ('JPG',       'Français'),
        'Fiche de Paie (T2)': ('JPG',       'Français'),
        'Facture STEG'      : ('JPG',       'Français / Arabe'),
    }
    for t in types:
        taille_moy = f"{np.mean(tailles_ko[t]):.1f}" if tailles_ko[t] else 'N/A'
        fmt, lang  = formats_info.get(t, ('?', '?'))
        rows.append([t, f"{counts[t]:,}", taille_moy, fmt, lang])

    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2.0)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#CCCCCC')
        if row == 0:
            cell.set_facecolor('#2C3E50')
            cell.set_text_props(color='white', fontweight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#F5F5F5')
        else:
            cell.set_facecolor('white')
        if col == 0 and row > 0:
            cell.set_facecolor(couleurs[row - 1])
            cell.set_text_props(color='white', fontweight='bold')

    total = sum(counts.values())
    ax.set_title(
        f'Tableau Récapitulatif du Jeu de Données  |  Total : {total:,} documents  |  '
        f'Clients CBS : {db_stats.get("total_clients", "N/A")}',
        fontsize=13, fontweight='bold', pad=20, color=COLORS['text']
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  --> Tableau récapitulatif sauvegardé : {output_path}")

# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  DATA UNDERSTANDING - Analyse du Jeu de Données KYC")
    print("=" * 60)

    # 1. Analyse du dossier
    print("\n[1/5] Analyse du dossier dataset_synthetique_masse...")
    counts, tailles_ko, dims = analyse_dossier(DATASET_DIR)

    total = sum(counts.values())
    print(f"      Total documents : {total:,}")
    for k, v in counts.items():
        moy_taille = f"{np.mean(tailles_ko[k]):.1f} Ko" if tailles_ko[k] else "N/A"
        print(f"        - {k:<22}: {v:>5} documents  |  Taille moy : {moy_taille}")

    # 2. Analyse de la base de données
    print("\n[2/5] Analyse de la base de données CBS (MySQL)...")
    db_stats = analyse_db()
    if db_stats['total_clients'] != 'N/A':
        print(f"      Total clients     : {db_stats['total_clients']:,}")
        print(f"      Clients bilingues : {db_stats['bilingues']:,}")
        print(f"      Salaire min/max   : {db_stats['salaire']['min']:.0f} / {db_stats['salaire']['max']:.0f} DT")
        print(f"      Salaire moyen     : {db_stats['salaire']['avg']:.0f} DT")
        print(f"      Niveaux de risque : {db_stats['risque']}")
    else:
        print("      [AVERTISSEMENT] MySQL non disponible, stats DB ignorées.")

    # 3. Génération des graphiques
    print("\n[3/5] Génération des graphiques...")
    plot_repartition(counts,
        os.path.join(OUTPUT_DIR, "fig1_repartition_documents.png"))

    plot_tailles(tailles_ko,
        os.path.join(OUTPUT_DIR, "fig2_taille_fichiers.png"))

    plot_risque(db_stats.get('risque', {}),
        os.path.join(OUTPUT_DIR, "fig3_niveau_risque.png"))

    plot_salaires(db_stats.get('salaires_list', []),
        os.path.join(OUTPUT_DIR, "fig4_salaires.png"))

    # 4. Tableau récapitulatif
    print("\n[4/5] Génération du tableau récapitulatif...")
    plot_tableau_recap(counts, db_stats, tailles_ko,
        os.path.join(OUTPUT_DIR, "fig5_tableau_recap.png"))

    # 5. Résumé final
    print("\n[5/5] Résumé Final")
    print("=" * 60)
    print(f"  Jeu de données total    : {total:,} documents")
    print(f"  Types de documents      : {len([v for v in counts.values() if v > 0])}")
    print(f"  Clients dans le CBS     : {db_stats.get('total_clients', 'N/A')}")
    print(f"  Clients bilingues AR/FR : {db_stats.get('bilingues', 'N/A')}")
    print(f"  Graphiques générés dans : {OUTPUT_DIR}")
    print("=" * 60)
    print("\nData Understanding terminee avec succes !")
