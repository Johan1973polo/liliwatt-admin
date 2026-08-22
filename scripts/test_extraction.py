#!/usr/bin/env python3
"""
test_extraction.py — Test standalone de l'extracteur de contrats (sans Flask).

Usage : python3 scripts/test_extraction.py contrats_test/contrat_ohm.pdf

Affiche :
  - le JSON brut renvoyé par le modèle
  - un tableau attendu / obtenu champ par champ
  - le nombre de tokens et le coût estimé
"""

import sys
import os
import json

# ── Charger OPENAI_API_KEY depuis .env si nécessaire ──────────────────────────
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

import pdfplumber
import io
import openai

# ── Valeurs de référence OHM ───────────────────────────────────────────────────
REFERENCE = {
    'ref_client':     'MIB-2607309010',
    'societe':        'CENTRE NAUTIQUE DE CASSENEUIL',
    'periode':        '2026-07',
    'date_debut':     '10/08/2026',
    'date_fin':       '31/12/2030',
    'type_energie':   'gaz',
    'pdl_pce':        '16364833539215',
    'fournisseur':    'OHM ENERGIE',
    'segment':        'GAZ',
    'nom_client':     'FERREIRA',
    'prenom_client':  'ANIBAL',
    'tel_client':     '0617176160',
    'email_client':   'ferreira-ani@sfr.fr',
    'volume_gaz':     14.4,
    'volume_elec':    None,
}

# ── Copie locale des fonctions (identiques à app.py) ──────────────────────────

_CONTRAT_SYSTEM_PROMPT = """Tu es un extracteur de données contractuelles pour des contrats d'énergie (gaz ou électricité).
Tu reçois le texte brut et les tableaux sérialisés d'un PDF de contrat.
Réponds UNIQUEMENT avec un objet JSON valide. Pas de texte autour, pas de balise markdown, pas de backtick.
Un champ introuvable vaut null. Ne pas inventer de valeur.

Règles d'extraction :

ref_client : Numéro MIB, format "MIB-XXXXXXXXXX". Il apparaît souvent sous la forme "MIB-XXXXXXXXXX: Offre du..." — extraire uniquement le numéro, sans les deux-points ni ce qui suit.

societe : Raison sociale du CLIENT. Dans le contrat, chercher le paragraphe qui commence par "Et" ou "d'autre part" — c'est le nom qui suit immédiatement, avant la virgule. Ne PAS prendre le nom du fournisseur (qui est entre "Entre" et "D'une part").

periode : Mois de SIGNATURE du contrat, format AAAA-MM. Chercher "Fait à ... le <jour> <mois> <année>" dans le corps du contrat. Convertir le nom du mois français en numéro (janvier=01, février=02, mars=03, avril=04, mai=05, juin=06, juillet=07, août=08, septembre=09, octobre=10, novembre=11, décembre=12).

date_debut : Date de DÉBUT de fourniture au format JJ/MM/AAAA. Se trouve dans le tableau des sites, colonne "Date de début".

date_fin : Date de FIN de fourniture au format JJ/MM/AAAA. Chercher la phrase "se termine le JJ/MM/AAAA".

ATTENTION : periode, date_debut et date_fin sont trois dates différentes — ne jamais les confondre.

type_energie : "gaz" si c'est un contrat de gaz naturel, "elec" si c'est un contrat d'électricité. Déduire du titre du contrat.

pdl_pce : Numéro(s) à 14 chiffres figurant dans la colonne "N° du Point de Comptage et d'Estimation (PCE)". ATTENTION : le SIRET fait aussi 14 chiffres mais se trouve dans une colonne distincte intitulée "SIRET du site" — ne pas les confondre. Si plusieurs sites, concaténer tous les PCE avec " / ".

fournisseur : Nom du fournisseur d'énergie. Se trouve entre "Entre" et "D'une part" dans l'en-tête du contrat.

segment : "GAZ" si type_energie vaut "gaz". null si type_energie vaut "elec".

nom_client : NOM (en majuscules) de la ligne du tableau Contacts dont la colonne Type contient exactement "Le signataire du contrat". Identifier la ligne par ce libellé, pas par sa position dans le tableau.

prenom_client : PRÉNOM de cette même ligne.

tel_client : Téléphone de cette même ligne (chiffres uniquement, sans espace ni tiret).

email_client : Email de cette même ligne.

volume_gaz : Si type_energie est "gaz" — volume d'une ANNÉE COMPLÈTE de fourniture en MWh (nombre décimal). Dans le tableau des sous-périodes, la première sous-période peut être PARTIELLE si la fourniture commence en cours d'année (ex: début 10/08/2026 → la sous-période 2026 ne couvre que quelques mois). Dans ce cas, IGNORER cette première sous-période et prendre la première sous-période couvrant une année entière (ex: 2027). Si plusieurs sites, additionner leurs volumes. Renvoyer uniquement la valeur numérique (ex: 14.4). null si type_energie est "elec".

volume_elec : Même règle pour un contrat d'électricité. null si type_energie est "gaz".

Champs toujours null (ne pas extraire) : vendeur, referent, montant_ht, commission_vendeur, commission_referent, statut_paiement, date_paiement_1, date_paiement_2, lien_drive."""


def extraire_contenu(pdf_bytes):
    parties = []
    total_chars = 0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages[:8], start=1):
            texte = page.extract_text() or ''
            total_chars += len(texte)
            parties.append(f'=== PAGE {i} / TEXTE ===\n{texte}')
            for j, table in enumerate(page.extract_tables(), start=1):
                lignes = []
                for row in table:
                    cells = [str(c).strip() if c else '' for c in row]
                    lignes.append(' | '.join(cells))
                parties.append(f'=== PAGE {i} / TABLEAU {j} ===\n' + '\n'.join(lignes))
    if total_chars < 200:
        raise ValueError('PDF sans texte extractible (scan ?)')
    return '\n\n'.join(parties)


def extraire_champs(contenu):
    client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY', ''))
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': _CONTRAT_SYSTEM_PROMPT},
            {'role': 'user',   'content': contenu},
        ],
        temperature=0,
        response_format={'type': 'json_object'},
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw), raw, resp.usage


def normalise(v):
    """Normalise pour comparaison : strip, lower pour les strings."""
    if v is None:
        return None
    if isinstance(v, float):
        return v
    return str(v).strip()


def comparer(attendu, obtenu):
    a = normalise(attendu)
    o = normalise(obtenu)
    if a is None and o is None:
        return True
    if a is None or o is None:
        return False
    if isinstance(a, float):
        try:
            return abs(float(o) - a) < 0.001
        except (TypeError, ValueError):
            return False
    return a.lower() == o.lower()


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/test_extraction.py contrats_test/contrat_ohm.pdf')
        sys.exit(1)

    pdf_path = sys.argv[1]
    with open(pdf_path, 'rb') as fh:
        pdf_bytes = fh.read()

    print(f'\nFichier : {pdf_path} ({len(pdf_bytes)//1024} Ko)')
    print('Extraction du contenu PDF...')
    contenu = extraire_contenu(pdf_bytes)
    contenu_chars = len(contenu)
    print(f'Contenu structuré : {contenu_chars} caractères')

    print('Appel OpenAI gpt-4o-mini...')
    champs, raw_json, usage = extraire_champs(contenu)

    # ── JSON brut ──────────────────────────────────────────────────────────────
    print('\n' + '='*70)
    print('  JSON BRUT RENVOYÉ PAR LE MODÈLE')
    print('='*70)
    print(raw_json)

    # ── Tableau comparatif ─────────────────────────────────────────────────────
    print('\n' + '='*70)
    print('  TABLEAU ATTENDU / OBTENU')
    print('='*70)
    fmt = '  {:<22} {:<25} {:<25} {}'
    print(fmt.format('CHAMP', 'ATTENDU', 'OBTENU', 'OK?'))
    print('  ' + '-'*80)

    nb_ok = 0
    nb_ko = 0
    for champ, attendu in REFERENCE.items():
        obtenu = champs.get(champ)
        ok = comparer(attendu, obtenu)
        if ok:
            nb_ok += 1
        else:
            nb_ko += 1
        statut = '✅' if ok else '❌'
        att_str = str(attendu) if attendu is not None else 'null'
        obt_str = str(obtenu) if obtenu is not None else 'null'
        print(fmt.format(champ, att_str[:24], obt_str[:24], statut))

    print(f'\n  Résultat : {nb_ok}/{nb_ok+nb_ko} champs corrects')

    # ── Tokens et coût ────────────────────────────────────────────────────────
    # gpt-4o-mini : $0.15 / 1M tokens prompt, $0.60 / 1M tokens completion (tarifs 2025)
    cout_prompt     = usage.prompt_tokens     * 0.15  / 1_000_000
    cout_completion = usage.completion_tokens * 0.60  / 1_000_000
    cout_total      = cout_prompt + cout_completion

    print('\n' + '='*70)
    print('  TOKENS ET COÛT')
    print('='*70)
    print(f'  Prompt tokens     : {usage.prompt_tokens:,}')
    print(f'  Completion tokens : {usage.completion_tokens:,}')
    print(f'  Total tokens      : {usage.total_tokens:,}')
    print(f'  Coût estimé       : ${cout_total:.4f} USD  (~{cout_total*0.92:.4f} €)')
    print(f'  Coût pour 100 contrats : ${cout_total*100:.2f} USD')


if __name__ == '__main__':
    main()
