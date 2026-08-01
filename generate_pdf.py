import os
import re
import sys
import base64
import requests
import markdown
import shutil
from xhtml2pdf import pisa
import xhtml2pdf.reportlab_paragraph as reportlab_paragraph

# Monkey patch pour corriger le bug TypeError: sequence item 0: expected str instance, list found
old_getPlainText = reportlab_paragraph.Paragraph.getPlainText

def new_getPlainText(self, identify=None):
    frags = getattr(self, "frags", None)
    if frags:
        result = []
        for frag in frags:
            if hasattr(frag, "text"):
                if isinstance(frag.text, str):
                    result.append(frag.text)
                elif isinstance(frag.text, list):
                    result.append("".join(str(x) for x in frag.text))
                else:
                    result.append(str(frag.text))
        return "".join(result)
    if identify:
        text = getattr(self, "text", None)
        if text is None:
            text = repr(self)
        return str(text)
    return ""

reportlab_paragraph.Paragraph.getPlainText = new_getPlainText
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def get_mermaid_image_url(mermaid_code):
    # Nettoyer le code
    mermaid_code = mermaid_code.strip()
    # Encoder en base64 url-friendly
    graph_bytes = mermaid_code.encode("utf-8")
    base64_bytes = base64.urlsafe_b64encode(graph_bytes)
    base64_string = base64_bytes.decode("ascii")
    # Enlever le rembourrage '='
    base64_string = base64_string.rstrip("=")
    return f"https://mermaid.ink/img/{base64_string}"

def download_image(url, output_path):
    print(f"Téléchargement du diagramme depuis : {url}")
    try:
        response = requests.get(url, timeout=25)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"Erreur HTTP {response.status_code} lors du téléchargement.")
            return False
    except Exception as e:
        print(f"Erreur de connexion : {e}")
        return False

def convert_md_to_pdf(md_path, pdf_path):
    # Lire le fichier Markdown
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Créer le dossier pour les images des diagrammes si nécessaire
    img_dir = os.path.join(os.path.dirname(md_path), "images_temp")
    os.makedirs(img_dir, exist_ok=True)

    # Trouver et remplacer les blocs Mermaid par des images locales
    mermaid_pattern = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
    matches = list(mermaid_pattern.finditer(md_content))
    
    offset = 0
    diagram_count = 0
    
    for match in matches:
        mermaid_code = match.group(1)
        diagram_count += 1
        img_name = f"diagramme_{diagram_count}.png"
        img_path = os.path.join(img_dir, img_name)
        
        # Récupérer l'URL de l'image
        img_url = get_mermaid_image_url(mermaid_code)
        
        # Télécharger l'image localement
        success = download_image(img_url, img_path)
        
        # Si téléchargement réussi, on remplace le bloc par une balise image markdown
        if success:
            # Remplacement avec chemin relatif
            markdown_img = f"![Diagramme UML {diagram_count}](images_temp/{img_name})"
            start = match.start() + offset
            end = match.end() + offset
            md_content = md_content[:start] + markdown_img + md_content[end:]
            offset += len(markdown_img) - (end - start)
        else:
            print(f"Échec de rendu pour le diagramme {diagram_count}, conservation du code textuel.")

    # Nettoyer l'autre chemin absolu vers l'image de l'architecture pour le rendre relatif
    # Copions l'image vers le dossier temp si elle existe
    arch_src = r"C:\Users\bahae\.gemini\antigravity\brain\e35d5f8a-4fec-411f-a99a-7f6fa81e8e12\kyc_system_architecture_1781829272735.png"
    arch_dest = os.path.join(img_dir, "kyc_system_architecture.png")
    if os.path.exists(arch_src):
        shutil.copy(arch_src, arch_dest)
        print("Copie de l'image d'architecture effectuée.")
        # Remplacer dans le md
        md_content = md_content.replace(
            "C:/Users/bahae/.gemini/antigravity/brain/e35d5f8a-4fec-411f-a99a-7f6fa81e8e12/kyc_system_architecture_1781829272735.png",
            "images_temp/kyc_system_architecture.png"
        )

    # Convertir le Markdown en HTML avec tables et fenced_code
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

    # Template HTML avec CSS pour un PDF professionnel et élégant
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4;
                margin: 2cm;
            }}
            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #222222;
            }}
            h1 {{
                font-size: 24pt;
                color: #1a365d;
                border-bottom: 2px solid #2b6cb0;
                padding-bottom: 8px;
                margin-top: 0;
                margin-bottom: 20px;
                text-align: center;
            }}
            h2 {{
                font-size: 16pt;
                color: #2b6cb0;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 5px;
                margin-top: 30px;
                margin-bottom: 15px;
                page-break-after: avoid;
            }}
            h3 {{
                font-size: 12pt;
                color: #4a5568;
                margin-top: 20px;
                margin-bottom: 10px;
                page-break-after: avoid;
            }}
            p {{
                margin-bottom: 12px;
                text-align: justify;
            }}
            ul, ol {{
                margin-bottom: 15px;
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            hr {{
                border: 0;
                border-top: 1px solid #e2e8f0;
                margin: 25px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                font-size: 10pt;
            }}
            th {{
                background-color: #ebf8ff;
                color: #2b6cb0;
                font-weight: bold;
                border: 1px solid #cbd5e0;
                padding: 8px;
                text-align: left;
            }}
            td {{
                border: 1px solid #cbd5e0;
                padding: 8px;
            }}
            tr:nth-child(even) {{
                background-color: #f7fafc;
            }}
            img {{
                display: block;
                margin: 20px auto;
                max-width: 100%;
                height: auto;
            }}
            pre, code {{
                font-family: 'Courier New', Courier, monospace;
                background-color: #f7fafc;
                font-size: 10pt;
            }}
            pre {{
                padding: 10px;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                white-space: pre-wrap;
                margin-bottom: 15px;
            }}
            .cover {{
                page-break-after: always;
                text-align: center;
                padding-top: 5cm;
            }}
            .cover h1 {{
                font-size: 28pt;
                margin-bottom: 2cm;
                border-bottom: none;
            }}
            .cover p {{
                font-size: 14pt;
                color: #4a5568;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="cover">
            <h1>Rapport de Cadrage, Planification et Architecture Technique</h1>
            <p><strong>Projet de Fin d'Études (PFE)</strong></p>
            <p style="margin-top: 1cm; font-size: 12pt; color: #718096;">
                Sujet : Automatisation de la revue KYC : Extraction documentaire (OCR) et Rapprochement de données bancaires (Core Banking System)<br>
                Contexte : Tunisie (STEG / SONEDE)
            </p>
            <p style="margin-top: 3cm; font-size: 11pt; color: #a0aec0;">
                Généré automatiquement par Antigravity
            </p>
        </div>
        {html_content}
    </body>
    </html>
    """

    # Enregistrer le HTML pour debug si besoin
    html_debug_path = md_path.replace(".md", "_debug.html")
    with open(html_debug_path, "w", encoding="utf-8") as f:
        f.write(styled_html)
    print(f"HTML temporaire sauvegardé pour débogage : {html_debug_path}")

    # Générer le PDF
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(styled_html, dest=pdf_file)
        
    if not pisa_status.err:
        print(f"[OK] PDF généré avec succès à l'emplacement : {pdf_path}")
        return True
    else:
        print("[ERROR] Erreur lors de la génération du PDF.")
        return False

if __name__ == "__main__":
    md_file = r"d:\PFE\AAAA.md"
    pdf_file = r"d:\PFE\AAAA.pdf"
    convert_md_to_pdf(md_file, pdf_file)
