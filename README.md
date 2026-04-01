# LILIWATT Admin

Application d'administration pour gérer les comptes email Zoho des commerciaux LILIWATT.

## Fonctionnalités

- ✅ Création automatique de comptes email Zoho
- ✅ Génération automatique d'adresses email (prenom.nom@liliwatt.fr)
- ✅ Génération automatique de mots de passe sécurisés (11 caractères)
- ✅ Sauvegarde automatique dans Google Sheets (feuille COMMERCIAUX)
- ✅ Application automatique de la signature LILIWATT avec branding
- ✅ Email de bienvenue automatique avec identifiants (envoyé à l'email personnel)
- ✅ Liste et gestion des utilisateurs existants
- ✅ Suppression de comptes utilisateurs
- ✅ Interface admin sécurisée avec authentification
- ✅ Design moderne avec dégradés violets (branding LILIWATT)

## Installation locale

```bash
# Cloner le repo
git clone https://github.com/Johan1973polo/liliwatt-admin.git
cd liliwatt-admin

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos vraies valeurs

# Lancer l'application
python app.py
```

L'application sera accessible sur http://localhost:5001

## Déploiement sur Render.com

1. Créer un nouveau Web Service sur Render.com
2. Connecter le repository GitHub : `Johan1973polo/liliwatt-admin`
3. Configurer les variables d'environnement :
   - `SECRET_KEY` : clé secrète Flask (générer avec `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `ADMIN_PASSWORD` : mot de passe admin
   - `ZOHO_CLIENT_ID` : ID client OAuth Zoho
   - `ZOHO_CLIENT_SECRET` : Secret client OAuth Zoho
   - `ZOHO_REFRESH_TOKEN` : Token de rafraîchissement Zoho
   - `ZOHO_ORG_ID` : ID de l'organisation Zoho
   - `ZOHO_SMTP_USER` : Adresse email d'envoi (bo@liliwatt.fr)
   - `ZOHO_SMTP_PASS` : Mot de passe SMTP Zoho
4. Build Command : `pip install -r requirements.txt`
5. Start Command : `gunicorn app:app`

## Configuration Zoho OAuth

### Étape 1 : Obtenir le code d'autorisation

Visitez l'URL suivante (remplacer les valeurs) :

```
https://accounts.zoho.eu/oauth/v2/auth?scope=ZohoMail.organization.accounts.ALL&client_id=VOTRE_CLIENT_ID&response_type=code&access_type=offline&redirect_uri=VOTRE_REDIRECT_URI
```

### Étape 2 : Échanger le code contre un refresh token

```bash
curl -X POST "https://accounts.zoho.eu/oauth/v2/token" \
  -d "code=VOTRE_CODE" \
  -d "client_id=VOTRE_CLIENT_ID" \
  -d "client_secret=VOTRE_CLIENT_SECRET" \
  -d "redirect_uri=VOTRE_REDIRECT_URI" \
  -d "grant_type=authorization_code"
```

Récupérez le `refresh_token` de la réponse.

## API Endpoints

### Authentification
- `GET /login` - Page de connexion
- `POST /login` - Authentification admin
- `GET /logout` - Déconnexion

### Dashboard
- `GET /` - Dashboard principal (protégé)

### Gestion utilisateurs
- `GET /api/users` - Liste tous les utilisateurs Zoho
- `POST /api/users` - Créer un nouvel utilisateur
- `DELETE /api/users/<account_id>` - Supprimer un utilisateur

## Structure du projet

```
liliwatt-admin/
├── app.py              # Application Flask principale
├── requirements.txt    # Dépendances Python
├── Procfile           # Configuration Render.com
├── .env.example       # Exemple de variables d'environnement
├── .gitignore         # Fichiers à ignorer
├── templates/
│   ├── login.html     # Page de connexion
│   └── index.html     # Dashboard admin
└── static/            # Assets statiques (vide pour l'instant)
```

## Signature email générée

La signature email LILIWATT inclut :
- Nom et prénom du commercial
- Poste
- Téléphone
- Email
- Site web (liliwatt.fr)
- Adresse (59 rue de Ponthieu, Bureau 326, 75008 Paris)
- Baseline marketing (18% d'économies en moyenne)
- Design avec dégradés violets (#7c3aed → #d946ef)

## Sécurité

- ⚠️ Ne jamais commiter le fichier `.env` avec les vraies credentials
- ⚠️ Utiliser des mots de passe forts pour `SECRET_KEY` et `ADMIN_PASSWORD`
- ⚠️ Le refresh token Zoho ne doit jamais être exposé publiquement
- ✅ Toutes les routes admin sont protégées par authentification
- ✅ Les sessions utilisent des cookies sécurisés

## Support

Pour tout problème, contacter l'équipe technique LILIWATT.

---

**© 2026 LILIWATT - Courtage Énergie B2B & B2C**
