import pandas as pd
import re
import io

def clean_data(value):
    """Nettoie une valeur numérique (remplace la virgule par le point)."""
    if isinstance(value, str):
        return value.replace(',', '.').replace('-', '').strip()
    return value

def extract_products_from_metro_invoice(raw_product_text):
    """
    Analyse le texte brut de la section produit en utilisant une regex ultra-robuste
    basée sur la séquence des nombres (EAN, Prix, Qté, Montant, TVA).
    """
    
    # Étape 1: Nettoyage et simplification du Texte
    # On supprime toutes les citations, guillemets, et on remplace tous les séparateurs par un simple espace
    text = re.sub(r'["\s,]+', ' ', raw_product_text).strip()
    
    data = []
    
    # Regex Pattern Ultra-Robuste : Cherche la séquence distinctive des nombres
    # EAN/ID -> DESIGNATION -> Prix -> Quantité -> Montant -> TVA
    pattern = re.compile(
        # G1: EAN (10 à 14 chiffres)
        r'(\d{10,14})'
        # G2: Numéro Article (6 à 10 chiffres, parfois collé ou précédé de bruit)
        r'\s*(\d{6,10})'
        
        # G3: Désignation (capture tout ce qui se trouve ensuite)
        # On rend cette capture non gourmande (.+?) jusqu'au motif de prix/quantité
        r'\s*(.+?)'
        
        # G4: Prix Unitaire (nombre avec point)
        r'([\d\.]+)'
        # G5: Quantité (un nombre entier)
        r'\s*(\d+)'
        # G6: Montant Total (nombre avec point)
        r'\s*([\d\.]+)'
        # G7: Code TVA (D ou P)
        r'\s*([DP])'
        , re.IGNORECASE | re.DOTALL
    )
    
    # Pré-nettoyage du texte d'exemple pour correspondre au regex (remplacement des virgules par des points)
    # La regex utilise le point pour les décimales, on prépare le texte.
    text_processed = text.replace(',', '.') 
    
    # On itère sur tous les motifs trouvés dans le texte nettoyé
    for match in pattern.finditer(text_processed):
        try:
            ean = match.group(1).strip()
            num_article = match.group(2).strip()
            
            # La désignation est le bloc le plus difficile. On nettoie tout ce qui est bruit
            designation_raw = match.group(3).strip()
            designation = re.sub(r'(Duplicata|PRIX AU KG OU AU LITRE|Plus COTIS SECURITE SOCIALE).*', '', designation_raw).strip()
            
            prix_unitaire_raw = match.group(4)
            quantite = match.group(5)
            montant_total_raw = match.group(6)
            code_tva = match.group(7)
            
            data.append({
                'EAN': ean,
                'Numéro Article': num_article,
                'Désignation': designation,
                'Prix Unitaire (Achat)': float(prix_unitaire_raw),
                'Quantité': int(quantite),
                'Montant Total': float(montant_total_raw),
                'Code TVA': code_tva
            })
            
        except Exception as e:
            # Cette erreur se produit si la conversion float/int échoue.
            print(f"Erreur de conversion pour un bloc: {e}. Bloc ignoré.")
            continue

    return pd.DataFrame(data)

# --- (Le reste du script, y compris l'exemple de données, reste identique) ---

# --- DONNÉES DE L'EXEMPLE (Source 33) ---

# Remarque : Pour faire fonctionner le script, vous devez copier le contenu exact
# de la section "The following table"  comme ceci, en tant que chaîne Python multi-ligne.
# J'ai reconstruit la chaîne la plus propre possible à partir de votre sortie fournie.
raw_invoice_data_example = """
5902738887876
1765353
","VODKA SOBIESKI 37.5D 70CL
 S 37,5
 0,263
 9:NC220860110000/S200_S/39 Alcool NON Rhum SUP18D/
0,700
","7,970
","13
",,"23,91
","D
"
"

3147690094708
1925981
","Duplicata
 PRIX AU KG OU AU LITRE: 11,386
 Plus COTIS. SECURITE SOCIALE
 RHUM AMBRE LM 40D 20CL X6
 G 40,0 0,080
 NC220840110000/S200_S/36_Rhums TRADDOM contingent Fisc
 PRIX AU KG OU AU LITRE: 12.490
 Plus COTIS. SECURITE SOCIALE
  32,0
 BS TI MANGUE PASSION 32D 70CL
  :NC220890690000/S200_S/39_Alcool NON Rhum_SUP18D/
 PRIX AU KG OU AU LITRE: 28,614
 Plus COTIS. SECURITE SOCIALE
 HEINEKEN PACK 5D 20X25CL VP
 0,013
  :NC220300010000/B000_B/25_Bieres SUP 2.8D_taux normal/
 PRIX AU KG OU AU LITRE: 2,100-




0,200
 : art 403




3760221470026 2693208
 *** SPIRITUEUX Total: 85,95
 3119780268276 2017291


0,700






0,250
","

2,498
 1.1/


20,030


0,525
","



6 2


11


2


20
",,"4,80


29,98


5,86
 20,03


1,37


21.00
","D


D


D


D


D


P


D
"


"3053485
3080216061306
","1664 BLDE 5.5D 18X25CL VP
 B 5.5 0.014
 0,250
  :NC220300010000/B000_B/25_Bieres SUP 2.8D_taux normal/
 PRIX AU KG OU AU LITRE: 2,140
","0,535
","2
18
",,"19,26
","P
D
"
"2028330
3155930400530
","DESPERAD 5.9D 33CL VP //
 B 5,9 0,019 0,330
  :NC220300010000/B000_B/25_Bieres SUP 2.8D_taux normal/
 PRIX AU KG OU AU LITRE: 3,352
","1,106
","1
24
",,"26,54
","D
"
"""

if __name__ == "__main__":
    df_products = extract_products_from_metro_invoice(raw_invoice_data_example)

    # Étape 2: Sauvegarde en CSV
    output_filename = "Produits_Facture_Extraits.csv"
    df_products.to_csv(output_filename, index=False, encoding='utf-8')

    print(f"Extraction terminée. Les données ont été sauvegardées dans {output_filename}")
    print("\nAperçu du DataFrame :")
    print(df_products.to_string())
