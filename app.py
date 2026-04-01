from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import requests
import json
from functools import wraps
from datetime import datetime

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



def save_to_sheet(prenom, nom, email, password, poste):
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
        ws.append_row([
            nom.upper(),
            prenom.capitalize(),
            password
        ])
        print(f"✅ {nom} {prenom} enregistré dans Google Sheets")
        return True
    except Exception as e:
        print(f"⚠️ Erreur Google Sheets : {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def make_signature(prenom, nom, poste, telephone, email):
    return f"""<div style="font-family:Arial,sans-serif;max-width:480px;">
  <div style="background:linear-gradient(135deg,#7c3aed,#d946ef);height:4px;border-radius:2px;margin-bottom:16px;"></div>
  <div style="margin-bottom:12px;">
    <div style="font-size:16px;font-weight:700;color:#1e1b4b;">{prenom} {nom}</div>
    <div style="font-size:10px;font-weight:600;color:#7c3aed;letter-spacing:1.5px;text-transform:uppercase;">{poste}</div>
    <div style="font-size:10px;font-weight:600;color:#7c3aed;letter-spacing:1px;text-transform:uppercase;">LILIWATT — Courtage Énergie B2B &amp; B2C</div>
  </div>
  <table style="border-collapse:collapse;font-size:13px;">
    <tr><td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">Tél</td><td><a href="tel:{telephone.replace(' ','')}" style="color:#1e1b4b;text-decoration:none;font-weight:600;">{telephone}</a></td></tr>
    <tr><td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">Email</td><td><a href="mailto:{email}" style="color:#7c3aed;text-decoration:none;font-weight:600;">{email}</a></td></tr>
    <tr><td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">Web</td><td><a href="https://liliwatt.fr" style="color:#7c3aed;text-decoration:none;font-weight:600;">www.liliwatt.fr</a></td></tr>
    <tr><td style="padding:3px 12px 3px 0;color:#9ca3af;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;vertical-align:top;">Adresse</td><td style="color:#374151;">59 rue de Ponthieu, Bureau 326<br>75008 Paris</td></tr>
  </table>
  <div style="margin:14px 0;height:1px;background:linear-gradient(to right,#7c3aed,#d946ef,transparent);"></div>
  <div style="font-size:11px;color:#6b7280;">Courtier Énergie B2B &amp; B2C<br><span style="color:#7c3aed;font-weight:700;">18% d'économies en moyenne</span> — Sans engagement • Sans coupure • 18+ fournisseurs comparés</div>
  <div style="background:linear-gradient(135deg,#7c3aed,#d946ef);height:2px;border-radius:2px;margin-top:14px;"></div>
</div>"""


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

def send_welcome_email(prenom, nom, email, password, email_perso='', account_id_zoho=''):
    """Envoie l'email de bienvenue via API Zoho Mail (pas SMTP)"""
    try:
        destinataire = email_perso if email_perso else email
        
        # Récupérer un token Zoho
        token_r = requests.post('https://accounts.zoho.eu/oauth/v2/token', data={
            'refresh_token': ZOHO_REFRESH_TOKEN,
            'client_id': ZOHO_CLIENT_ID,
            'client_secret': ZOHO_CLIENT_SECRET,
            'grant_type': 'refresh_token'
        }, timeout=15)
        token = token_r.json().get('access_token')
        
        if not token:
            print("⚠️ Token Zoho non obtenu pour email")
            return False
        
        html_body = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#1e1b4b,#7c3aed);padding:32px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="color:white;font-size:28px;font-weight:800;letter-spacing:3px;margin:0;">LILIWATT</h1>
    <p style="color:rgba(255,255,255,0.8);margin:8px 0 0;font-size:13px;letter-spacing:1px;text-transform:uppercase;">Courtage Énergie B2B &amp; B2C</p>
  </div>
  <div style="background:#f5f3ff;padding:32px;border-radius:0 0 12px 12px;">
    <p style="font-size:16px;color:#1e1b4b;margin-bottom:24px;">Bonjour <strong>{prenom}</strong>,</p>
    <p style="color:#374151;line-height:1.6;">Bienvenue dans l'équipe LILIWATT ! Voici votre environnement de travail :</p>
    <div style="background:white;border-radius:10px;padding:24px;margin:24px 0;border-left:4px solid #7c3aed;">
      <table style="width:100%;font-size:14px;border-collapse:collapse;">
        <tr><td style="padding:10px 0;color:#6b7280;font-weight:700;text-transform:uppercase;font-size:11px;letter-spacing:1px;width:140px;">Messagerie</td><td style="padding:10px 0;color:#1e1b4b;font-weight:600;">mail.zoho.eu</td></tr>
        <tr style="border-top:1px solid #f0eeff;"><td style="padding:10px 0;color:#6b7280;font-weight:700;text-transform:uppercase;font-size:11px;letter-spacing:1px;">Identifiant</td><td style="padding:10px 0;color:#7c3aed;font-weight:700;">{email}</td></tr>
        <tr style="border-top:1px solid #f0eeff;"><td style="padding:10px 0;color:#6b7280;font-weight:700;text-transform:uppercase;font-size:11px;letter-spacing:1px;">Mot de passe</td><td style="padding:10px 0;color:#1e1b4b;font-weight:700;font-size:16px;">{password}</td></tr>
      </table>
    </div>
    <div style="background:#ede9fe;border-radius:10px;padding:16px;margin-bottom:24px;">
      <p style="margin:0;font-size:13px;color:#5b21b6;">⚠️ <strong>Important :</strong> Changez votre mot de passe dès votre première connexion.</p>
    </div>
    <a href="https://mail.zoho.eu" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#d946ef);color:white;padding:14px 32px;border-radius:50px;text-decoration:none;font-weight:700;font-size:14px;">Accéder à ma messagerie</a>

    <div style="margin-top:24px;padding:16px;background:#faf5ff;border-radius:10px;border:1px solid #e9d5ff;">
      <p style="margin:0 0 12px;font-weight:700;color:#1e1b4b;font-size:13px;">📝 Votre signature email personnalisée</p>
      <p style="margin:0 0 12px;font-size:12px;color:#6b7280;">Copiez ce code dans <a href="https://mail.zoho.eu/zm/#settings/signatures" style="color:#7c3aed;">Paramètres → Signatures</a> :</p>
      <div style="background:white;border-radius:8px;padding:12px;border:1px solid #e9d5ff;">
        <strong style="color:#1e1b4b;">{prenom} {nom}</strong><br>
        <span style="color:#7c3aed;font-size:12px;">{poste} — LILIWATT</span><br><br>
        Tél : {telephone}<br>
        Email : {email}<br>
        Web : www.liliwatt.fr<br>
        59 rue de Ponthieu, Bureau 326 — 75008 Paris
      </div>
    </div>
    <hr style="border:1px solid #e9d5ff;margin:32px 0;">
    <p style="font-size:12px;color:#9ca3af;margin:0;">LILIWATT — LILISTRAT STRATÉGIE SAS<br>59 rue de Ponthieu, Bureau 326 — 75008 Paris</p>
  </div>
</div>"""

        # Envoyer via API Zoho Mail depuis contact@liliwatt.fr
        # Toujours utiliser ZOHO_ACCOUNT_ID (contact@liliwatt.fr) pour l'envoi
        account_id = os.environ.get('ZOHO_ACCOUNT_ID', '8439060000000002002')
        print(f"📧 Envoi email depuis account_id: {account_id}")
        
        send_r = requests.post(
            f'https://mail.zoho.eu/api/accounts/{account_id}/messages',
            headers={
                'Authorization': f'Zoho-oauthtoken {token}',
                'Content-Type': 'application/json'
            },
            json={
                'fromAddress': 'bo@liliwatt.fr',
                'toAddress': destinataire,
                'subject': 'Bienvenue chez LILIWATT — Vos accès email',
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

@app.route('/')
@login_required
def index():
    return render_template('index.html')

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

        if result.get('status', {}).get('code') in [200, 201] or 'data' in result:
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

            # Enregistrer dans Google Sheets
            save_to_sheet(prenom, nom, email_local, password, poste)
            
            # Récupérer account_id depuis la réponse Zoho
            created_account_id = result.get('data', {}).get('accountId', '')
            
            # Envoyer email directement (pas de thread)
            send_welcome_email(prenom, nom, email_local, password, email_perso, created_account_id)
            
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
