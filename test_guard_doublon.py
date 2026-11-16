"""
test_guard_doublon.py — Garde-fou anti-doublon : trois invitations successives sur GERIC GOURIN.

Sheet : mockée (GOOGLE_CREDS_JSON absent localement — uniquement sur Render).
CRM   : réel — les events sont créés et supprimés dans le vrai calendrier Kevin.
Zoho  : mocké — aucun email envoyé à GERIC GOURIN.
DB    : requêtée directement via Prisma/Node.js pour afficher le compteur brut.

Lancer depuis liliwatt-admin :
    python test_guard_doublon.py
"""

import sys, os, subprocess, json
from unittest.mock import MagicMock, patch

# ── Charger .env (format "export KEY=value" ou "KEY=value") ─────────────────
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip().removeprefix('export ')
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _k, _, _v = _line.partition('=')
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# ── Neutraliser uniquement les modules non installés ────────────────────────
for _mod in ['google_meet_service', 'mail_template']:
    sys.modules.setdefault(_mod, MagicMock())

_mt = sys.modules['mail_template']
for _name in ('mail_liliwatt', 'paragraphe', 'accent', 'bloc', 'tableau_infos',
              'bouton', 'signature_equipe', 'titre_section', 'ROSE', 'TEXTE_FORT', 'ACCENT'):
    setattr(_mt, _name, MagicMock(return_value='<mocked>'))

import requests as _real_requests

# Capturer avant tout patch : les patchs modifient l'attribut du module,
# pas ces références directes aux fonctions.
_real_post   = _real_requests.post
_real_delete = _real_requests.delete

import app as admin_app  # noqa: E402

CRM_API_URL   = os.environ.get('CRM_API_URL', '').rstrip('/')
CRM_API_TOKEN = os.environ.get('CRM_API_TOKEN', '')
CRM_DIR       = '/Users/strategyglobal/Desktop/liliwatt-crm'

print(f'CRM_API_URL   : {CRM_API_URL or "(vide)"}')
print(f'CRM_API_TOKEN : {"(configuré)" if CRM_API_TOKEN else "(vide)"}')

# ── Compteur DB via Prisma/Node.js ────────────────────────────────────────────
_NODE_QUERY = r"""
const fs = require('fs');
let dbUrl = '';
for (const line of fs.readFileSync('%s/.env', 'utf8').split('\n')) {
  const t = line.trim();
  if (t.startsWith('DATABASE_URL')) {
    dbUrl = t.slice(t.indexOf('=')+1).trim().replace(/^["']|["']$/g,'');
    break;
  }
}
const { PrismaClient } = require('./node_modules/@prisma/client');
const p = new PrismaClient({ datasources: { db: { url: dbUrl } } });
p.calendarEvent.findMany({
  where: { title: { contains: 'Gourin', mode: 'insensitive' } },
  select: { id: true, title: true, startTime: true },
  orderBy: { startTime: 'asc' }
}).then(evts => { console.log(JSON.stringify(evts)); })
  .catch(e => { console.error('DB_ERROR:' + e.message); process.exit(1); })
  .finally(() => p.$disconnect());
""" % CRM_DIR

def _db_count(label):
    """Requête DB réelle, affiche id + startTime de chaque event 'Gourin'."""
    result = subprocess.run(
        ['node', '-e', _NODE_QUERY],
        capture_output=True, text=True,
        cwd=CRM_DIR, timeout=20
    )
    if result.returncode != 0 or result.stdout.startswith('DB_ERROR'):
        print(f'  [{label}] DB inaccessible : {result.stderr or result.stdout}')
        return
    events = json.loads(result.stdout)
    print(f'  [{label}] DB — {len(events)} event(s) title∋"Gourin" :')
    for e in events:
        print(f'    id: {e["id"]}  |  start: {e["startTime"]}  |  title: {e["title"]}')
    if not events:
        print(f'    (aucun)')

# ── Mock Sheet : simule la ligne GERIC GOURIN ────────────────────────────────
EMAIL_TEST = 'test.gericgourin@example.com'
FILE_ID    = 'fake_file_id_geric_gourin_test'

class _MockWs:
    def __init__(self):
        self._P = ''

    def _make_row(self):
        row = [''] * 16
        row[0] = 'GOURIN'; row[1] = 'GERIC'
        row[2] = EMAIL_TEST; row[3] = '0600000000'
        row[12] = FILE_ID; row[15] = self._P
        return row

    def get_all_values(self):
        return [[''] * 16, self._make_row()]

    def row_values(self, row_num):
        rows = self.get_all_values()
        return rows[row_num - 1] if 0 < row_num <= len(rows) else []

    def update(self, cell_range, values, **kwargs):
        if cell_range.upper().startswith('P') and values and values[0]:
            self._P = values[0][0]

_mock_ws = _MockWs()
_mock_gc = MagicMock()
_mock_gc.open_by_key.return_value = MagicMock()

# ── Wrapper DELETE : log la réponse réelle du garde-fou ──────────────────────
_delete_log = []  # (event_id, raw_response_dict)

def _logging_delete(url, **kwargs):
    resp = _real_delete(url, **kwargs)
    if '/api/external/calendar-event/' in url:
        event_id = url.rstrip('/').split('/')[-1]
        try:
            data = resp.json()
        except Exception:
            data = {}
        if data.get('alreadyDeleted'):
            verdict = '⚠  alreadyDeleted (non trouvé en DB — pas supprimé par CE DELETE)'
        elif data.get('success'):
            verdict = '✅ success (trouvé en DB et supprimé par CE DELETE)'
        else:
            verdict = f'❌ erreur : {data}'
        print(f'  [DELETE GUARD] {event_id[:30]}… → {verdict}')
        _delete_log.append((event_id, data))
    return resp

# ── Mock sélectif POST : Zoho muet, CRM réel ─────────────────────────────────
def _selective_post(url, **kwargs):
    if 'zoho' in url.lower():
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {}
        return resp
    return _real_post(url, **kwargs)

# ── Invitation ────────────────────────────────────────────────────────────────
def _invite(date_session, heure_session):
    with patch('app.get_sheets_client',        return_value=_mock_gc), \
         patch('app._get_or_create_phase1',    return_value=_mock_ws), \
         patch('app.get_zoho_token',           return_value='fake_zoho_token'), \
         patch('app._zoho_get_account_id',     return_value='fake_account'), \
         patch('app.requests.post',            side_effect=_selective_post), \
         patch('app.requests.delete',          side_effect=_logging_delete):
        return admin_app._send_invitation_visio(
            email=EMAIL_TEST, prenom='GERIC', nom='GOURIN',
            telephone='', experience='',
            date_session=date_session, heure_session=heure_session,
            file_id=FILE_ID, reprogrammation=False, ecrire_statut=False,
        )

# ════════════════════════════════════════════════════════════════════════════
print('\n╔══ ÉTAT INITIAL ════════════════════════════════════════════════════════')
_db_count('avant tout')
print(f'  col P mock   : "{_mock_ws._P or "(vide)"}"')

DATES = [
    ('2027-01-05', '10:00'),
    ('2027-01-12', '14:00'),
    ('2027-01-19', '09:00'),
]

event_ids = []

for n, (date_s, heure_s) in enumerate(DATES, 1):
    print(f'\n╠══ INVITATION {n} — {date_s} {heure_s} ════════════════════════════════════')

    result = _invite(date_s, heure_s)
    P_apres = _mock_ws._P
    event_ids.append(P_apres)

    _db_count(f'après invitation {n}')
    print(f'  col P mock après : {P_apres[:45] if P_apres else "(vide)"}')
    print(f'  reprogramme      : {result.get("reprogramme")}  (attendu: {"False" if n == 1 else "True"})')

    if result.get('reprogramme'):
        msg_ui = (f'Entretien reprogrammé au {result["date_lisible"]} '
                  f'à {result["heure"]} — l\'ancien a été supprimé de l\'agenda')
    else:
        msg_ui = f'Invitation envoyée à {EMAIL_TEST}'
    if result.get('delete_warning'):
        msg_ui += f' · ⚠ {result["delete_warning"]}'
    print(f'  Interface Carole : « {msg_ui} »')

# ── Nettoyage ────────────────────────────────────────────────────────────────
last_id = event_ids[-1] if event_ids else ''
if last_id:
    print(f'\n╠══ NETTOYAGE ════════════════════════════════════════════════════════════')
    r = _real_delete(
        f'{CRM_API_URL}/api/external/calendar-event/{last_id}',
        headers={'Authorization': f'Bearer {CRM_API_TOKEN}'}, timeout=15
    )
    chk = r.json()
    print(f'  DELETE event final : {chk}')
    _db_count('après nettoyage')

# ── RÉSUMÉ ────────────────────────────────────────────────────────────────────
print('\n╠══ RÉSUMÉ ═══════════════════════════════════════════════════════════════')
all_distinct = len(set(e for e in event_ids if e)) == len(event_ids) == 3
for n, eid in enumerate(event_ids, 1):
    print(f'  Invitation {n} → eventId : {eid[:50] if eid else "(vide)"}')
print(f'  Tous les eventId distincts : {"✅ oui" if all_distinct else "⚠  non"}')
print(f'  DELETE guards appelés      : {len(_delete_log)}')
real_deletes = [(eid, d) for eid, d in _delete_log if not d.get('alreadyDeleted') and d.get('success')]
print(f'  DELETEs ayant trouvé+supprimé : {len(real_deletes)} (attendu: 2)')
print('╚═══════════════════════════════════════════════════════════════════════')
