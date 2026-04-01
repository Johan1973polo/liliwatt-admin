from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import requests
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'liliwatt-admin-secret-2026')

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'liliwatt2026')
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
        password = d.get('password', '').strip()

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
                'displayName': f'{prenom} {nom}',
                'firstName': prenom,
                'lastName': nom,
                'emailAddress': email_local,
                'password': password,
                'role': 'MemberUser'
            }
        )
        result = r.json()
        print(f"Création utilisateur: {result}")

        if result.get('status', {}).get('code') in [200, 201] or 'data' in result:
            account_id = result.get('data', {}).get('accountId', '')

            # Appliquer la signature
            if account_id:
                sig_html = make_signature(prenom, nom, poste, telephone, email_local)
                requests.post(
                    f'https://mail.zoho.eu/api/organization/{ZOHO_ORG_ID}/accounts/{account_id}/signatures',
                    headers={'Authorization': f'Zoho-oauthtoken {token}', 'Content-Type': 'application/json'},
                    json={'signatureName': 'LILIWATT', 'signature': sig_html, 'isDefault': True}
                )

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

@app.route('/api/users/<account_id>', methods=['DELETE'])
@login_required
def delete_user(account_id):
    try:
        token = get_zoho_token()
        r = requests.delete(
            f'https://mail.zoho.eu/api/organization/{ZOHO_ORG_ID}/accounts/{account_id}',
            headers={'Authorization': f'Zoho-oauthtoken {token}'}
        )
        return jsonify({'success': True, 'result': r.json()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
