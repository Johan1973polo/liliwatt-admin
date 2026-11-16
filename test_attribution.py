"""
test_attribution.py — Lot 3 Étape A : attribution des CV entre recruteuses.

Appelle les VRAIES routes Flask sur http://127.0.0.1:5001.
Écrit dans le SHEET DE PRODUCTION.
Nettoyage à la fin : T remis à vide, C restauré.

Lancer depuis liliwatt-admin :
    .venv/bin/python test_attribution.py
"""

import json, os, sys, subprocess, time
import gspread
from google.oauth2.service_account import Credentials
import requests

BASE_URL = 'http://127.0.0.1:5001'
JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'liliwatt-eddcc0bc9e18.json')
RECRUTEMENT_SHEET_ID = '11A-aJIqtm0JZ01lU43GpWudWDNFtknIr-4sYgYD-6ck'

# ── Charger le JSON de service account (sans afficher le contenu) ────────────
with open(JSON_FILE) as _f:
    _creds_json = _f.read()
os.environ['GOOGLE_CREDS_JSON'] = _creds_json

# ── Charger .env (format "export KEY=value" ou "KEY=value") ─────────────────
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip().removeprefix('export ')
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _k, _, _v = _line.partition('=')
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')

# ── Démarrer Flask ───────────────────────────────────────────────────────────
print('\n▶ Démarrage Flask (port 5001)...')
_flask_env = os.environ.copy()
_app_dir   = os.path.dirname(os.path.abspath(__file__))
_flask_proc = subprocess.Popen(
    [os.path.join(_app_dir, '.venv', 'bin', 'python'), 'app.py'],
    cwd=_app_dir,
    env=_flask_env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

for _ in range(30):
    time.sleep(0.5)
    try:
        if requests.get(f'{BASE_URL}/login', timeout=2).status_code in (200, 302, 301):
            break
    except Exception:
        pass
else:
    print('❌ Flask ne répond pas après 15s — abandon.')
    _flask_proc.terminate()
    sys.exit(1)
print('  Flask actif.')

# ── Client gspread direct (lectures raw) ────────────────────────────────────
_scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
_gc_direct = gspread.authorize(
    Credentials.from_service_account_info(json.loads(_creds_json), scopes=_scopes)
)

def _sh():
    return _gc_direct.open_by_key(RECRUTEMENT_SHEET_ID)

def _ws():
    return _sh().worksheet('PHASE 1')

def raw_headers():
    return _ws().row_values(1)

def raw_row_by_fileid(file_id):
    rows = _ws().get_all_values()
    for i, row in enumerate(rows):
        if (row[12] if len(row) > 12 else '').strip() == file_id:
            return i + 1, row
    return None, None

# ── Créer une session HTTP authentifiée ─────────────────────────────────────
def make_session(name, email, role='recruteur'):
    s = requests.Session()
    s.post(f'{BASE_URL}/login',
           data={'password': ADMIN_PASSWORD},
           allow_redirects=False)
    s.post(f'{BASE_URL}/select-recruiter',
           data={'recruiter_name': name, 'recruiter_email': email, 'recruiter_role': role},
           allow_redirects=False)
    info = s.get(f'{BASE_URL}/api/recruiter-info').json()
    return s, info

print('\n▶ Création des sessions...')
sess_carole,   info_c = make_session('Carole Andria', 'carole.andria@liliwatt.fr')
sess_nathalie, info_n = make_session('Nathalie',      'nathalie@liliwatt.fr')
print(f'  Carole   : {info_c}')
print(f'  Nathalie : {info_n}')

# ═══════════════════════════════════════════════════════════════════════
# TEST 1 — En-têtes A1:T1 avant/après _get_or_create_phase1
# ═══════════════════════════════════════════════════════════════════════
print('\n╔══ TEST 1 — EN-TÊTES ══════════════════════════════════════════')

try:
    h_before = raw_headers()
    print(f'  AVANT  ({len(h_before)} cols) : {h_before}')
except Exception as e:
    print(f'  AVANT : onglet absent ou erreur — {e}')
    h_before = []

r1 = sess_carole.get(f'{BASE_URL}/api/recrutement/candidats-phase1')
print(f'  GET candidats-phase1 → HTTP {r1.status_code}')

h_after = raw_headers()
print(f'  APRÈS  ({len(h_after)} cols) : {h_after}')

if len(h_after) >= 20 and h_after[19] == 'ATTRIBUE_A':
    print('  ✅ Col T (index 19) = "ATTRIBUE_A"')
else:
    t_found = h_after[19] if len(h_after) > 19 else '(absent)'
    print(f'  ⚠  Col T = "{t_found}" — attendu "ATTRIBUE_A"')

# ═══════════════════════════════════════════════════════════════════════
# TEST 2 — Création de ligne sur CV jamais extrait
# ═══════════════════════════════════════════════════════════════════════
print('\n╠══ TEST 2 — CRÉATION DE LIGNE ════════════════════════════════')

r_inbox = sess_carole.get(f'{BASE_URL}/api/recrutement/cv-inbox?folder=source')
inbox_data = r_inbox.json()
print(f'  cv-inbox source → HTTP {r_inbox.status_code}, {len(inbox_data.get("files", []))} fichier(s)')

test_file = None
for f in inbox_data.get('files', []):
    if not f.get('profilCree', True):
        test_file = f
        break

if not test_file:
    print('  ⚠  Aucun CV sans profil dans source — test 2/3/4 ignorés')
    test_file_id = None
    row_num_after = None
    row_after = None
    orig_email = ''
else:
    test_file_id = test_file['fileId']
    print(f'  CV choisi : "{test_file.get("name", "?")}"  id={test_file_id}')

    # AVANT extraction : vérifier absence de la ligne
    row_num_before, row_before = raw_row_by_fileid(test_file_id)
    print(f'  Ligne AVANT extraction : row={row_num_before}  data={row_before}')

    # Appel cv-extraire
    r_ext = sess_carole.post(f'{BASE_URL}/api/recrutement/cv-extraire',
                             json={'fileId': test_file_id})
    ext_data = r_ext.json()
    print(f'  cv-extraire → HTTP {r_ext.status_code}')
    print(f'  Réponse JSON :')
    for k in ('success', 'ligne_existante', 'attribution_blocked', 'attribution_lost', 'attribue_a', 'illisible', 'doublon_email'):
        print(f'    {k} = {ext_data.get(k)}')

    # Lecture BRUTE de la ligne créée
    row_num_after, row_after = raw_row_by_fileid(test_file_id)
    orig_email = row_after[2] if row_after and len(row_after) > 2 else ''
    print(f'  Ligne créée en row {row_num_after} — Lecture BRUTE A-T :')
    if row_after:
        for col_idx, val in enumerate(row_after):
            if val and col_idx < len(h_after):
                print(f'    col {chr(65+col_idx)} ({h_after[col_idx]}) = "{val}"')

    # Vérifications clés
    if row_after:
        f_col = row_after[5]  if len(row_after) > 5  else ''
        h_col = row_after[7]  if len(row_after) > 7  else ''
        j_col = row_after[9]  if len(row_after) > 9  else ''
        m_col = row_after[12] if len(row_after) > 12 else ''
        t_col = row_after[19] if len(row_after) > 19 else ''
        print(f'  F(STATUT)      = "{f_col}"  (attendu: "NON CONTACTÉ") {"✅" if f_col == "NON CONTACTÉ" else "⚠"}')
        print(f'  H(DATE)        = "{h_col}"')
        print(f'  J(LIEN_CV)     = "{j_col[:60] if j_col else ""}"  {"✅" if j_col else "⚠ vide"}')
        print(f'  M(DRIVE_FILE_ID) = "{m_col}"  {"✅" if m_col == test_file_id else "⚠"}')
        print(f'  T(ATTRIBUE_A)  = "{t_col}"  (attendu: "Carole Andria") {"✅" if t_col == "Carole Andria" else "⚠"}')

# ═══════════════════════════════════════════════════════════════════════
# TEST 3 — Attribution
# ═══════════════════════════════════════════════════════════════════════
if test_file_id:
    print('\n╠══ TEST 3 — ATTRIBUTION ════════════════════════════════════')

    # 3a. T après ouverture Carole (fait en test 2)
    _, row_t3a = raw_row_by_fileid(test_file_id)
    t_3a = row_t3a[19] if row_t3a and len(row_t3a) > 19 else ''
    print(f'  3a. T en DB : "{t_3a}"  (attendu: "Carole Andria") {"✅" if t_3a == "Carole Andria" else "⚠"}')

    # 3b. Nathalie : inbox source → le CV ne doit PAS apparaître
    r_nat = sess_nathalie.get(f'{BASE_URL}/api/recrutement/cv-inbox?folder=source')
    nat_files = r_nat.json().get('files', [])
    nat_has = any(f['fileId'] == test_file_id for f in nat_files)
    print(f'  3b. CV visible dans inbox source Nathalie : {nat_has}  (attendu: False) {"✅" if not nat_has else "⚠"}')

    # 3c. Tous les CV (Nathalie) → doit apparaître avec attribue_a = Carole Andria
    r_tous = sess_nathalie.get(f'{BASE_URL}/api/recrutement/cv-inbox?folder=tous')
    tous_files = r_tous.json().get('files', [])
    found = next((f for f in tous_files if f['fileId'] == test_file_id), None)
    if found:
        print(f'  3c. CV dans Tous les CV : ✅  attribue_a="{found.get("attribue_a")}"  dossier="{found.get("dossier")}"')
    else:
        print(f'  3c. CV dans Tous les CV : ⚠  introuvable ({len(tous_files)} fichiers reçus)')

    # 3d. Nathalie utilise cv-attribuer
    r_attrib = sess_nathalie.post(f'{BASE_URL}/api/recrutement/cv-attribuer',
                                  json={'fileId': test_file_id})
    attrib_data = r_attrib.json()
    print(f'  3d. cv-attribuer Nathalie → HTTP {r_attrib.status_code}  JSON={attrib_data}')

    # Lecture brute T après attribution
    _, row_t3d = raw_row_by_fileid(test_file_id)
    t_3d = row_t3d[19] if row_t3d and len(row_t3d) > 19 else ''
    print(f'  T en DB après attribution Nathalie : "{t_3d}"  (attendu: "Nathalie") {"✅" if t_3d == "Nathalie" else "⚠"}')

    # 3e. Remettre T = Carole Andria pour test 4
    r_back = sess_carole.post(f'{BASE_URL}/api/recrutement/cv-attribuer',
                              json={'fileId': test_file_id})
    print(f'  3e. T remis à Carole Andria : {r_back.json()}')

# ═══════════════════════════════════════════════════════════════════════
# TEST 4 — Réouverture : A-E inchangés, pas de GPT, T inchangé
# ═══════════════════════════════════════════════════════════════════════
if test_file_id and row_after and row_num_after:
    print('\n╠══ TEST 4 — RÉOUVERTURE FICHE EXISTANTE ═══════════════════')

    # Modifier C directement via gspread (simule une correction manuelle)
    ws_direct = _ws()
    ws_direct.update(f'C{row_num_after}', [['test.modification@example.com']], value_input_option='RAW')
    print(f'  C{row_num_after} modifié manuellement : "{orig_email}" → "test.modification@example.com"')

    # Carole réouvre
    r_reopen = sess_carole.post(f'{BASE_URL}/api/recrutement/cv-extraire',
                                json={'fileId': test_file_id})
    reopen_data = r_reopen.json()
    print(f'  cv-extraire (réouverture) → HTTP {r_reopen.status_code}')
    print(f'  ligne_existante = {reopen_data.get("ligne_existante")}  (attendu: True) {"✅" if reopen_data.get("ligne_existante") else "⚠"}')
    print(f'  attribue_a      = "{reopen_data.get("attribue_a")}"')

    # Lecture BRUTE A-T après réouverture
    _, row_t4 = raw_row_by_fileid(test_file_id)
    print(f'  Lecture BRUTE A-E après réouverture :')
    if row_t4:
        for col_idx in range(5):
            hdr = h_after[col_idx] if col_idx < len(h_after) else f'col{col_idx}'
            val = row_t4[col_idx] if len(row_t4) > col_idx else ''
            print(f'    {chr(65+col_idx)} ({hdr}) = "{val}"')
        c_now = row_t4[2] if len(row_t4) > 2 else ''
        t_now = row_t4[19] if len(row_t4) > 19 else ''
        email_preserved = (c_now == 'test.modification@example.com')
        print(f'  C (EMAIL) = "{c_now}"  → modification manuelle préservée : {"✅" if email_preserved else "⚠ ÉCRASÉ"}')
        print(f'  T (ATTRIBUE_A) = "{t_now}"  (attendu: "Carole Andria") {"✅" if t_now == "Carole Andria" else "⚠"}')

# ═══════════════════════════════════════════════════════════════════════
# NETTOYAGE
# ═══════════════════════════════════════════════════════════════════════
print('\n╠══ NETTOYAGE ════════════════════════════════════════════════')

writes_cleanup = []
if test_file_id and row_num_after:
    ws_clean = _ws()
    # Restaurer C
    ws_clean.update(f'C{row_num_after}', [[orig_email]], value_input_option='RAW')
    writes_cleanup.append(f'C{row_num_after} restauré → "{orig_email}"')
    # Vider T
    ws_clean.update(f'T{row_num_after}', [['']], value_input_option='RAW')
    writes_cleanup.append(f'T{row_num_after} remis à ""')
    # Vérification finale
    final = ws_clean.row_values(row_num_after)
    t_final = final[19] if len(final) > 19 else '?'
    c_final = final[2]  if len(final) > 2  else '?'
    print(f'  Lecture finale row {row_num_after} : C="{c_final}"  T="{t_final}"')
    print(f'  T vide : {"✅" if t_final == "" else "⚠"}')

print('\n  BILAN COMPLET DES ÉCRITURES EFFECTUÉES :')
if test_file_id and row_num_after:
    print(f'  LIGNE {row_num_after} créée — file_id : {test_file_id}')
    print(f'  Colonnes écrites lors de la création (append_row A-T) :')
    if row_after:
        for ci, v in enumerate(row_after):
            if v and ci < len(h_after):
                print(f'    {chr(65+ci)} ({h_after[ci]}) = "{v}"')
    print(f'  T{row_num_after} ← "Carole Andria"  (attribution test 2)')
    print(f'  T{row_num_after} ← "Nathalie"        (attribution test 3d)')
    print(f'  T{row_num_after} ← "Carole Andria"  (remise test 3e)')
    print(f'  C{row_num_after} ← "test.modification@example.com"  (write test 4)')
    for w in writes_cleanup:
        print(f'  {w}  (nettoyage)')
else:
    print('  (aucune ligne de test créée)')

print('\n╚═══════════════════════════════════════════════════════════')

_flask_proc.terminate()
print('Flask arrêté.')
