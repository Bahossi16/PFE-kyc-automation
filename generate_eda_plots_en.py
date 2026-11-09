"""
=======================================================================
  DATA UNDERSTANDING - ENGLISH PLOTS GENERATOR
  Project: KYC Automation (UIB PFE)
  Generates English figures for slides and defense report.
=======================================================================
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

DATASET_DIR = r"D:\PFE\dataset_synthetique_masse"
OUTPUT_DIR  = r"D:\PFE\data_understanding_output_en"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    'cin'   : '#4E79A7',
    'paie1' : '#F28E2B',
    'paie2' : '#E15759',
    'steg'  : '#76B7B2',
    'grid'  : '#F0F0F0',
    'text'  : '#333333',
}

# English label mappings
LABELS_EN = {
    'CIN': 'National ID (CIN)',
    'Fiche de Paie (T1)': 'Payslip (Layout 1)',
    'Fiche de Paie (T2)': 'Payslip (Layout 2)',
    'Facture STEG': 'Utility Bill (STEG)'
}

def scan_dataset(directory):
    counts = {
        'National ID (CIN)': 0,
        'Payslip (Layout 1)': 0,
        'Payslip (Layout 2)': 0,
        'Utility Bill (STEG)': 0
    }
    sizes_kb = {
        'National ID (CIN)': [],
        'Payslip (Layout 1)': [],
        'Payslip (Layout 2)': [],
        'Utility Bill (STEG)': []
    }

    if not os.path.isdir(directory):
        print(f"[ERROR] Directory not found: {directory}")
        return counts, sizes_kb

    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue

        size_kb = os.path.getsize(fpath) / 1024

        if fname.startswith('cin_mass'):
            key = 'National ID (CIN)'
        elif fname.startswith('paie_mass') or fname.startswith('paie2_mass_exist'):
            key = 'Payslip (Layout 1)'
        elif fname.startswith('paie2_mass_new'):
            key = 'Payslip (Layout 2)'
        elif fname.startswith('steg_mass'):
            key = 'Utility Bill (STEG)'
        else:
            continue

        counts[key] += 1
        sizes_kb[key].append(size_kb)

    return counts, sizes_kb

def plot_repartition_en(counts, output_path):
    labels  = list(counts.keys())
    values  = list(counts.values())
    total   = sum(values)
    colors  = [COLORS['cin'], COLORS['paie1'], COLORS['paie2'], COLORS['steg']]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.patch.set_facecolor('white')
    fig.suptitle(
        f'Synthetic Dataset Distribution\n(Total: {total:,} documents)',
        fontsize=15, fontweight='bold', color=COLORS['text'], y=1.02
    )

    # Pie Chart
    wedges, texts, autotexts = ax1.pie(
        values, labels=None, colors=colors,
        autopct='%1.1f%%', startangle=140,
        wedgeprops=dict(linewidth=1.5, edgecolor='white'),
        textprops=dict(fontsize=11)
    )
    for at in autotexts:
        at.set_fontweight('bold')
        at.set_color('white')
        at.set_fontsize(12)

    legend_labels = [f"{l} ({v:,})" for l, v in zip(labels, values)]
    ax1.legend(wedges, legend_labels, loc='lower center',
               bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=10)
    ax1.set_title('Distribution by Document Type', fontsize=12, fontweight='bold', pad=12)

    # Bar Chart
    bars = ax2.bar(labels, values, color=colors, edgecolor='white', linewidth=1.2, width=0.55)
    ax2.set_facecolor(COLORS['grid'])
    ax2.yaxis.grid(True, color='white', linewidth=1.2)
    ax2.set_axisbelow(True)
    ax2.set_ylabel('Number of Documents', fontsize=11)
    ax2.set_title('Document Count by Category', fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', labelsize=9.5)
    ax2.spines[['top','right','left','bottom']].set_visible(False)

    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                 f'{val:,}', ha='center', va='bottom', fontsize=11, fontweight='bold',
                 color=COLORS['text'])

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {output_path}")

def plot_sizes_en(sizes_kb, output_path):
    data_filtered = {k: v for k, v in sizes_kb.items() if v}
    if not data_filtered:
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['grid'])

    colors = [COLORS['cin'], COLORS['paie1'], COLORS['paie2'], COLORS['steg']]
    keys   = list(data_filtered.keys())
    vals   = [data_filtered[k] for k in keys]
    cols   = colors[:len(keys)]

    bp = ax.boxplot(vals, patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5))

    for patch, color in zip(bp['boxes'], cols):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax.set_xticklabels(keys, fontsize=10.5)
    ax.set_ylabel('File Size (KB)', fontsize=11)
    ax.set_title('File Size Distribution by Document Category',
                 fontsize=13, fontweight='bold', pad=12)
    ax.yaxis.grid(True, color='white', linewidth=1.2)
    ax.set_axisbelow(True)
    ax.spines[['top','right','left','bottom']].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {output_path}")

def plot_eda_combined_slide_en(counts, sizes_kb, output_path):
    """Generates a single, ready-to-use slide graphic combining both charts with English labels."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 8), gridspec_kw={'height_ratios': [1, 1]})
    fig.patch.set_facecolor('white')

    colors = [COLORS['cin'], COLORS['paie1'], COLORS['paie2'], COLORS['steg']]
    labels = list(counts.keys())
    values = list(counts.values())

    # 1. Pie Chart
    wedges, texts, autotexts = ax1.pie(
        values, labels=None, colors=colors,
        autopct='%1.1f%%', startangle=140,
        wedgeprops=dict(linewidth=1.5, edgecolor='white'),
        textprops=dict(fontsize=10)
    )
    for at in autotexts:
        at.set_fontweight('bold')
        at.set_color('white')
    ax1.set_title('Distribution by Document Type', fontsize=11, fontweight='bold')

    # Legend in ax1
    legend_labels = [f"{l} ({v})" for l, v in zip(labels, values)]
    ax1.legend(wedges, legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8.5)

    # 2. Bar Chart
    bars = ax2.bar(labels, values, color=colors, edgecolor='white', width=0.5)
    ax2.set_facecolor(COLORS['grid'])
    ax2.yaxis.grid(True, color='white', linewidth=1.2)
    ax2.set_axisbelow(True)
    ax2.set_ylabel('Number of Documents', fontsize=10)
    ax2.set_title('Document Count (Total: 2,100)', fontsize=11, fontweight='bold')
    ax2.tick_params(axis='x', labelsize=8)
    ax2.spines[['top','right','left','bottom']].set_visible(False)
    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
                 f'{val}', ha='center', va='bottom', fontsize=9.5, fontweight='bold', color=COLORS['text'])

    # 3. Boxplot File Sizes spanning the bottom
    ax3.remove()
    ax4.remove()
    ax_bottom = fig.add_subplot(2, 1, 2)
    ax_bottom.set_facecolor(COLORS['grid'])

    vals = [sizes_kb[k] for k in labels]
    bp = ax_bottom.boxplot(vals, patch_artist=True,
                           medianprops=dict(color='black', linewidth=2),
                           whiskerprops=dict(linewidth=1.5),
                           capprops=dict(linewidth=1.5))

    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax_bottom.set_xticklabels(labels, fontsize=10)
    ax_bottom.set_ylabel('File Size (KB)', fontsize=10)
    ax_bottom.set_title('File Size Distribution across Document Types', fontsize=11, fontweight='bold', pad=10)
    ax_bottom.yaxis.grid(True, color='white', linewidth=1.2)
    ax_bottom.set_axisbelow(True)
    ax_bottom.spines[['top','right','left','bottom']].set_visible(False)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.35)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved Combined Slide Graphic: {output_path}")

if __name__ == '__main__':
    counts, sizes_kb = scan_dataset(DATASET_DIR)
    
    # Generate standalone figures
    plot_repartition_en(counts, os.path.join(OUTPUT_DIR, "fig1_distribution_en.png"))
    plot_sizes_en(sizes_kb, os.path.join(OUTPUT_DIR, "fig2_file_sizes_en.png"))
    
    # Generate combined graphic ready for Canva
    plot_eda_combined_slide_en(counts, sizes_kb, os.path.join(OUTPUT_DIR, "eda_slide_combined_en.png"))
