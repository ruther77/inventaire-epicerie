import pandas as pd
import re
import io
from PyPDF2 import PdfReader 
from docx import Document    

def clean_data(value):
    """Nettoie une valeur numérique (remplace la virgule par le point)."""
    if isinstance(value, str):
        # Remplace la virgule par le point et supprime tout caractère non numérique/point/espace
        return value.replace(',', '.').replace('-', '').strip()
    return value

def extract_text_from_file(uploaded_file):
    """
    Extrait le texte brut d'un fichier téléversé (PDF ou DOCX/DOC).
    """
    file_type = uploaded_file.type
    
    # 1. Traitement des PDF
    if 'pdf' in file_type:
        try:
            pdf_reader = PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception:
            return "Erreur lors de la lecture du PDF."

    # 2. Traitement des DOCX (Word)
    elif 'word' in file_type or 'document' in file_type or uploaded_file.name.endswith('.docx'):
        try:
            document = Document(uploaded_file)
            text = '\n'.join([paragraph.text for paragraph in document.paragraphs])
            return text
        except Exception:
            return "Erreur lors de la lecture du fichier Word (.docx)."

    # 3. Traitement du texte brut
    elif 'text' in file_type or uploaded_file.name.endswith('.txt'):
        return uploaded_file.getvalue().decode("utf-8")
        
    else:
        return "" # Type de fichier non supporté

# Fichier : invoice_extractor.py (Mise à jour de la fonction d'extraction)

# ... (les imports et la fonction clean_data restent inchangés) ...

def extract_products_from_metro_invoice(raw_product_text):
    """
    Analyse le texte brut de la section produit en utilisant une regex plus stricte
    pour éviter l'agglomération de plusieurs lignes de produits dans une seule entrée.
    """
    
    # Étape 1: Nettoyage et simplification du Texte
    # On ajoute un point-virgule après chaque saut de ligne pour faciliter la détection de fin de ligne de produit
    text = re.sub(r'["\s,]+', ' ', raw_product_text).strip()
    text = text.replace('\n', '; ') # Remplacement des sauts de ligne par ; 
    
    data = []
    
    # Regex Pattern Ultra-Robuste et STRICTE : Cherche la séquence distinctive des nombres
    # L'élément clé est la désignation (G3) qui s'arrête strictement avant le Prix Unitaire
    pattern = re.compile(
        # G1: EAN (10 à 14 chiffres)
        r'(\d{10,14})'
        # G2: Numéro Article (6 à 10 chiffres)
        r'\s*(\d{6,10})'
        
        # G3: Désignation (capture tout, NON GOURMAND, jusqu'à la prochaine séquence de prix)
        # On évite que la désignation "mange" la ligne suivante
        r'\s*(.+?)'
        
        # G4: Prix Unitaire (nombre décimal avec point)
        r'([\d\.]+)'
        # G5: Quantité (un nombre entier)
        r'\s*(\d+)'
        # G6: Montant Total (nombre décimal avec point)
        r'\s*([\d\.]+)'
        # G7: Code TVA (D ou P)
        r'\s*([DP])'
        , re.IGNORECASE | re.DOTALL
    )
    
    # Pré-nettoyage du texte pour le rendre compatible avec la regex
    text_processed = text.replace(',', '.') 
    
    # On itère sur tous les motifs trouvés dans le texte nettoyé
    for match in pattern.finditer(text_processed):
        try:
            ean = match.group(1).strip()
            num_article = match.group(2).strip()
            
            designation_raw = match.group(3).strip()
            # Nettoyage des chaînes de bruit connues
            designation = re.sub(r'(Duplicata|PRIX AU KG OU AU LITRE|Plus COTIS SECURITE SOCIALE|Total:.*|Volume effectif|Montant TTC|PAGE:.*|Numéro Article|VE unit. L.).*', '', designation_raw).strip()
            
            prix_unitaire_raw = match.group(4)
            quantite = match.group(5)
            montant_total_raw = match.group(6)
            code_tva = match.group(7)
            
            data.append({
                'nom': designation,
                'prix_vente': float(montant_total_raw)/float(prix_unitaire_raw),
                'tva': code_tva,
                'qte_init': int(quantite),
                'codes': ean
            })
            
        except Exception as e:
            # Poursuit la recherche même en cas d'erreur de conversion de type
            continue

    return pd.DataFrame(data)

# ... (le bloc if __name__ == '__main__': reste inchangé) ...
if __name__ == '__main__':
    pass
