from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import requests
import json
import uuid
from functools import wraps
from datetime import datetime, timedelta
from google_meet_service import create_referent_meet_room

def parse_float(val):
    if not val:
        return 0.0
    try:
        return float(str(val).replace(',', '.').replace(' ', '').replace('\u202f', ''))
    except:
        return 0.0

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'liliwatt-admin-secret-2026')

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID', '')
ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET', '')
ZOHO_REFRESH_TOKEN = os.environ.get('ZOHO_REFRESH_TOKEN', '')
ZOHO_ORG_ID = os.environ.get('ZOHO_ORG_ID', '')

def get_zoho_token():
    r = requests.post('https://accounts.zoho.eu/oauth/v2/token', data={
        'refresh_token': ZOHO_REFRESH_TOKEN,
        'client_id': ZOHO_CLIENT_ID,
        'client_secret': ZOHO_CLIENT_SECRET,
        'grant_type': 'refresh_token'
    })
    return r.json().get('access_token')



def save_to_sheet(prenom, nom, email, password, poste, drive_folder_id='', referent_email='', token_rgpd='', role='vendeur'):
    """Enregistre le commercial dans Google Sheets"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        import json
        from datetime import datetime

        creds_json = os.environ.get('GOOGLE_CREDS_JSON', '')
        if not creds_json:
            print("⚠️ GOOGLE_CREDS_JSON non défini")
            return False

        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        gc = gspread.authorize(creds)
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1
        rgpd_link = f'https://liliwatt-courtier.onrender.com/rgpd/{token_rgpd}' if token_rgpd else ''
        ws.append_row([
            nom.upper(),
            prenom.capitalize(),
            password,
            email,
            poste,
            drive_folder_id,
            referent_email,
            token_rgpd,
            rgpd_link,
            role,
            'actif'
        ])
        print(f"✅ {nom} {prenom} enregistré dans Google Sheets (token RGPD: {token_rgpd})")
        return True
    except Exception as e:
        print(f"⚠️ Erreur Google Sheets : {e}")
        return False

def orpheliner_vendeurs(ancien_referent_email):
    """Détache tous les vendeurs de leur ancien référent."""
    try:
        gc = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        orphelins = []
        for i, row in enumerate(rows):
            if len(row) > 6 and row[6].strip().lower() == ancien_referent_email.lower():
                ws.update_cell(i + 1, 7, '')
                orphelins.append(row[3].strip().lower())
                print(f'  → Vendeur orphelin : {row[3]}')
        print(f'✅ {len(orphelins)} vendeur(s) orphelin(s) après départ de {ancien_referent_email}')
        if orphelins:
            crm_url = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
            crm_key = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
            for email_v in orphelins:
                try:
                    requests.post(f'{crm_url}/api/crm/assign-referent',
                        headers={'X-API-Key': crm_key, 'Content-Type': 'application/json'},
                        json={'vendeur_email': email_v, 'referent_email': None}, timeout=10)
                except: pass
            print(f'✅ CRM Neon : {len(orphelins)} vendeurs mis à referentId=null')
        return orphelins
    except Exception as e:
        print(f'❌ Erreur orpheliner_vendeurs : {e}')
        return []


def get_sheets_client():
    """Retourne un client gspread authentifié"""
    import gspread
    from google.oauth2.service_account import Credentials
    creds_json = os.environ.get('GOOGLE_CREDS_JSON', '')
    if not creds_json:
        return None
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    )
    return gspread.authorize(creds)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def make_signature(prenom, nom, poste, telephone, email):
    return f"""<table cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,sans-serif;max-width:480px;">
  <tr><td colspan="2" style="border-top:4px solid #7c3aed;padding-bottom:12px;"></td></tr>
  <tr><td colspan="2" style="font-size:16px;font-weight:700;color:#1e1b4b;padding-bottom:2px;">{prenom} {nom}</td></tr>
  <tr><td colspan="2" style="font-size:10px;font-weight:600;color:#7c3aed;letter-spacing:1.5px;text-transform:uppercase;padding-bottom:2px;">{poste}</td></tr>
  <tr><td colspan="2" style="font-size:10px;font-weight:600;color:#7c3aed;letter-spacing:1px;text-transform:uppercase;padding-bottom:12px;">LILIWATT &mdash; Courtage &Eacute;nergie B2B &amp; B2C</td></tr>
  <tr>
    <td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;vertical-align:top;">T&eacute;l</td>
    <td style="font-size:13px;"><a href="tel:{telephone.replace(' ','')}" style="color:#1e1b4b;text-decoration:none;font-weight:600;">{telephone}</a></td>
  </tr>
  <tr>
    <td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;vertical-align:top;">Email</td>
    <td style="font-size:13px;"><a href="mailto:{email}" style="color:#7c3aed;text-decoration:none;font-weight:600;">{email}</a></td>
  </tr>
  <tr>
    <td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;vertical-align:top;">Web</td>
    <td style="font-size:13px;"><a href="https://liliwatt.fr" style="color:#7c3aed;text-decoration:none;font-weight:600;">www.liliwatt.fr</a></td>
  </tr>
  <tr>
    <td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;vertical-align:top;">Adresse</td>
    <td style="font-size:13px;color:#374151;">59 rue de Ponthieu, Bureau 326<br>75008 Paris</td>
  </tr>
  <tr><td colspan="2" style="padding-top:12px;border-bottom:1px solid #7c3aed;"></td></tr>
  <tr><td colspan="2" style="font-size:11px;color:#6b7280;padding-top:10px;">Courtier &Eacute;nergie B2B &amp; B2C<br><span style="color:#7c3aed;font-weight:700;">18% d'&eacute;conomies en moyenne</span> &mdash; Sans engagement &bull; Sans coupure &bull; 18+ fournisseurs compar&eacute;s</td></tr>
  <tr><td colspan="2" style="border-bottom:2px solid #7c3aed;padding-top:12px;"></td></tr>
</table>"""


def generate_password():
    """Génère un mot de passe sécurisé automatiquement"""
    import random
    import string
    majuscules = random.choices(string.ascii_uppercase, k=2)
    minuscules = random.choices(string.ascii_lowercase, k=4)
    chiffres = random.choices(string.digits, k=3)
    speciaux = random.choices('@#$!%&', k=2)
    all_chars = majuscules + minuscules + chiffres + speciaux
    random.shuffle(all_chars)
    return ''.join(all_chars)

def send_welcome_email(prenom, nom, email, password, poste='', telephone='', email_perso='', account_id_zoho='', token_rgpd='', referent_email=''):
    """Envoie l'email de bienvenue via API Zoho Mail"""
    try:
        destinataire = email_perso if email_perso else email
        email_liliwatt = email

        token = get_zoho_token()
        if not token:
            print("⚠️ Token Zoho non obtenu pour email")
            return False

        # Chercher le nom du référent
        referent_name = None
        if referent_email:
            try:
                gc = get_sheets_client()
                if gc:
                    sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
                    ws = gc.open_by_key(sheet_id).sheet1
                    for row in ws.get_all_values()[1:]:
                        if len(row) > 3 and row[3].strip().lower() == referent_email.strip().lower():
                            referent_name = f"{row[1]} {row[0]}".strip()
                            break
            except:
                referent_name = referent_email

        referent_block = ''
        if referent_name:
            referent_block = f"""<div style="background:#f0fdf4;border-radius:16px;padding:28px;margin-bottom:24px;border:1px solid #bbf7d0;">
    <h3 style="color:#166534;margin:0 0 8px;font-size:17px;">👤 Votre référent</h3>
    <p style="color:#166534;margin:0;font-size:14px;line-height:1.8;">
      <strong>{referent_name}</strong> est votre référent dédié chez LILIWATT. Il est disponible via la messagerie interne du CRM pour vous accompagner dans la prise en main de vos outils, répondre à vos questions et vous guider lors de vos premières semaines d'activité.<br><br>
      N'hésitez pas à le contacter dès votre connexion.
    </p>
  </div>"""

        html_body = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f5f3ff;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:40px 20px;">
  <div style="background:linear-gradient(135deg,#7c3aed,#d946ef);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <h1 style="color:white;margin:0;font-size:32px;font-weight:700;letter-spacing:2px;">⚡ LILIWATT</h1>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px;">Cabinet de courtage en énergie B2B</p>
  </div>
  <div style="background:white;border-radius:16px;padding:32px;margin-bottom:24px;border:1px solid #e9d5ff;">
    <h2 style="color:#7c3aed;margin:0 0 16px;font-size:22px;">Bienvenue {prenom} ! 🎉</h2>
    <p style="color:#374151;line-height:1.8;margin:0;font-size:15px;">
      Nous sommes ravis de vous accueillir dans l'équipe LILIWATT.<br><br>
      Votre espace de travail est prêt. <strong>Votre point d'entrée unique est le CRM LILIWATT</strong> — depuis ce tableau de bord personnel, vous accédez directement à tous vos outils métier, vos modules de formation et votre messagerie interne.<br><br>
      Dès votre première connexion, vous trouverez vos accès pré-configurés et vos modules de formation disponibles pour vous permettre de démarrer rapidement.
    </p>
  </div>
  <div style="background:linear-gradient(135deg,#7c3aed,#d946ef);border-radius:16px;padding:36px;margin-bottom:24px;text-align:center;">
    <h3 style="color:white;margin:0 0 8px;font-size:22px;">🖥️ Votre espace CRM LILIWATT</h3>
    <p style="color:rgba(255,255,255,0.85);margin:0 0 6px;font-size:14px;">Tableau de bord — Formation — Messagerie — Outils métier</p>
    <p style="color:rgba(255,255,255,0.75);margin:0 0 24px;font-size:13px;">Connectez-vous dès maintenant pour découvrir votre espace et commencer votre formation.</p>
    <a href="https://liliwatt-crm-8ofi.vercel.app" style="background:white;color:#7c3aed;padding:16px 40px;border-radius:50px;text-decoration:none;font-weight:700;font-size:16px;display:inline-block;letter-spacing:0.5px;">Accéder à mon espace →</a>
    <div style="margin-top:28px;background:rgba(0,0,0,0.2);border-radius:12px;padding:18px;">
      <p style="color:rgba(255,255,255,0.9);margin:0 0 8px;font-size:14px;">📧 Identifiant : <strong>{email_liliwatt}</strong></p>
      <p style="color:rgba(255,255,255,0.9);margin:0;font-size:14px;">🔑 Mot de passe : <strong>{password}</strong></p>
    </div>
  </div>
  <div style="background:white;border-radius:16px;padding:32px;margin-bottom:24px;border:1px solid #e9d5ff;">
    <h3 style="color:#374151;margin:0 0 6px;font-size:17px;">Vos outils accessibles depuis le CRM</h3>
    <p style="color:#6b7280;margin:0 0 20px;font-size:13px;">Tous vos outils sont accessibles en un clic depuis votre tableau de bord personnel.</p>
    <div style="padding:16px;background:#f5f3ff;border-radius:12px;margin-bottom:12px;">
      <p style="margin:0 0 4px;font-weight:700;color:#374151;font-size:15px;">📞 Base Prospection</p>
      <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.6;">Vos prospects qualifiés avec coordonnées téléphoniques, secteur d'activité et statut d'appel. Commencez à prospecter dès le premier jour.</p>
    </div>
    <div style="padding:16px;background:#f5f3ff;border-radius:12px;">
      <p style="margin:0 0 4px;font-weight:700;color:#374151;font-size:15px;">⚡ Outil Courtage — Extracteur &amp; Comparatif</p>
      <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.6;">Déposez la facture de votre prospect, notre outil extrait automatiquement les données et génère un comparatif personnalisé en moins de 2 minutes.</p>
    </div>
  </div>
  <div style="background:white;border-radius:16px;padding:28px;margin-bottom:24px;border:1px solid #e9d5ff;">
    <h3 style="color:#374151;margin:0 0 6px;font-size:17px;">✉️ Votre boîte mail professionnelle</h3>
    <p style="color:#6b7280;margin:0 0 16px;font-size:13px;">Votre adresse email professionnelle est active. Utilisez-la pour toutes vos communications clients.</p>
    <div style="background:#f5f3ff;border-radius:12px;padding:16px;">
      <p style="margin:0 0 8px;font-size:14px;color:#374151;">🌐 Accès webmail : <a href="https://mail.zoho.eu" style="color:#7c3aed;font-weight:600;">mail.zoho.eu</a></p>
      <p style="margin:0 0 8px;font-size:14px;color:#374151;">📧 Email : <strong>{email_liliwatt}</strong></p>
      <p style="margin:0;font-size:14px;color:#374151;">🔑 Mot de passe : <strong>{password}</strong></p>
    </div>
  </div>
  {referent_block}
  <div style="background:white;border-radius:16px;padding:28px;margin-bottom:24px;border:1px solid #e9d5ff;">
    <h3 style="color:#374151;margin:0 0 16px;font-size:17px;">🚀 Vos prochaines étapes</h3>
    <div style="display:flex;gap:16px;margin-bottom:14px;align-items:flex-start;"><div style="background:#7c3aed;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;">1</div><p style="margin:0;color:#374151;font-size:14px;line-height:1.6;"><strong>Connectez-vous au CRM</strong> avec vos identifiants ci-dessus</p></div>
    <div style="display:flex;gap:16px;margin-bottom:14px;align-items:flex-start;"><div style="background:#7c3aed;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;">2</div><p style="margin:0;color:#374151;font-size:14px;line-height:1.6;"><strong>Commencez votre formation</strong> — les modules sont déverrouillés progressivement par votre référent</p></div>
    <div style="display:flex;gap:16px;margin-bottom:14px;align-items:flex-start;"><div style="background:#7c3aed;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;">3</div><p style="margin:0;color:#374151;font-size:14px;line-height:1.6;"><strong>Découvrez vos outils</strong> — prospection et courtage accessibles depuis votre tableau de bord</p></div>
    <div style="display:flex;gap:16px;align-items:flex-start;"><div style="background:#d946ef;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;">4</div><p style="margin:0;color:#374151;font-size:14px;line-height:1.6;"><strong>Lancez vos premiers appels</strong> — votre base de prospects qualifiés vous attend</p></div>
  </div>
  <div style="text-align:center;padding:24px 0;">
    <div style="background:linear-gradient(135deg,#7c3aed,#d946ef);border-radius:12px;padding:20px;margin-bottom:20px;">
      <p style="color:white;margin:0;font-size:14px;font-weight:600;">Une question ? Contactez-nous</p>
      <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:13px;">contact@liliwatt.fr — 01 84 16 08 56</p>
    </div>
    <p style="color:#9ca3af;font-size:12px;margin:0;">LILIWATT — LILISTRAT STRATÉGIE SAS</p>
    <p style="color:#9ca3af;font-size:12px;margin:4px 0 0;">59 rue de Ponthieu, Bureau 326 — 75008 Paris</p>
    <p style="color:#9ca3af;font-size:12px;margin:4px 0 0;">www.liliwatt.fr</p>
  </div>
</div>
</body></html>"""

        account_id = os.environ.get('ZOHO_ACCOUNT_ID', '8439060000000002002')
        print(f"📧 Envoi email bienvenue à {destinataire} depuis account_id: {account_id}")

        send_r = requests.post(
            f'https://mail.zoho.eu/api/accounts/{account_id}/messages',
            headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
            json={
                'fromAddress': 'bo@liliwatt.fr',
                'toAddress': destinataire,
                'subject': f'Bienvenue chez LILIWATT — Vos accès {prenom} 🎉',
                'content': html_body,
                'mailFormat': 'html'
            },
            timeout=15
        )

        result = send_r.json()
        print(f"✅ Email bienvenue envoyé - status: {send_r.status_code} - response: {str(result)[:100]}")
        return True

    except Exception as e:
        print(f"⚠️ Erreur email bienvenue : {e}")
        import traceback; traceback.print_exc()
        return False


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'Mot de passe incorrect'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/create-drive-folder', methods=['POST'])
@login_required
def create_drive_folder():
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials as SACredentials
        import base64

        d = request.get_json()
        prenom = d.get('prenom', '').strip()
        nom = d.get('nom', '').strip()
        if not prenom or not nom:
            return jsonify({'success': False, 'error': 'Prénom et nom requis'})

        VENDEURS_PARENT_ID = '157Sol6u32W0loIEv8CmYT3uoDaGyZ7q6'
        SHARED_DRIVE_ID = '0ACKaJQqRlmwgUk9PVA'
        folder_name = f"{prenom.capitalize()} {nom.upper()}"

        # Charger credentials Drive (3 sources possibles)
        creds_b64 = os.environ.get('GOOGLE_DRIVE_CREDS_BASE64', '')
        creds_json_env = os.environ.get('GOOGLE_CREDS_JSON', '')
        if creds_b64:
            creds_dict = json.loads(base64.b64decode(creds_b64).decode())
        elif creds_json_env:
            creds_dict = json.loads(creds_json_env)
        else:
            with open(os.path.join(os.path.dirname(__file__), 'liliwatt-eddcc0bc9e18.json')) as f:
                creds_dict = json.load(f)

        creds = SACredentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/drive']
        )
        drive = build('drive', 'v3', credentials=creds)

        # Créer le dossier principal du vendeur dans le Shared Drive
        vendeur_folder = drive.files().create(
            body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [VENDEURS_PARENT_ID], 'driveId': SHARED_DRIVE_ID},
            fields='id', supportsAllDrives=True
        ).execute()
        vendeur_id = vendeur_folder['id']

        # Créer les 3 sous-dossiers dans le Shared Drive
        for sub in ['CLIENT EN ATTENTE', 'CLIENTS SIGNÉS', 'CLIENTS PERDUS']:
            drive.files().create(
                body={'name': sub, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [vendeur_id], 'driveId': SHARED_DRIVE_ID},
                fields='id', supportsAllDrives=True
            ).execute()

        link = f"https://drive.google.com/drive/folders/{vendeur_id}"
        print(f"✅ Dossier Drive créé : {folder_name} → {vendeur_id}")
        return jsonify({'success': True, 'drive_folder_id': vendeur_id, 'link': link})

    except Exception as e:
        import traceback
        print(f"⚠️ Erreur création dossier Drive : {e}")
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})

@app.route('/api/update-rgpd-links')
@login_required
def update_rgpd_links():
    try:
        gc = get_sheets_client()
        if not gc:
            return jsonify({'success': False, 'error': 'Google Sheets non configuré'})
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        updated = []
        batch = []
        for i, row in enumerate(rows):
            token = row[7] if len(row) > 7 else ''
            link = row[8] if len(row) > 8 else ''
            email = row[3] if len(row) > 3 else ''
            if token and not link and '@' in email:
                rgpd_link = f'https://liliwatt-courtier.onrender.com/rgpd/{token}'
                batch.append({'range': f'I{i+1}', 'values': [[rgpd_link]]})
                updated.append({'email': email, 'link': rgpd_link})
        if batch:
            ws.batch_update(batch, value_input_option='RAW')
        return jsonify({'success': True, 'updated': len(updated), 'details': updated})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/signature/<token_rgpd>')
def signature_page(token_rgpd):
    try:
        gc = get_sheets_client()
        if not gc:
            return 'Erreur configuration', 500
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        vendeur = None
        for row in rows:
            if len(row) > 7 and row[7] == token_rgpd and '@' in (row[3] or ''):
                vendeur = {'nom': row[0], 'prenom': row[1], 'email': row[3], 'poste': row[4], 'telephone': ''}
                break
        if not vendeur:
            return 'Vendeur introuvable.', 404
        sig_html = make_signature(vendeur['prenom'], vendeur['nom'], vendeur['poste'], vendeur['telephone'], vendeur['email'])
        return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signature — {vendeur['prenom']} {vendeur['nom']}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f5f3ff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.card{{background:#fff;border-radius:16px;padding:40px;max-width:560px;width:100%;box-shadow:0 4px 24px rgba(124,58,237,.1)}}
h1{{color:#1e1b4b;font-size:20px;margin-bottom:6px}}
.sub{{color:#6b7280;font-size:13px;margin-bottom:24px}}
.sig-box{{border:1.5px solid #e9d5ff;border-radius:10px;padding:20px;margin-bottom:20px;background:#faf5ff}}
.btn{{display:block;width:100%;padding:14px;background:linear-gradient(135deg,#7c3aed,#d946ef);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;transition:transform .15s}}
.btn:hover{{transform:translateY(-1px)}}
.msg{{text-align:center;margin-top:12px;font-size:14px;color:#16a34a;font-weight:600;display:none}}
</style></head><body>
<div class="card">
<h1>Signature email de {vendeur['prenom']} {vendeur['nom']}</h1>
<p class="sub">Cliquez sur le bouton pour copier la signature dans votre presse-papier, puis collez-la dans Zoho Mail &rarr; Param&egrave;tres &rarr; Signatures.</p>
<div class="sig-box" id="sigBox">{sig_html}</div>
<button class="btn" onclick="copySig()">&#128203; Copier la signature</button>
<p class="msg" id="msg">&#10003; Signature copi&eacute;e !</p>
</div>
<script>
async function copySig(){{
  const box=document.getElementById('sigBox');
  try{{
    const blob=new Blob([box.innerHTML],{{type:'text/html'}});
    await navigator.clipboard.write([new ClipboardItem({{'text/html':blob}})]);
  }}catch(e){{
    const r=document.createRange();r.selectNodeContents(box);
    const s=window.getSelection();s.removeAllRanges();s.addRange(r);
    document.execCommand('copy');s.removeAllRanges();
  }}
  const m=document.getElementById('msg');m.style.display='block';
  setTimeout(()=>m.style.display='none',3000);
}}
</script></body></html>"""
    except Exception as e:
        return f'Erreur : {e}', 500

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/vendeurs')
@login_required
def list_vendeurs_api():
    try:
        gc = get_sheets_client()
        if not gc:
            return jsonify({'success': False, 'error': 'Sheets non configuré'})
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        vendeurs = []
        for row in rows[1:]:  # skip header
            if len(row) > 3 and '@' in row[3]:
                statut = (row[10] if len(row) > 10 else 'actif').strip().lower()
                if statut == 'supprime':
                    continue
                vendeurs.append({
                    'nom': row[0],
                    'prenom': row[1],
                    'email': row[3],
                    'referent_email': (row[6] if len(row) > 6 else '').strip(),
                    'role': (row[9] if len(row) > 9 else 'vendeur').strip().lower(),
                    'statut': statut
                })
        return jsonify({'success': True, 'vendeurs': vendeurs})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/referents-avec-equipe')
@login_required
def referents_avec_equipe():
    try:
        gc = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        # Collecter les référents par colonne J (role) ET colonne G (fallback)
        ref_emails = set()
        for row in rows[1:]:
            # Méthode 1 : colonne J = referent
            if len(row) > 9 and row[9].strip().lower() == 'referent' and len(row) > 3 and '@' in row[3]:
                ref_emails.add(row[3].strip().lower())
            # Méthode 2 : email en colonne G
            if len(row) > 6 and row[6].strip() and '@' in row[6]:
                ref_emails.add(row[6].strip().lower())
        # Construire la liste avec équipes
        referents = []
        for row in rows[1:]:
            if len(row) > 3 and row[3].strip().lower() in ref_emails:
                email = row[3].strip()
                equipe = [r[3] for r in rows[1:] if len(r) > 6 and r[6].strip().lower() == email.lower() and r[3] != email]
                referents.append({'email': email, 'nom': row[0], 'prenom': row[1], 'vendeurs': equipe})
        return jsonify({'success': True, 'referents': referents})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/referents')
@login_required
def get_referents():
    try:
        gc = get_sheets_client()
        if not gc:
            return jsonify({'success': False, 'error': 'Google Sheets non configuré'})
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()

        referents = []
        referent_emails_from_col_g = set()

        for row in rows[1:]:  # skip header
            if len(row) < 4 or not row[3].strip():
                continue
            email = row[3].strip()
            role = row[9].strip().lower() if len(row) > 9 else ''
            statut = row[10].strip().lower() if len(row) > 10 else 'actif'

            # Collecter les emails référents depuis colonne G
            if len(row) > 6 and row[6].strip() and '@' in row[6]:
                referent_emails_from_col_g.add(row[6].strip().lower())

            # Méthode 1 : colonne J = "referent"
            if role == 'referent' and statut != 'supprime':
                referents.append({
                    'email': email,
                    'nom': row[0].strip(),
                    'prenom': row[1].strip()
                })

        # Méthode 2 fallback : emails trouvés en colonne G mais pas encore dans la liste
        existing_emails = {r['email'].lower() for r in referents}
        for row in rows[1:]:
            if len(row) > 3:
                email = row[3].strip()
                if email.lower() in referent_emails_from_col_g and email.lower() not in existing_emails:
                    referents.append({
                        'email': email,
                        'nom': row[0].strip(),
                        'prenom': row[1].strip()
                    })
                    existing_emails.add(email.lower())

        return jsonify({'success': True, 'referents': referents})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users', methods=['GET'])
@login_required
def list_users():
    try:
        token = get_zoho_token()
        r = requests.get(
            f'https://mail.zoho.eu/api/organization/{ZOHO_ORG_ID}/accounts',
            headers={'Authorization': f'Zoho-oauthtoken {token}'}
        )
        data = r.json()
        users = data.get('data', [])
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    try:
        d = request.get_json()
        prenom = d.get('prenom', '').strip()
        nom = d.get('nom', '').strip()
        poste = d.get('poste', '').strip()
        telephone = d.get('telephone', '').strip()
        password_input = d.get('password', '').strip()
        email_perso = d.get('email_perso', '').strip()
        drive_folder_id = d.get('drive_folder_id', '').strip()
        referent_email = d.get('referent_email', '').strip()
        role = d.get('role', 'vendeur').strip().lower()
        # Générer automatiquement si vide
        password = password_input if password_input else generate_password()

        email_local = f"{prenom.lower()}.{nom.lower()}@liliwatt.fr"
        email_local = email_local.replace('é','e').replace('è','e').replace('ê','e').replace('ë','e')
        email_local = email_local.replace('à','a').replace('â','a').replace('ù','u').replace('û','u')
        email_local = email_local.replace(' ','.').replace("'",'')

        token = get_zoho_token()

        # Créer l'utilisateur
        r = requests.post(
            f'https://mail.zoho.eu/api/organization/{ZOHO_ORG_ID}/accounts',
            headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
            json={
                'firstName': prenom,
                'lastName': nom,
                'primaryEmailAddress': email_local,
                'password': password
            }
        )
        result = r.json()
        print(f"Création utilisateur: {result}")

        if result.get('status', {}).get('code') in [200, 201, '200', '201'] or 'data' in result:
            account_id = result.get('data', {}).get('accountId', '')

            # Appliquer la signature
            if account_id:
                sig_html = make_signature(prenom, nom, poste, telephone, email_local)
                sig_r = requests.post(
                    f'https://mail.zoho.eu/api/accounts/{account_id}/signatures',
                    headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
                    json={'signatureName': 'LILIWATT', 'signature': sig_html, 'isDefault': True},
                    timeout=15
                )
                sig_result = sig_r.json()
                print(f"📝 Signature API response: {sig_result}")
                # Récupérer l'ID de la signature pour la définir par défaut
                sig_id = sig_result.get('data', {}).get('signatureId', '')
                if sig_id:
                    requests.put(
                        f'https://mail.zoho.eu/api/accounts/{account_id}/signatures/{sig_id}',
                        headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
                        json={'signatureName': 'LILIWATT', 'signature': sig_html, 'isDefault': True},
                        timeout=15
                    )
                    print(f"✅ Signature appliquée pour {email_local}")

            # Configurer redirection vers contact@liliwatt.fr
            try:
                token_fwd = get_zoho_token()
                account_id = result.get('data', {}).get('accountId', '')
                if account_id:
                    requests.post(
                        f'https://mail.zoho.eu/api/organization/{ZOHO_ORG_ID}/accounts/{account_id}/settings/forwardingaddress',
                        headers={
                            'Authorization': f'Zoho-oauthtoken {token_fwd}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'forwardingAddress': 'contact@liliwatt.fr',
                            'keepCopy': True
                        },
                        timeout=15
                    )
                    print(f"✅ Redirection configurée : {email_local} → contact@liliwatt.fr")
            except Exception as e:
                print(f"⚠️ Erreur redirection : {e}")

            # Générer un token RGPD unique
            token_rgpd = uuid.uuid4().hex[:12]

            # Enregistrer dans Google Sheets
            save_to_sheet(prenom, nom, email_local, password, poste, drive_folder_id, referent_email, token_rgpd, role)

            # Créer l'utilisateur dans courtier-energie
            try:
                import jwt as pyjwt
                courtier_url = os.environ.get('COURTIER_API_URL', 'https://liliwatt-courtier.onrender.com')
                courtier_secret = os.environ.get('COURTIER_JWT_SECRET', 'liliwatt-jwt-secret-2026')
                admin_token = pyjwt.encode(
                    {'id': 'admin_liliwatt', 'email': 'johan.mallet@liliwatt.fr', 'role': 'admin', 'exp': datetime.utcnow() + timedelta(hours=2)},
                    courtier_secret, algorithm='HS256'
                )
                courtier_r = requests.post(
                    f'{courtier_url}/api/auth/create-user',
                    headers={'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'},
                    json={
                        'email': email_local,
                        'password': password,
                        'role': 'vendeur',
                        'drive_folder_id': drive_folder_id
                    },
                    timeout=10
                )
                print(f"✅ Utilisateur créé dans courtier-energie: {courtier_r.json()}")
            except Exception as e:
                print(f"⚠️ Erreur création courtier-energie: {e}")

            # Créer l'utilisateur dans le CRM LILIWATT (Neon/Vercel)
            try:
                CRM_URL = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
                CRM_API_KEY = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
                lien_rgpd = f'https://liliwatt-courtier.onrender.com/rgpd/{token_rgpd}'
                # Numéro courtier auto
                courtier_number = get_next_courtier_number()
                crm_r = requests.post(
                    f'{CRM_URL}/api/crm/create-user',
                    headers={'X-API-Key': CRM_API_KEY, 'Content-Type': 'application/json'},
                    json={
                        'email': email_local,
                        'firstName': prenom,
                        'lastName': nom,
                        'role': role.upper(),
                        'password': password,
                        'referentEmail': referent_email,
                        'token_rgpd': token_rgpd,
                        'lien_rgpd': lien_rgpd,
                        'zoho_password': password,
                        'courtierNumber': courtier_number
                    },
                    timeout=10
                )
                print(f"✅ CRM LILIWATT: {crm_r.status_code} — {crm_r.json()}")
            except Exception as e:
                print(f"⚠️ Erreur CRM LILIWATT: {e}")

            # Envoyer email de bienvenue
            created_account_id = result.get('data', {}).get('accountId', '')
            send_welcome_email(prenom, nom, email_local, password, poste, telephone, email_perso, created_account_id, token_rgpd, referent_email)

            # Notifier bo@liliwatt.fr avec la signature HTML prête à copier
            try:
                sig_html = make_signature(prenom, nom, poste, telephone, email_local)
                rgpd_link = f'https://liliwatt-courtier.onrender.com/rgpd/{token_rgpd}'
                bo_body = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#1e1b4b,#7c3aed);padding:24px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="color:white;font-size:24px;font-weight:800;letter-spacing:3px;margin:0;">LILIWATT</h1>
    <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;font-size:12px;">Nouveau commercial cr&eacute;&eacute;</p>
  </div>
  <div style="background:#f5f3ff;padding:28px;border-radius:0 0 12px 12px;">
    <p style="font-size:15px;color:#1e1b4b;margin-bottom:20px;"><strong>{prenom} {nom}</strong> a &eacute;t&eacute; ajout&eacute; &agrave; l'&eacute;quipe.</p>

    <div style="background:#fef3c7;border:2px solid #fbbf24;border-radius:10px;padding:20px;margin-bottom:20px;">
      <p style="margin:0 0 12px;font-weight:700;color:#92400e;font-size:14px;">&#128272; Identifiants Zoho Mail</p>
      <table style="width:100%;font-size:14px;border-collapse:collapse;">
        <tr><td style="padding:6px 0;color:#92400e;font-weight:700;width:130px;">Email</td><td style="color:#1e1b4b;font-weight:700;">{email_local}</td></tr>
        <tr><td style="padding:6px 0;color:#92400e;font-weight:700;">Mot de passe</td><td style="color:#1e1b4b;font-weight:700;font-size:16px;">{password}</td></tr>
        <tr><td style="padding:6px 0;color:#92400e;font-weight:700;">Connexion</td><td><a href="https://mail.zoho.eu" style="color:#7c3aed;font-weight:700;text-decoration:none;">mail.zoho.eu</a></td></tr>
      </table>
    </div>

    <div style="background:white;border-radius:10px;padding:20px;margin-bottom:20px;border-left:4px solid #7c3aed;">
      <table style="width:100%;font-size:13px;border-collapse:collapse;">
        <tr><td style="padding:6px 0;color:#6b7280;font-weight:700;width:130px;">Poste</td><td style="color:#1e1b4b;">{poste}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">T&eacute;l&eacute;phone</td><td style="color:#1e1b4b;">{telephone}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">R&eacute;f&eacute;rent</td><td style="color:#1e1b4b;">{referent_email or '&mdash;'}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">Lien RGPD</td><td><a href="{rgpd_link}" style="color:#7c3aed;word-break:break-all;">{rgpd_link}</a></td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">Drive</td><td><a href="https://drive.google.com/drive/folders/{drive_folder_id}" style="color:#7c3aed;">Ouvrir le dossier</a></td></tr>
      </table>
    </div>

    <div style="background:#ede9fe;border-radius:10px;padding:16px;margin-bottom:16px;">
      <p style="margin:0 0 10px;font-weight:700;color:#1e1b4b;font-size:13px;">&#9999;&#65039; Signature email pr&ecirc;te &agrave; copier dans Zoho :</p>
      <div style="background:white;border-radius:8px;padding:16px;border:1px solid #e9d5ff;">{sig_html}</div>
    </div>
  </div>
</div>"""
                bo_token = get_zoho_token()
                if bo_token:
                    account_id = os.environ.get('ZOHO_ACCOUNT_ID', '8439060000000002002')
                    requests.post(
                        f'https://mail.zoho.eu/api/accounts/{account_id}/messages',
                        headers={'Authorization': f'Zoho-oauthtoken {bo_token}', 'Content-Type': 'application/json'},
                        json={
                            'fromAddress': 'bo@liliwatt.fr',
                            'toAddress': 'bo@liliwatt.fr',
                            'subject': f'Nouveau commercial : {prenom} {nom} — {poste}',
                            'content': bo_body,
                            'mailFormat': 'html'
                        },
                        timeout=15
                    )
                    print(f"✅ Notification bo@liliwatt.fr envoyée pour {prenom} {nom}")
            except Exception as e:
                print(f"⚠️ Erreur notification bo@: {e}")

            return jsonify({
                'success': True,
                'email': email_local,
                'password': password,
                'message': f'Utilisateur {prenom} {nom} créé avec succès'
            })
        else:
            return jsonify({'success': False, 'error': str(result)})

    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})

@app.route('/api/users/drive-folder', methods=['GET'])
@login_required
def get_drive_folder():
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'error': 'Email manquant'})
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.sheet1
        rows = ws.get_all_values()
        for row in rows:
            if len(row) >= 4 and row[3].lower() == email.lower():
                drive_folder_id = row[5] if len(row) > 5 else ''
                return jsonify({'success': True, 'drive_folder_id': drive_folder_id})
        return jsonify({'success': False, 'error': 'Vendeur non trouvé'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

RECRUTEMENT_SHEET_ID = '11A-aJIqtm0JZ01lU43GpWudWDNFtknIr-4sYgYD-6ck'

@app.route('/api/recrutement/candidats')
@login_required
def list_candidats():
    try:
        gc = get_sheets_client()
        if not gc:
            return jsonify({'success': False, 'error': 'Sheets non configuré'})
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).sheet1
        rows = ws.get_all_values()
        candidats = []
        for i, row in enumerate(rows):
            if i == 0 or not row[2] or '@' not in row[2]:
                continue
            candidats.append({
                'row': i + 1,
                'nom': row[0] if len(row) > 0 else '',
                'prenom': row[1] if len(row) > 1 else '',
                'email': row[2] if len(row) > 2 else '',
                'telephone': row[3] if len(row) > 3 else '',
                'siren': row[4] if len(row) > 4 else '',
                'qualite': row[5] if len(row) > 5 else '',
                'date': row[6] if len(row) > 6 else '',
                'drive_link': row[7] if len(row) > 7 else '',
                'statut': row[8] if len(row) > 8 else 'EN COURS',
                'referant': row[10] if len(row) > 10 else ''
            })
        return jsonify({'success': True, 'candidats': candidats})
    except Exception as e:
        import traceback
        print(f"⚠️ Erreur candidats: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/statut', methods=['POST'])
@login_required
def update_statut_candidat():
    try:
        d = request.get_json()
        row_num = d.get('row')
        statut = d.get('statut', '')
        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).sheet1
        ws.update_cell(row_num, 9, statut)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/referant', methods=['POST'])
@login_required
def update_referant_candidat():
    try:
        d = request.get_json()
        row_num = d.get('row')
        referant = d.get('referant', '')
        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).sheet1
        ws.update_cell(row_num, 11, referant)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/envoyer-contrat', methods=['POST'])
@login_required
def envoyer_contrat():
    try:
        from generate_contrats import generate_contrats
        d = request.get_json()
        email = d.get('email', '').strip()
        if not email:
            return jsonify({'success': False, 'error': 'Email requis'})

        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).sheet1
        rows = ws.get_all_values()
        candidat = None
        for row in rows:
            if len(row) > 2 and row[2].lower() == email.lower():
                candidat = {'nom': row[0], 'prenom': row[1], 'email': row[2],
                           'siren': row[4] if len(row) > 4 else '',
                           'qualite': row[5] if len(row) > 5 else '',
                           'drive_link': row[7] if len(row) > 7 else ''}
                break
        if not candidat:
            return jsonify({'success': False, 'error': 'Candidat non trouvé'})

        # Extraire le folder ID du lien Drive
        import re
        match = re.search(r'folders/([a-zA-Z0-9_-]+)', candidat['drive_link'])
        if not match:
            return jsonify({'success': False, 'error': 'Dossier Drive non trouvé'})
        folder_id = match.group(1)

        print(f"📄 Génération contrats pour {candidat['prenom']} {candidat['nom']}")
        files = generate_contrats(
            candidat['prenom'], candidat['nom'],
            candidat['siren'], candidat['qualite'], folder_id
        )
        print(f"✅ {len(files)} contrat(s) générés")
        return jsonify({'success': True, 'files': files, 'drive_link': candidat['drive_link']})
    except Exception as e:
        import traceback
        print(f"⚠️ Erreur contrat: {e}")
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})

# ===== PHASE 1 — Import CV + Profils =====

@app.route('/api/recrutement/candidats-phase1')
@login_required
def list_candidats_phase1():
    try:
        gc = get_sheets_client()
        if not gc:
            return jsonify({'success': False, 'error': 'Sheets non configuré'})
        sh = gc.open_by_key(RECRUTEMENT_SHEET_ID)
        try:
            ws = sh.worksheet('PHASE 1')
        except Exception:
            ws = sh.add_worksheet(title='PHASE 1', rows=500, cols=10)
            ws.update('A1:J1', [['NOM', 'PRENOM', 'EMAIL', 'TEL', 'ADRESSE', 'STATUT', 'NOTE', 'DATE', 'SESSION', 'LIEN_CV']])
        rows = ws.get_all_values()
        candidats = []
        for i, row in enumerate(rows):
            if i == 0:
                # Log les headers pour debug
                print(f"📋 PHASE 1 headers ({len(row)} cols): {row}")
                continue
            if len(row) < 3 or not row[2]:
                continue
            lien_cv = row[9] if len(row) > 9 else ''
            if not lien_cv and len(row) > 8:
                # Chercher un lien Drive dans toutes les colonnes restantes
                for col_idx in range(8, len(row)):
                    if row[col_idx] and ('drive.google.com' in row[col_idx] or row[col_idx].startswith('http')):
                        lien_cv = row[col_idx]
                        break
            candidats.append({
                'row': i + 1,
                'nom': row[0], 'prenom': row[1], 'email': row[2],
                'telephone': row[3] if len(row) > 3 else '',
                'adresse': row[4] if len(row) > 4 else '',
                'statut': row[5] if len(row) > 5 else 'NON CONTACTÉ',
                'note': row[6] if len(row) > 6 else '',
                'date': row[7] if len(row) > 7 else '',
                'session': row[8] if len(row) > 8 else '',
                'lien_cv': lien_cv
            })
            if lien_cv:
                print(f"  📄 CV trouvé pour {row[1]} {row[0]}: {lien_cv[:60]}...")
        return jsonify({'success': True, 'candidats': candidats})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/referents-liste')
@login_required
def referents_liste():
    try:
        gc = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        refs = []
        for row in rows:
            if len(row) > 9 and row[9] in ('referent', 'admin') and '@' in (row[3] or ''):
                refs.append({'nom': row[0], 'prenom': row[1], 'email': row[3]})
        return jsonify({'success': True, 'referents': refs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/phase1/envoyer-referent', methods=['POST'])
@login_required
def envoyer_referent_phase1():
    try:
        d = request.get_json()
        ref_email = d.get('referent_email', '')
        candidat = d.get('candidat', {})
        token = get_zoho_token()
        if not token:
            return jsonify({'success': False, 'error': 'Zoho token non obtenu'})
        mail_html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:linear-gradient(135deg,#1e1b4b,#7c3aed);padding:24px;border-radius:12px 12px 0 0;text-align:center;">
<h1 style="color:#fff;font-size:24px;letter-spacing:3px;margin:0;">LILIWATT</h1>
<p style="color:rgba(255,255,255,.8);font-size:12px;margin:4px 0 0;">Profil candidat à évaluer</p>
</div>
<div style="background:#f5f3ff;padding:28px;border-radius:0 0 12px 12px;">
<p style="font-size:15px;color:#1e1b4b;">Bonjour,</p>
<p style="color:#374151;line-height:1.7;">Un nouveau profil candidat vous est transmis pour évaluation :</p>
<div style="background:#fff;border-radius:10px;padding:20px;margin:16px 0;border-left:4px solid #7c3aed;">
<table style="width:100%;font-size:13px;border-collapse:collapse;">
<tr><td style="padding:6px 0;color:#6b7280;font-weight:700;width:100px;">Nom</td><td style="color:#1e1b4b;">{candidat.get('prenom','')} {candidat.get('nom','')}</td></tr>
<tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">Email</td><td style="color:#1e1b4b;">{candidat.get('email','')}</td></tr>
<tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">Tél</td><td style="color:#1e1b4b;">{candidat.get('telephone','')}</td></tr>
<tr><td style="padding:6px 0;color:#6b7280;font-weight:700;">Adresse</td><td style="color:#1e1b4b;">{candidat.get('adresse','')}</td></tr>
</table>
</div>
{('<p style="margin:12px 0;"><a href="' + candidat.get('lien_cv','') + '" style="color:#7c3aed;font-weight:600;">📄 Voir le CV</a></p>') if candidat.get('lien_cv') else ''}
<p style="color:#374151;">Lien session Meet : <a href="https://meet.google.com/tzv-pgjc-und?authuser=0" style="color:#7c3aed;font-weight:600;">Rejoindre</a></p>
<hr style="border:1px solid #e9d5ff;margin:20px 0;">
<p style="font-size:11px;color:#9ca3af;">LILIWATT — LILISTRAT STRATÉGIE SAS — 59 rue de Ponthieu, Bureau 326 — 75008 Paris</p>
</div></div>"""
        account_id = os.environ.get('ZOHO_ACCOUNT_ID', '8439060000000002002')
        requests.post(
            f'https://mail.zoho.eu/api/accounts/{account_id}/messages',
            headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
            json={'fromAddress': 'recrutement@liliwatt.fr', 'toAddress': ref_email,
                  'subject': f"📋 Profil candidat — {candidat.get('prenom','')} {candidat.get('nom','')}",
                  'content': mail_html, 'mailFormat': 'html'},
            timeout=15
        )
        print(f"✅ Profil envoyé à {ref_email}: {candidat.get('prenom','')} {candidat.get('nom','')}")
        return jsonify({'success': True})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

def extract_text_from_file(file_bytes, filename):
    """Extrait le texte d'un PDF ou Word."""
    import io
    text = ''
    fname = filename.lower()
    if fname.endswith('.pdf'):
        import pdfplumber
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + '\n'
        pdf.close()
    elif fname.endswith('.docx') or fname.endswith('.doc'):
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        text = '\n'.join(p.text for p in doc.paragraphs)
    return text.strip()

def extract_cv_with_gpt(text):
    """Appelle GPT-4o-mini pour extraire les infos du CV."""
    import openai
    client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY', ''))
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': 'Extrais ces informations du CV en JSON : nom, prenom, email, telephone, adresse. Réponds UNIQUEMENT en JSON valide.'},
            {'role': 'user', 'content': text[:4000]}
        ],
        temperature=0
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
    return json.loads(raw)

def save_cv_to_sheet(data, lien_cv=''):
    """Sauvegarde les données extraites dans PHASE 1."""
    gc = get_sheets_client()
    sh = gc.open_by_key(RECRUTEMENT_SHEET_ID)
    try:
        ws = sh.worksheet('PHASE 1')
    except Exception:
        ws = sh.add_worksheet(title='PHASE 1', rows=500, cols=10)
        ws.update('A1:J1', [['NOM', 'PRENOM', 'EMAIL', 'TEL', 'ADRESSE', 'STATUT', 'NOTE', 'DATE', 'SESSION', 'LIEN_CV']])
    import time
    date_str = datetime.now().strftime('%d/%m/%Y')
    tel = data.get('telephone', '') or ''
    if isinstance(tel, list):
        tel = ' / '.join(str(t) for t in tel)
    email = data.get('email', '') or ''
    if isinstance(email, list):
        email = email[0] if email else ''
    row_data = [
        (data.get('nom', '') or '').upper(),
        data.get('prenom', '') or '',
        email,
        tel,
        data.get('adresse', '') or '',
        'NON CONTACTÉ', '', date_str, '', lien_cv
    ]
    for attempt in range(3):
        try:
            ws.append_row(row_data)
            break
        except Exception as e:
            if attempt < 2:
                print(f"⚠️ Sheets retry {attempt+1}/3: {e}")
                time.sleep(2)
            else:
                raise e

RECRUTEMENT_DRIVE_PARENT = '1eQYZqexJ67EcVPe8rsmKDf6mtASf9yjA'

def upload_cv_to_drive(file_bytes, original_filename, prenom, nom):
    """Upload le CV original dans Drive et retourne le lien."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        from google.oauth2.service_account import Credentials as SACredentials
        import base64, io

        creds_b64 = os.environ.get('GOOGLE_DRIVE_CREDS_BASE64', '')
        creds_json_env = os.environ.get('GOOGLE_CREDS_JSON', '')
        if creds_b64:
            creds_dict = json.loads(base64.b64decode(creds_b64).decode())
        elif creds_json_env:
            creds_dict = json.loads(creds_json_env)
        else:
            with open(os.path.join(os.path.dirname(__file__), 'liliwatt-eddcc0bc9e18.json')) as fl:
                creds_dict = json.load(fl)
        creds = SACredentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
        drive = build('drive', 'v3', credentials=creds)

        # Trouver/créer CANDIDATURES EN COURS
        q = f"'{RECRUTEMENT_DRIVE_PARENT}' in parents and name='CANDIDATURES EN COURS' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        res = drive.files().list(q=q, fields='files(id)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        if res['files']:
            attente_id = res['files'][0]['id']
        else:
            f2 = drive.files().create(body={'name': 'CANDIDATURES EN COURS', 'mimeType': 'application/vnd.google-apps.folder', 'parents': [RECRUTEMENT_DRIVE_PARENT]}, fields='id', supportsAllDrives=True).execute()
            attente_id = f2['id']

        # Trouver/créer dossier candidat
        folder_name = f"{prenom} {nom.upper()}"
        q2 = f"'{attente_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        res2 = drive.files().list(q=q2, fields='files(id)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        if res2['files']:
            cand_id = res2['files'][0]['id']
        else:
            f3 = drive.files().create(body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [attente_id]}, fields='id', supportsAllDrives=True).execute()
            cand_id = f3['id']

        # Upload le fichier
        mime = 'application/pdf' if original_filename.lower().endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime)
        uploaded = drive.files().create(
            body={'name': original_filename, 'parents': [cand_id], 'mimeType': mime},
            media_body=media, fields='id, webViewLink', supportsAllDrives=True
        ).execute()
        print(f"📁 CV uploadé Drive: {original_filename} → {uploaded.get('webViewLink','')}")
        return uploaded.get('webViewLink', '')
    except Exception as e:
        print(f"⚠️ Erreur upload CV Drive: {e}")
        return ''

@app.route('/api/recrutement/upload-cv', methods=['POST'])
@login_required
def upload_cv():
    try:
        if 'cv' not in request.files:
            return jsonify({'success': False, 'error': 'Fichier CV requis'})
        f = request.files['cv']
        filename = f.filename
        file_bytes = f.read()

        # ZIP : extraire et traiter chaque fichier
        if filename.endswith('.zip'):
            import zipfile, io
            results = {'total': 0, 'ok': 0, 'errors': 0}
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                all_names = zf.namelist()
                print(f"📦 ZIP ouvert: {len(all_names)} entrées")
                for name in all_names:
                    # Ignorer fichiers cachés macOS et dossiers
                    basename = name.split('/')[-1]
                    if basename.startswith('.') or basename.startswith('__') or not basename:
                        continue
                    if not basename.lower().endswith(('.pdf', '.docx', '.doc')):
                        print(f"  ⏭️ Ignoré (format): {name}")
                        continue
                    print(f"  📄 Trouvé: {name} ({zf.getinfo(name).file_size} octets)")
                    results['total'] += 1
                    try:
                        inner = zf.read(name)
                        text = extract_text_from_file(inner, basename)
                        if not text:
                            print(f"  ⚠️ Pas de texte extrait: {name}")
                            results['errors'] += 1; continue
                        data = extract_cv_with_gpt(text)
                        lien = upload_cv_to_drive(inner, basename, data.get('prenom', ''), data.get('nom', ''))
                        save_cv_to_sheet(data, lien)
                        results['ok'] += 1
                        print(f"  ✅ {name}: {data.get('nom','')} {data.get('prenom','')} ({data.get('email','')})")
                    except Exception as e:
                        results['errors'] += 1
                        print(f"  ❌ {name}: {e}")
            print(f"📦 ZIP terminé: {results['total']} traités, {results['ok']} ok, {results['errors']} erreurs")
            return jsonify({'success': True, 'zip': True, **results})

        # Fichier unique
        text = extract_text_from_file(file_bytes, filename)
        if not text:
            return jsonify({'success': False, 'error': 'Impossible d\'extraire le texte du CV'})

        data = extract_cv_with_gpt(text)
        print(f"📄 CV extrait: {data}")
        lien_cv = upload_cv_to_drive(file_bytes, filename, data.get('prenom', ''), data.get('nom', ''))
        save_cv_to_sheet(data, lien_cv)
        return jsonify({'success': True, 'data': data, 'lien_cv': lien_cv})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/phase1/statut', methods=['POST'])
@login_required
def update_phase1_statut():
    try:
        d = request.get_json()
        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).worksheet('PHASE 1')
        ws.update_cell(d['row'], 6, d['statut'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/phase1/note', methods=['POST'])
@login_required
def update_phase1_note():
    try:
        d = request.get_json()
        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).worksheet('PHASE 1')
        ws.update_cell(d['row'], 7, d['note'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/phase1/inviter', methods=['POST'])
@login_required
def inviter_phase1():
    try:
        d = request.get_json()
        email = d.get('email', '')
        prenom = d.get('prenom', '')
        date_session = d.get('date_session', '')
        heure_session = d.get('heure_session', '')
        row_num = d.get('row')

        # Envoyer le mail d'invitation
        mail_html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:linear-gradient(135deg,#1e1b4b,#7c3aed);padding:32px;border-radius:12px 12px 0 0;text-align:center;">
<h1 style="color:#fff;font-size:28px;font-weight:800;letter-spacing:3px;margin:0;">LILIWATT</h1>
<p style="color:rgba(255,255,255,.8);font-size:12px;margin:6px 0 0;">Invitation session de présentation</p>
</div>
<div style="background:#f5f3ff;padding:32px;border-radius:0 0 12px 12px;">
<p style="font-size:16px;color:#1e1b4b;">Bonjour <strong>{prenom}</strong>,</p>
<p style="color:#374151;line-height:1.7;">Suite à notre échange, nous avons le plaisir de vous inviter à rejoindre notre session de présentation LILIWATT.</p>
<div style="background:#fff;border-radius:10px;padding:24px;margin:24px 0;border-left:4px solid #7c3aed;">
<table style="width:100%;font-size:14px;border-collapse:collapse;">
<tr><td style="padding:8px 0;color:#6b7280;font-weight:700;width:100px;">Date</td><td style="color:#1e1b4b;font-weight:700;">{date_session}</td></tr>
<tr><td style="padding:8px 0;color:#6b7280;font-weight:700;">Heure</td><td style="color:#1e1b4b;font-weight:700;">{heure_session}</td></tr>
</table>
</div>
<a href="https://meet.google.com/tzv-pgjc-und?authuser=0" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#d946ef);color:#fff;padding:14px 32px;border-radius:50px;text-decoration:none;font-weight:700;font-size:14px;">Rejoindre la session Google Meet</a>
<p style="color:#374151;margin-top:20px;line-height:1.7;">À très bientôt !</p>
<p style="color:#6b7280;font-size:13px;">L'équipe LILIWATT<br>recrutement@liliwatt.fr</p>
<hr style="border:1px solid #e9d5ff;margin:24px 0;">
<p style="font-size:11px;color:#9ca3af;">LILIWATT — LILISTRAT STRATÉGIE SAS — 59 rue de Ponthieu, Bureau 326 — 75008 Paris</p>
</div></div>"""

        token = get_zoho_token()
        if token:
            account_id = os.environ.get('ZOHO_ACCOUNT_ID', '8439060000000002002')
            requests.post(
                f'https://mail.zoho.eu/api/accounts/{account_id}/messages',
                headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
                json={'fromAddress': 'recrutement@liliwatt.fr', 'toAddress': email,
                      'subject': f'Invitation session LILIWATT — {date_session} à {heure_session}',
                      'content': mail_html, 'mailFormat': 'html'},
                timeout=15
            )
            print(f"✅ Invitation envoyée à {email}")

        # Mettre à jour Sheets
        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).worksheet('PHASE 1')
        ws.update_cell(row_num, 6, 'CONTACTÉ')
        ws.update_cell(row_num, 9, f'{date_session} {heure_session}')

        return jsonify({'success': True})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recrutement/profil/<int:row_id>', methods=['DELETE'])
@login_required
def delete_phase1_profil(row_id):
    try:
        d = request.get_json() or {}
        drive_file_id = d.get('drive_file_id', '')

        # 1. Supprimer la ligne dans le Sheet PHASE 1
        gc = get_sheets_client()
        ws = gc.open_by_key(RECRUTEMENT_SHEET_ID).worksheet('PHASE 1')
        ws.delete_rows(row_id)
        print(f"✅ Ligne {row_id} supprimée du Sheet PHASE 1")

        # 2. Supprimer le fichier CV dans le Drive si fourni
        if drive_file_id:
            try:
                from googleapiclient.discovery import build
                from google.oauth2.service_account import Credentials as SACredentials
                import base64

                creds_b64 = os.environ.get('GOOGLE_DRIVE_CREDS_BASE64', '')
                creds_json_env = os.environ.get('GOOGLE_CREDS_JSON', '')
                if creds_b64:
                    creds_dict = json.loads(base64.b64decode(creds_b64).decode())
                elif creds_json_env:
                    creds_dict = json.loads(creds_json_env)
                else:
                    creds_dict = None

                if creds_dict:
                    creds = SACredentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                    drive_service = build('drive', 'v3', credentials=creds)
                    drive_service.files().delete(fileId=drive_file_id).execute()
                    print(f"✅ Fichier Drive {drive_file_id} supprimé")
            except Exception as e:
                print(f"⚠️ Erreur suppression Drive: {e}")

        return jsonify({'success': True})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ===== SUIVI DES VENTES =====
SUIVI_VENTES_SHEET_ID = os.environ.get('SUIVI_VENTES_SHEET_ID', '1Ld1Zl3qVzdVZsyksdfxYfL1LiVcFd5BEbrPV6NYLfcA')

def get_suivi_sheet_id():
    return SUIVI_VENTES_SHEET_ID

SUIVI_HEADERS = ['REF','REF_CLIENT','SOCIETE','VENDEUR','REFERENT','PERIODE','DEBUT',
    'FIN','TYPE','PDL_PCE','FOURNISSEUR','MONTANT','COMM_VENDEUR',
    'COMM_REFERENT','MARGE','STATUT_PAIEMENT','DATE_P1','DATE_P2','SEGMENT',
    'NOM_CLIENT','PRENOM_CLIENT','TEL_CLIENT','EMAIL_CLIENT',
    'VOLUME_ELEC_MWH','VOLUME_GAZ_MWH','LIEN_DRIVE']

@app.route('/api/suivi-ventes/init-sheet')
@login_required
def init_suivi_sheet():
    try:
        gc = get_sheets_client()
        sh = gc.open_by_key(SUIVI_VENTES_SHEET_ID)
        ws = sh.sheet1
        ws.update('A1:Z1', [SUIVI_HEADERS])
        ws.format('A1:Z1', {
            'backgroundColor': {'red': 0.118, 'green': 0.106, 'blue': 0.294},
            'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True, 'fontSize': 10}
        })
        ws.freeze(rows=1)
        sheet_url = f"https://docs.google.com/spreadsheets/d/{SUIVI_VENTES_SHEET_ID}"
        print(f"✅ Sheet Suivi Ventes initialisé: {SUIVI_VENTES_SHEET_ID}")
        return jsonify({'success': True, 'sheet_id': SUIVI_VENTES_SHEET_ID, 'sheet_url': sheet_url})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/suivi-ventes/ajouter', methods=['POST'])
@login_required
def ajouter_vente():
    try:
        d = request.get_json()
        sheet_id = get_suivi_sheet_id()
        if not sheet_id:
            return jsonify({'success': False, 'error': 'Sheet non initialisé'})

        gc = get_sheets_client()
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1

        # Générer réf auto
        now = datetime.now()
        rows = ws.get_all_values()
        count = len(rows)
        ref = f"LW-{now.strftime('%Y%m')}-{count:03d}"

        montant = parse_float(d.get('montant_ht'))
        comm_v = parse_float(d.get('commission_vendeur'))
        comm_r = parse_float(d.get('commission_referent'))
        vol_elec = parse_float(d.get('volume_elec'))
        vol_gaz = parse_float(d.get('volume_gaz'))
        marge = montant - comm_v - comm_r

        # Normaliser le type
        type_val = (d.get('type_energie', '') or '').strip()
        if 'gaz' in type_val.lower():
            type_val = 'Gaz'
        elif 'lec' in type_val.lower():
            type_val = 'Électricité'
        print(f"📝 Vente type: {type_val} (reçu: {d.get('type_energie','')})")

        row_data = [
            ref, d.get('ref_client', ''), d.get('societe', ''), d.get('vendeur', ''), d.get('referent', ''),
            d.get('periode_prod', ''), d.get('date_debut_contrat', ''), d.get('date_fin_contrat', ''),
            type_val, d.get('pdl_pce', ''), d.get('fournisseur', ''),
            montant, comm_v, comm_r, marge,
            d.get('statut_paiement', ''), d.get('date_paiement_1', ''), d.get('date_paiement_2', ''),
            d.get('segment', ''), d.get('nom_client', ''), d.get('prenom_client', ''),
            d.get('tel_client', ''), d.get('email_client', ''),
            vol_elec, vol_gaz, d.get('lien_drive', '')
        ]

        import time
        for attempt in range(3):
            try:
                ws.append_row(row_data, value_input_option='RAW')
                break
            except Exception:
                if attempt < 2: time.sleep(2)
                else: raise

        print(f"✅ Vente ajoutée: {ref} — {d.get('nom_client','')} — {montant}€")
        return jsonify({'success': True, 'ref': ref})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/suivi-ventes/liste')
@login_required
def liste_ventes():
    try:
        sheet_id = get_suivi_sheet_id()
        if not sheet_id:
            return jsonify({'success': False, 'error': 'Sheet non initialisé'})
        print(f"📊 SUIVI SHEET ID: {sheet_id}")
        gc = get_sheets_client()
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1
        print(f"📊 Feuille: {ws.title} | ID feuille: {ws.id}")
        rows = ws.get_all_values()
        print(f"📊 Nb lignes: {len(rows)}")
        if rows:
            print(f"📊 Ligne 1 (en-têtes): {rows[0][:10]}")
        if len(rows) > 1:
            print(f"📊 Ligne 2 (1ère donnée): {rows[1][:10]}")
        if len(rows) < 2:
            return jsonify({'success': True, 'ventes': [], 'totaux': {'comm_vendeur': 0, 'comm_referent': 0, 'marge': 0, 'nb': 0}})

        vendeur_filter = request.args.get('vendeur', '')
        fournisseur_filter = request.args.get('fournisseur', '')
        annee_filter = request.args.get('annee', '')
        mois_filter = request.args.get('mois', '')
        search = request.args.get('search', '').lower()

        def g(row, i): return row[i] if len(row) > i else ''

        ventes = []
        total_cv, total_cr, total_m = 0, 0, 0
        for row in rows[1:]:
            if len(row) < 14: continue
            if vendeur_filter and g(row,3) != vendeur_filter: continue
            if fournisseur_filter and g(row,10) != fournisseur_filter: continue
            periode = g(row,5)
            if annee_filter and not periode.startswith(annee_filter): continue
            if mois_filter and len(periode) >= 7 and periode[5:7] != mois_filter: continue
            if search:
                haystack = ' '.join([g(row,2),g(row,19),g(row,20),g(row,21),g(row,22)]).lower()
                if search not in haystack: continue
            cv = parse_float(g(row,12)); cr = parse_float(g(row,13)); m = parse_float(g(row,14))
            total_cv += cv; total_cr += cr; total_m += m
            ventes.append({
                'ref': g(row,0), 'ref_client': g(row,1), 'societe': g(row,2),
                'vendeur': g(row,3), 'referent': g(row,4),
                'periode_prod': g(row,5), 'date_debut': g(row,6), 'date_fin': g(row,7),
                'type': 'Gaz' if 'gaz' in g(row,18).lower() else g(row,8),
                'pdl_pce': g(row,9), 'fournisseur': g(row,10),
                'montant_ht': g(row,11), 'comm_vendeur': cv, 'comm_referent': cr, 'marge': m,
                'statut_paiement': g(row,15), 'date_p1': g(row,16), 'date_p2': g(row,17),
                'segment': g(row,18), 'nom_client': g(row,19), 'prenom_client': g(row,20),
                'tel_client': g(row,21), 'email_client': g(row,22),
                'volume_elec': g(row,23), 'volume_gaz': g(row,24), 'lien_drive': g(row,25)
            })
        return jsonify({'success': True, 'ventes': ventes, 'totaux': {'comm_vendeur': total_cv, 'comm_referent': total_cr, 'marge': total_m, 'nb': len(ventes)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/suivi-ventes/export-vendeur')
@login_required
def export_vendeur():
    try:
        sheet_id = get_suivi_sheet_id()
        email = request.args.get('vendeur', '')
        periode = request.args.get('periode', '')
        annee = request.args.get('annee', '')
        if not sheet_id:
            return jsonify({'success': False, 'error': 'Sheet non initialisé'})
        gc = get_sheets_client()
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()

        # Colonnes export : tout sauf col 14 (MARGE)
        export_cols = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23,24,25]
        header = [SUIVI_HEADERS[i] for i in export_cols if i < len(SUIVI_HEADERS)]
        csv_lines = [','.join(header)]
        for row in rows[1:]:
            if len(row) < 14: continue
            if email and row[3] != email: continue
            if periode and row[5] != periode: continue
            if annee and not row[5].startswith(annee): continue
            vals = [str(row[i]) if i < len(row) else '' for i in export_cols]
            csv_lines.append(','.join(f'"{v}"' for v in vals))

        from flask import Response
        label = email.split('@')[0] if email else 'tous'
        csv_content = '\n'.join(csv_lines)
        return Response(csv_content, mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=export_{label}_{annee or periode or "all"}.csv'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/<email>', methods=['DELETE'])
@login_required
def delete_user(email):
    try:
        token = get_zoho_token()
        r = requests.delete(
            f'https://mail.zoho.eu/api/organization/{ZOHO_ORG_ID}/accounts',
            headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
            json={'emailList': [email]}
        )
        return jsonify({'success': True, 'result': r.json()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== PROSPECTS MASTER — pagination serveur =====
import csv as csv_module
import math

MASTER_CSV = os.environ.get('MASTER_CSV_PATH', os.path.join(os.path.dirname(__file__), 'master_prospects_enrichi.csv'))

def iter_master_csv(filtres):
    """Générateur : lit le CSV ligne par ligne sans tout charger."""
    if not os.path.exists(MASTER_CSV):
        return
    with open(MASTER_CSV, encoding='utf-8', errors='ignore') as f:
        reader = csv_module.DictReader(f)
        for row in reader:
            # Filtres
            if filtres.get('segment'):
                seg = (row.get('typologie_contrat', '') or row.get('segments', '')).upper()
                if filtres['segment'].upper() not in seg:
                    continue
            if filtres.get('statut'):
                if (row.get('statut', '') or '') != filtres['statut']:
                    continue
            if filtres.get('annee_fin'):
                fin = row.get('date_fin_livraison', '') or ''
                if filtres['annee_fin'] not in fin:
                    continue
            if filtres.get('non_attribues'):
                if (row.get('vendeur_attribue', '') or '').strip():
                    continue
            if filtres.get('search'):
                hay = ' '.join([row.get('raison_sociale',''), row.get('siren',''), row.get('adresse',''), row.get('signataire',''), row.get('dirigeant','')]).lower()
                if filtres['search'].lower() not in hay:
                    continue
            yield row

@app.route('/api/prospects/master')
@login_required
def prospects_master():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        filtres = {
            'segment': request.args.get('segment', ''),
            'statut': request.args.get('statut', ''),
            'annee_fin': request.args.get('annee_fin', ''),
            'non_attribues': request.args.get('non_attribues', '') == 'true',
            'search': request.args.get('search', ''),
        }
        skip = (page - 1) * per_page
        results = []
        total = 0
        for row in iter_master_csv(filtres):
            total += 1
            if total > skip and len(results) < per_page:
                results.append(row)
        return jsonify({
            'success': True,
            'prospects': results,
            'total': total,
            'page': page,
            'pages': math.ceil(total / per_page) if total else 0
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ===== PROSPECTION ADMIN =====
PROSPECTION_SHEET_ID = '1JFEAXFZbdvf40yDWZGVnuEgUN15XdOAx6WgqL69-AMA'

# ===== BASE PREMIUM =====
@app.route('/api/base-premium/stats')
@login_required
def base_premium_stats():
    try:
        gc = get_sheets_client()
        sh = gc.open_by_key(PROSPECTION_SHEET_ID)
        try:
            ws = sh.worksheet('LEADS OHM')
        except Exception:
            return jsonify({'success': True, 'stats': {'total': 0, 'attribues': 0, 'disponibles': 0, 'par_vendeur': []}})
        rows = ws.get_all_values()
        if len(rows) < 2:
            return jsonify({'success': True, 'stats': {'total': 0, 'attribues': 0, 'disponibles': 0, 'par_vendeur': []}})
        headers = rows[0]
        va_idx = next((i for i, h in enumerate(headers) if 'vendeur_attribue' in h.lower()), -1)
        total = len(rows) - 1
        vendeurs = {}
        attribues = 0
        for row in rows[1:]:
            attr = row[va_idx].strip() if va_idx >= 0 and va_idx < len(row) else ''
            if attr:
                attribues += 1
                if attr not in vendeurs:
                    vendeurs[attr] = 0
                vendeurs[attr] += 1
        # Enrichir noms
        par_vendeur = []
        try:
            gc2 = get_sheets_client()
            mdp_ws = gc2.open_by_key(os.environ.get('GOOGLE_SHEET_ID', '')).sheet1
            mdp_rows = mdp_ws.get_all_values()
            for email, nb in vendeurs.items():
                nom, prenom = email.split('@')[0], ''
                for mr in mdp_rows:
                    if len(mr) > 3 and mr[3].lower() == email.lower():
                        nom, prenom = mr[0], mr[1]
                        break
                par_vendeur.append({'email': email, 'nom': nom, 'prenom': prenom, 'nb_contacts': nb})
        except:
            par_vendeur = [{'email': e, 'nom': e.split('@')[0], 'prenom': '', 'nb_contacts': n} for e, n in vendeurs.items()]
        return jsonify({'success': True, 'stats': {'total': total, 'attribues': attribues, 'disponibles': total - attribues, 'par_vendeur': par_vendeur}})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/base-premium/liste')
@login_required
def base_premium_liste():
    try:
        gc = get_sheets_client()
        sh = gc.open_by_key(PROSPECTION_SHEET_ID)
        try:
            ws = sh.worksheet('LEADS OHM')
        except Exception:
            return jsonify({'success': True, 'prospects': [], 'total': 0, 'page': 1, 'pages': 0})
        rows = ws.get_all_values()
        if len(rows) < 2:
            return jsonify({'success': True, 'prospects': [], 'total': 0, 'page': 1, 'pages': 0})
        headers = rows[0]
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        seg_f = request.args.get('segment', '').upper()
        score_f = int(request.args.get('score_min', 0))
        statut_f = request.args.get('statut_ohm', '')
        annee_f = request.args.get('annee_fin', '')
        has_sign = request.args.get('has_signataire', '') == 'true'
        has_email = request.args.get('has_email', '') == 'true'
        non_attr = request.args.get('non_attribues', '') == 'true'

        def g(row, *names):
            for n in names:
                idx = next((i for i, h in enumerate(headers) if n.lower() in h.lower()), -1)
                if idx >= 0 and idx < len(row) and row[idx].strip():
                    return row[idx].strip()
            return ''

        filtered = []
        for i, row in enumerate(rows[1:], start=2):
            if seg_f and seg_f not in (g(row, 'segment', 'typologie') or '').upper():
                continue
            if score_f:
                try:
                    if int(g(row, 'score') or '0') < score_f: continue
                except: continue
            if statut_f and g(row, 'statut') != statut_f: continue
            if annee_f and annee_f not in (g(row, 'date_fin') or ''): continue
            if has_sign and not g(row, 'signataire'): continue
            if has_email and not g(row, 'email_signataire'): continue
            if non_attr and g(row, 'vendeur_attribue'): continue
            obj = {'_row': i}
            for j, h in enumerate(headers):
                obj[h] = row[j] if j < len(row) else ''
            filtered.append(obj)

        total = len(filtered)
        pages = math.ceil(total / per_page) if total else 0
        start = (page - 1) * per_page
        prospects = filtered[start:start + per_page]
        return jsonify({'success': True, 'prospects': prospects, 'total': total, 'page': page, 'pages': pages})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/base-premium/attribuer', methods=['POST'])
@login_required
def base_premium_attribuer():
    try:
        d = request.get_json()
        rows_list = d.get('rows', [])
        vendeur_email = d.get('vendeur_email', '')
        if not rows_list or not vendeur_email:
            return jsonify({'success': False, 'error': 'Rows et vendeur requis'})
        if len(rows_list) > 20:
            return jsonify({'success': False, 'error': 'Max 20 contacts'})
        gc = get_sheets_client()
        sh = gc.open_by_key(PROSPECTION_SHEET_ID)
        ws = sh.worksheet('LEADS OHM')
        headers = ws.row_values(1)
        col_idx = -1
        for i, h in enumerate(headers):
            if 'vendeur_attribue' in h.lower():
                col_idx = i + 1
                break
        if col_idx < 0:
            col_idx = len(headers) + 1
            ws.update_cell(1, col_idx, 'vendeur_attribue')
        import time
        for row_num in rows_list:
            ws.update_cell(row_num, col_idx, vendeur_email)
            time.sleep(0.3)
        print(f"💎 {len(rows_list)} contacts attribués à {vendeur_email}")
        return jsonify({'success': True, 'attribues': len(rows_list)})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prospection/scraper', methods=['POST'])
@login_required
def prospection_scraper():
    try:
        import subprocess
        d = request.get_json()
        ville = d.get('ville', '').strip()
        secteurs = d.get('secteurs', [])
        if not ville or not secteurs:
            return jsonify({'success': False, 'error': 'Ville et secteurs requis'})

        script = os.path.join(os.path.dirname(__file__), '..', 'scraper_google_places.py')
        if not os.path.exists(script):
            script = '/Users/strategyglobal/Desktop/scraper_google_places.py'

        details = []
        total = 0
        for secteur in secteurs:
            try:
                result = subprocess.run(
                    ['python3', script, secteur, ville],
                    capture_output=True, text=True, timeout=120,
                    cwd=os.path.dirname(script)
                )
                output = result.stdout + result.stderr
                # Parse le résultat
                trouves = 0
                ajoutes = 0
                for line in output.split('\n'):
                    if 'trouvés' in line:
                        import re
                        m = re.search(r'(\d+) trouvés', line)
                        if m: trouves = int(m.group(1))
                    if 'nouvelles lignes' in line:
                        m = re.search(r'(\d+) nouvelles', line)
                        if m: ajoutes = int(m.group(1))
                details.append({'secteur': secteur, 'trouves': trouves, 'ajoutes': ajoutes})
                total += ajoutes
                print(f"🎯 Scraping {secteur}/{ville}: {trouves} trouvés, {ajoutes} ajoutés")
            except subprocess.TimeoutExpired:
                details.append({'secteur': secteur, 'trouves': 0, 'ajoutes': 0, 'error': 'timeout'})
            except Exception as e:
                details.append({'secteur': secteur, 'trouves': 0, 'ajoutes': 0, 'error': str(e)})

        return jsonify({'success': True, 'total_ajoutes': total, 'details': details})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prospection/leads-ohm')
@login_required
def prospection_leads_ohm():
    try:
        gc = get_sheets_client()
        sh = gc.open_by_key(PROSPECTION_SHEET_ID)
        try:
            ws = sh.worksheet('LEADS OHM')
        except Exception:
            return jsonify({'success': True, 'prospects': []})
        rows = ws.get_all_values()
        if len(rows) < 2:
            return jsonify({'success': True, 'prospects': []})

        headers = rows[0]
        seg_f = request.args.get('segment', '')
        annee_f = request.args.get('annee_fin', '')
        statut_f = request.args.get('statut', '')
        non_attr = request.args.get('non_attribues', '') == 'true'
        per_page = int(request.args.get('per_page', 20))

        def g(row, name):
            idx = headers.index(name) if name in headers else -1
            return row[idx] if idx >= 0 and idx < len(row) else ''

        prospects = []
        for i, row in enumerate(rows[1:], start=2):
            if seg_f:
                s = g(row, 'segments') or g(row, 'typologie_contrat') or ''
                if seg_f.upper() not in s.upper(): continue
            if annee_f and annee_f not in (g(row, 'date_fin_livraison') or ''): continue
            if statut_f and (g(row, 'statut') or '') != statut_f: continue
            if non_attr and (g(row, 'vendeur_attribue') or '').strip(): continue
            obj = {'_row': i}
            for j, h in enumerate(headers):
                obj[h] = row[j] if j < len(row) else ''
            prospects.append(obj)
            if len(prospects) >= per_page: break

        return jsonify({'success': True, 'prospects': prospects})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prospection/attribuer-leads', methods=['POST'])
@login_required
def attribuer_leads():
    try:
        d = request.get_json()
        rows_list = d.get('rows', [])
        email_vendeur = d.get('email_vendeur', '')
        if not rows_list or not email_vendeur:
            return jsonify({'success': False, 'error': 'Rows et email requis'})

        gc = get_sheets_client()
        sh = gc.open_by_key(PROSPECTION_SHEET_ID)
        try:
            ws = sh.worksheet('LEADS OHM')
        except Exception:
            return jsonify({'success': False, 'error': 'Feuille LEADS OHM non trouvée'})

        headers = ws.row_values(1)
        col_idx = -1
        for i, h in enumerate(headers):
            if 'vendeur_attribue' in h.lower():
                col_idx = i + 1
                break
        if col_idx < 0:
            col_idx = len(headers) + 1
            ws.update_cell(1, col_idx, 'vendeur_attribue')

        import time
        for row_num in rows_list:
            ws.update_cell(row_num, col_idx, email_vendeur)
            time.sleep(0.3)

        print(f"✅ {len(rows_list)} leads attribués à {email_vendeur}")
        return jsonify({'success': True, 'nb': len(rows_list)})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

def get_next_courtier_number():
    """Génère le prochain numéro de courtier auto-incrémenté"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_json = os.environ.get('GOOGLE_CREDS_JSON', '')
        if not creds_json:
            return None
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ])
        gc = gspread.authorize(creds)
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1
        all_values = ws.get_all_values()
        numbers = []
        for row in all_values[1:]:
            if len(row) > 11 and row[11].strip().isdigit():
                numbers.append(int(row[11]))
        next_num = max(numbers, default=46) + 1
        print(f"📊 Prochain numéro courtier: {next_num}")
        return next_num
    except Exception as e:
        print(f"⚠️ Erreur numéro courtier: {e}")
        return None


def update_role_in_sheets(email, new_role, sheet_id):
    """Met à jour le rôle d'un utilisateur dans un Google Sheet"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_json = os.environ.get('GOOGLE_CREDS_JSON', '')
        if not creds_json:
            return False
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1
        all_values = ws.get_all_values()
        for i, row in enumerate(all_values):
            if len(row) > 3 and row[3].lower() == email.lower():
                # Colonne J = index 10 (0-based) = rôle
                ws.update_cell(i + 1, 10, new_role)
                print(f'✅ Sheets mis à jour: {email} → {new_role} (sheet {sheet_id[:8]}...)')
                return True
        print(f'⚠️ Email {email} non trouvé dans sheet {sheet_id[:8]}...')
        return False
    except Exception as e:
        print(f'❌ Sheets error: {e}')
        return False


@app.route('/api/promote-vendeur', methods=['POST'])
@login_required
def promote_vendeur():
    data = request.get_json()
    email = data.get('email')
    new_role = data.get('role')  # 'vendeur' ou 'referent'

    if not email or new_role not in ['vendeur', 'referent']:
        return jsonify({'error': 'Paramètres invalides'}), 400

    # 1. Google Sheets MDP ZOHO
    sheets_id = os.environ.get('GOOGLE_SHEET_ID', '')
    if sheets_id:
        update_role_in_sheets(email, new_role, sheets_id)

    # 2. CRM Neon (Vercel)
    crm_role = 'REFERENT' if new_role == 'referent' else 'VENDEUR'
    CRM_URL = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
    CRM_API_KEY = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
    try:
        crm_res = requests.post(
            f'{CRM_URL}/api/crm/promote',
            headers={'X-API-Key': CRM_API_KEY, 'Content-Type': 'application/json'},
            json={'email': email, 'role': crm_role},
            timeout=10
        )
        print(f'CRM promote: {crm_res.status_code} — {crm_res.text}')
    except Exception as e:
        print(f'CRM promote error: {e}')

    # 3. Sheets Prospection
    master_sheet_id = os.environ.get('MASTER_SHEET_ID', '')
    if master_sheet_id:
        update_role_in_sheets(email, new_role, master_sheet_id)

    # 4. Création salle Meet si promu référent
    meet_link = None
    if new_role == 'referent':
        try:
            gc = get_sheets_client()
            sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
            ws = gc.open_by_key(sheet_id).sheet1
            rows = ws.get_all_values()
            prenom_ref = ''
            nom_ref = ''
            lien_actuel = ''
            row_idx = -1
            for i, row in enumerate(rows):
                if len(row) > 3 and row[3].strip().lower() == email.lower():
                    prenom_ref = row[1].strip() if len(row) > 1 else ''
                    nom_ref = row[0].strip() if len(row) > 0 else ''
                    lien_actuel = row[12].strip() if len(row) > 12 else ''
                    row_idx = i + 1
                    break
            if not lien_actuel or 'meet.google.com' not in lien_actuel:
                result = create_referent_meet_room(prenom_ref, nom_ref, email)
                meet_link = result['meet_link']
                if row_idx > 0:
                    ws.update_cell(row_idx, 13, meet_link)
                CRM_URL2 = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
                CRM_KEY2 = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
                requests.post(f'{CRM_URL2}/api/crm/update-lien-visio',
                    headers={'X-API-Key': CRM_KEY2, 'Content-Type': 'application/json'},
                    json={'email': email, 'lien': meet_link}, timeout=10)
                print(f'✅ Salle Meet créée pour promotion: {meet_link}')
            else:
                print(f'⏭️ Salle Meet existe déjà: {lien_actuel}')
        except Exception as e:
            print(f'⚠️ Meet promotion error: {e}')

    # 5. Si rétrogradation referent → vendeur, orpheliner ses vendeurs
    orphelins = []
    if new_role == 'vendeur':
        orphelins = orpheliner_vendeurs(email)

    return jsonify({'success': True, 'email': email, 'role': new_role, 'meet_link': meet_link, 'orphelins': orphelins})


@app.route('/api/count-vendeurs-sous-referent')
@login_required
def count_vendeurs_sous_referent():
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'count': 0})
    try:
        gc = get_sheets_client()
        ws = gc.open_by_key(os.environ.get('GOOGLE_SHEET_ID', '')).sheet1
        rows = ws.get_all_values()
        count = sum(1 for row in rows if len(row) > 6 and row[6].strip().lower() == email)
        return jsonify({'count': count})
    except:
        return jsonify({'count': 0})


@app.route('/api/changer-referent', methods=['POST'])
@login_required
def changer_referent():
    data = request.get_json()
    vendeur_email = (data.get('vendeur_email') or '').strip().lower()
    referent_email = (data.get('referent_email') or '').strip().lower()

    if not vendeur_email:
        return jsonify({'success': False, 'error': 'Email vendeur manquant'}), 400

    results = {}

    # 1. Sheets colonne G (REFERANT) = index 7 en 1-based
    try:
        gc = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
        ws = gc.open_by_key(sheet_id).sheet1
        rows = ws.get_all_values()
        found = False
        for i, row in enumerate(rows):
            if len(row) > 3 and row[3].strip().lower() == vendeur_email:
                ws.update_cell(i + 1, 7, referent_email)
                print(f'✅ Sheets: référent de {vendeur_email} → {referent_email or "aucun"}')
                results['sheets'] = 'ok'
                found = True
                break
        if not found:
            results['sheets'] = 'vendeur introuvable'
    except Exception as e:
        print(f'❌ Erreur Sheets changer-referent: {e}')
        results['sheets'] = str(e)

    # 2. CRM Neon
    try:
        crm_url = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
        crm_key = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
        r = requests.post(
            f'{crm_url}/api/crm/assign-referent',
            headers={'X-API-Key': crm_key, 'Content-Type': 'application/json'},
            json={'vendeur_email': vendeur_email, 'referent_email': referent_email or None},
            timeout=15
        )
        print(f'CRM assign-referent: {r.status_code}')
        results['crm'] = 'ok' if r.ok else f'status {r.status_code}'
    except Exception as e:
        print(f'⚠️ CRM assign-referent error: {e}')
        results['crm'] = str(e)

    return jsonify({'success': True, 'results': results})


@app.route('/api/toggle-vendeur', methods=['POST'])
@login_required
def toggle_vendeur():
    data = request.get_json()
    email = data.get('email')
    actif = data.get('actif')  # True ou False

    if not email or actif is None:
        return jsonify({'error': 'Paramètres invalides'}), 400

    # 1. Google Sheets — colonne K = STATUT
    gc = get_sheets_client()
    if gc:
        try:
            sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
            sh = gc.open_by_key(sheet_id)
            ws = sh.sheet1
            all_values = ws.get_all_values()
            for i, row in enumerate(all_values):
                if len(row) > 3 and row[3].lower() == email.lower():
                    ws.update_cell(i + 1, 11, 'actif' if actif else 'inactif')
                    print(f'✅ Sheets toggle: {email} → {"actif" if actif else "inactif"}')
                    break
        except Exception as e:
            print(f'❌ Sheets toggle error: {e}')

    # 2. CRM Neon
    CRM_URL = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
    CRM_API_KEY = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
    try:
        requests.post(
            f'{CRM_URL}/api/crm/toggle',
            headers={'X-API-Key': CRM_API_KEY, 'Content-Type': 'application/json'},
            json={'email': email, 'actif': actif},
            timeout=10
        )
    except Exception as e:
        print(f'CRM toggle error: {e}')

    # 3. Orpheliner si désactivation d'un référent
    orphelins = []
    if not actif:
        try:
            gc2 = get_sheets_client()
            ws2 = gc2.open_by_key(os.environ.get('GOOGLE_SHEET_ID', '')).sheet1
            for row in ws2.get_all_values():
                if len(row) > 9 and row[3].strip().lower() == email.lower() and row[9].strip().lower() == 'referent':
                    orphelins = orpheliner_vendeurs(email)
                    break
        except: pass

    return jsonify({'success': True, 'email': email, 'actif': actif, 'orphelins': orphelins})


@app.route('/api/supprimer-vendeur', methods=['POST'])
@login_required
def supprimer_vendeur():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email requis'}), 400

    # 1. Google Sheets — marque SUPPRIMÉ dans colonne K
    gc = get_sheets_client()
    if gc:
        try:
            sheet_id = os.environ.get('GOOGLE_SHEET_ID', '')
            sh = gc.open_by_key(sheet_id)
            ws = sh.sheet1
            all_values = ws.get_all_values()
            for i, row in enumerate(all_values):
                if len(row) > 3 and row[3].lower() == email.lower():
                    ws.update_cell(i + 1, 11, 'supprime')
                    print(f'✅ Sheets supprimé: {email}')
                    break
        except Exception as e:
            print(f'❌ Sheets suppress error: {e}')

    # 2. CRM Neon — marque inactif + deletedAt
    CRM_URL = os.environ.get('CRM_URL', 'https://liliwatt-crm-8ofi.vercel.app')
    CRM_API_KEY = os.environ.get('CRM_API_KEY', 'liliwatt-crm-api-key-2026')
    try:
        requests.post(
            f'{CRM_URL}/api/crm/delete-user',
            headers={'X-API-Key': CRM_API_KEY, 'Content-Type': 'application/json'},
            json={'email': email},
            timeout=10
        )
    except Exception as e:
        print(f'CRM delete error: {e}')

    # 3. Orpheliner si c'est un référent
    orphelins = orpheliner_vendeurs(email)

    return jsonify({'success': True, 'email': email, 'orphelins': orphelins})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
