#!/usr/bin/env python3
"""
Rapproche l'export CRM (Neon) avec le Sheet MDP ZOHO VENDEURS et remplit
les colonnes L (NUMERO_COURTIER) et N (TELEPHONE) quand elles sont vides.

Le CRM fait foi : il porte la contrainte @unique sur courtierNumber.

Usage :
    python3 scripts/sync_crm_vers_sheet.py ~/Desktop/crm_export.csv          # dry-run
    python3 scripts/sync_crm_vers_sheet.py ~/Desktop/crm_export.csv --apply  # ecriture

Le mode par defaut n'ecrit RIEN : il affiche ce qui serait modifie.
"""
import sys, os, csv, json, unicodedata

COL_EMAIL = 3    # D
COL_COURTIER = 11  # L
COL_TEL = 13     # N
NB_COLS = 14     # A -> N

ECRASER = False  # True = ecrase aussi les cellules deja remplies


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').strip())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    csv_path = os.path.expanduser(sys.argv[1])
    apply_changes = '--apply' in sys.argv

    # ---- 1. Charger l'export CRM ----
    crm = {}
    with open(csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            email = norm(row.get('email'))
            if not email:
                continue
            crm[email] = {
                'phone': (row.get('phone') or '').strip(),
                'courtier': (row.get('courtierNumber') or '').strip(),
                'nom': f"{row.get('firstName','')} {row.get('lastName','')}".strip(),
            }
    print(f"CRM : {len(crm)} utilisateurs charges depuis {csv_path}\n")

    # ---- 2. Lire le Sheet ----
    import gspread
    from google.oauth2.service_account import Credentials
    SCOPES = ['https://spreadsheets.google.com/feeds',
              'https://www.googleapis.com/auth/drive']
    creds_json = os.environ.get('GOOGLE_CREDS_JSON', '')
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
        print("Credentials : variable GOOGLE_CREDS_JSON")
    else:
        # Fallback : fichier de service account a la racine du repo
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sa_file = os.path.join(racine, 'liliwatt-eddcc0bc9e18.json')
        if not os.path.exists(sa_file):
            print("Ni GOOGLE_CREDS_JSON ni %s. Impossible de lire le Sheet." % sa_file)
            sys.exit(1)
        creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
        print("Credentials : %s" % os.path.basename(sa_file))
    gc = gspread.authorize(creds)
    sheet_id = os.environ.get('GOOGLE_SHEET_ID') or '11gVGMBtqMUhPh70yjMgjW-yLDht6fO0KqWJAF53ASXk'
    ws = gc.open_by_key(sheet_id).sheet1
    rows = ws.get_all_values()

    updates, inchanges, absents = [], 0, []

    for i, row in enumerate(rows[1:], start=2):  # start=2 : ligne 1 = entetes
        if len(row) <= COL_EMAIL:
            continue
        email = norm(row[COL_EMAIL])
        if '@' not in email:
            continue
        if email not in crm:
            absents.append((i, row[COL_EMAIL]))
            continue

        data = crm[email]
        actuel_courtier = row[COL_COURTIER].strip() if len(row) > COL_COURTIER else ''
        actuel_tel = row[COL_TEL].strip() if len(row) > COL_TEL else ''

        if data['courtier'] and (ECRASER or not actuel_courtier):
            if actuel_courtier != data['courtier']:
                updates.append((f'L{i}', data['courtier'], row[0], actuel_courtier))
        if data['phone'] and (ECRASER or not actuel_tel):
            if actuel_tel != data['phone']:
                updates.append((f'N{i}', data['phone'], row[0], actuel_tel))

        if not updates or updates[-1][2] != row[0]:
            inchanges += 1

    # ---- 3. Rapport ----
    print(f"{'CELLULE':<8} {'VENDEUR':<18} {'AVANT':<16} -> APRES")
    print('-' * 62)
    for cell, val, nom, avant in updates:
        print(f"{cell:<8} {nom[:17]:<18} {(avant or '(vide)'):<16} -> {val}")

    print(f"\n{len(updates)} cellule(s) a remplir.")
    if absents:
        print(f"\n{len(absents)} ligne(s) du Sheet absente(s) du CRM (non modifiees) :")
        for i, e in absents:
            print(f"   ligne {i:>3} : {e}")

    # ---- 4. Ecriture ----
    if not updates:
        print("\nRien a faire.")
        return
    if not apply_changes:
        print("\nDRY-RUN : aucune ecriture. Relance avec --apply pour appliquer.")
        return

    ws.batch_update([{'range': c, 'values': [[v]]} for c, v, _, _ in updates])
    print(f"\n{len(updates)} cellule(s) ecrite(s) dans le Sheet.")


if __name__ == '__main__':
    main()
