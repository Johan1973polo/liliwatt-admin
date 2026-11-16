"""
test_zoho_cache.py — Vérifie le cache et les messages d'erreur de get_zoho_token().

Lancer depuis le répertoire liliwatt-admin :
    python test_zoho_cache.py

Dépendances : uniquement stdlib + modules déjà installés dans le venv.
Aucun appel réseau, aucune lecture de .env.
"""

import sys
import os
from unittest.mock import MagicMock, patch

# ── Neutraliser les imports lourds avant de charger app ─────────────────────
for _mod in [
    'google_meet_service',
    'mail_template',
    'gspread',
    'google',
    'google.oauth2',
    'google.oauth2.service_account',
    'googleapiclient',
    'googleapiclient.discovery',
]:
    sys.modules.setdefault(_mod, MagicMock())

# mail_template : app utilise ces noms à l'import
_mt = sys.modules['mail_template']
for _name in ('mail_liliwatt', 'paragraphe', 'accent', 'bloc', 'tableau_infos',
              'bouton', 'signature_equipe', 'titre_section', 'ROSE',
              'TEXTE_FORT', 'ACCENT'):
    setattr(_mt, _name, MagicMock())

# Variables d'environnement minimales (valeurs fictives, jamais de vrais secrets)
for _k, _v in [
    ('ZOHO_CLIENT_ID',     'test_client_id'),
    ('ZOHO_CLIENT_SECRET', 'test_client_secret'),
    ('ZOHO_REFRESH_TOKEN', 'test_refresh_token'),
    ('ZOHO_ORG_ID',        'test_org_id'),
    ('ZOHO_ACCOUNT_ID',    '8439060000000002002'),
    ('SECRET_KEY',         'test-secret-key'),
    ('ADMIN_PASSWORD',     'test'),
]:
    os.environ.setdefault(_k, _v)

import app as admin_app  # noqa: E402  (import après les patches)

FAKE_TOKEN = 'fake_access_token_xyz123'


def _reset_cache():
    admin_app._zoho_token_cache = {'token': None, 'expires_at': 0.0}


# ── TEST 1 : un seul appel HTTP pour 3 demandes successives ─────────────────
def test_cache_un_seul_appel():
    _reset_cache()
    call_count = 0

    def mock_post(url, **kwargs):
        nonlocal call_count
        resp = MagicMock()
        if 'oauth/v2/token' in url:
            call_count += 1
            resp.status_code = 200
            resp.json.return_value = {'access_token': FAKE_TOKEN}
        return resp

    with patch('app.requests.post', side_effect=mock_post):
        tokens = [admin_app.get_zoho_token() for _ in range(3)]

    assert all(t == FAKE_TOKEN for t in tokens), f"Token inattendu : {tokens}"
    assert call_count == 1, (
        f"ÉCHEC : {call_count} appel(s) au endpoint token au lieu de 1\n"
        f"Le cache ne fonctionne pas."
    )
    print(f"✅ TEST 1 — {call_count} seul appel HTTP pour 3 demandes. Cache opérationnel.")


# ── TEST 2 : message « Zoho injoignable (réseau) » ──────────────────────────
def test_erreur_reseau():
    _reset_cache()
    import requests as req

    with patch('app.requests.post', side_effect=req.exceptions.ConnectionError('host down')):
        try:
            admin_app.get_zoho_token()
            assert False, "Aurait dû lever une exception"
        except Exception as e:
            msg = str(e)
            assert 'réseau' in msg, f"Message inattendu : « {msg} »"
            print(f"✅ TEST 2 — Cas réseau     : « {msg} »")


# ── TEST 3 : message « Zoho a refusé l'authentification » ───────────────────
def test_erreur_authentification():
    _reset_cache()

    def mock_refus(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 400
        resp.json.return_value = {'error': 'invalid_code'}
        return resp

    with patch('app.requests.post', side_effect=mock_refus):
        try:
            admin_app.get_zoho_token()
            assert False, "Aurait dû lever une exception"
        except Exception as e:
            msg = str(e)
            assert 'refusé' in msg and 'invalid_code' in msg, f"Message inattendu : « {msg} »"
            print(f"✅ TEST 3 — Cas refus auth : « {msg} »")


# ── TEST 4 : message « Zoho a répondu sans token » ──────────────────────────
def test_erreur_sans_token():
    _reset_cache()

    def mock_sans_token(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 503
        resp.json.return_value = {}   # pas d'error, pas d'access_token
        return resp

    with patch('app.requests.post', side_effect=mock_sans_token):
        try:
            admin_app.get_zoho_token()
            assert False, "Aurait dû lever une exception"
        except Exception as e:
            msg = str(e)
            assert 'HTTP 503' in msg, f"Message inattendu : « {msg} »"
            print(f"✅ TEST 4 — Cas sans token : « {msg} »")


# ── TEST 5 : cache invalidé après une erreur ────────────────────────────────
def test_cache_invalide_apres_erreur():
    """Après un refus Zoho, la tentative suivante repart bien vers Zoho (pas de cache corrompu)."""
    _reset_cache()
    import requests as req

    # Premier appel → erreur réseau
    with patch('app.requests.post', side_effect=req.exceptions.ConnectionError):
        try:
            admin_app.get_zoho_token()
        except Exception:
            pass

    assert admin_app._zoho_token_cache['token'] is None, (
        "ÉCHEC : un token corrompu est resté en cache après une erreur"
    )

    # Deuxième appel → succès
    call_count = 0
    def mock_ok(url, **kwargs):
        nonlocal call_count
        resp = MagicMock()
        if 'oauth/v2/token' in url:
            call_count += 1
            resp.status_code = 200
            resp.json.return_value = {'access_token': FAKE_TOKEN}
        return resp

    with patch('app.requests.post', side_effect=mock_ok):
        token = admin_app.get_zoho_token()

    assert token == FAKE_TOKEN, f"Token inattendu après récupération : {token}"
    assert call_count == 1, f"Devrait avoir fait 1 appel après récupération, fait {call_count}"
    print("✅ TEST 5 — Cache invalidé après erreur, récupération propre.")


# ── Lancement ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("── Tests get_zoho_token() ──────────────────────────────")
    test_cache_un_seul_appel()
    test_erreur_reseau()
    test_erreur_authentification()
    test_erreur_sans_token()
    test_cache_invalide_apres_erreur()
    print("────────────────────────────────────────────────────────")
    print("✅ Tous les tests passent.")
