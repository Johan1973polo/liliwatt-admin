# Guide de Déploiement LILIWATT Admin

## Résumé du Projet

Application Flask pour gérer automatiquement les comptes email Zoho Mail des commerciaux LILIWATT.

## Credentials Zoho OAuth (testés et validés)

### Configuration OAuth
```
Client ID: 1000.9W93I9JDA3GN47P3ZBAWAEVCQI2RWU
Client Secret: 4a13cc8af6573803ea9084dca1931542648d96e4a0
Refresh Token: 1000.b405dc6c268231a8f7f827d1898d5011.32fce7278b68d4ded24688514710e322
Organization ID: 20113501048
```

### Scopes autorisés
- `ZohoMail.organization.accounts.ALL`
- `ZohoMail.organization.accounts.CREATE`
- `ZohoMail.organization.accounts.DELETE`
- `ZohoMail.organization.accounts.READ`

## Tests Réalisés

### ✅ Test 1: Obtention du token d'accès
```bash
curl -s -X POST "https://accounts.zoho.eu/oauth/v2/token" \
  -d "refresh_token=1000.b405dc6c268231a8f7f827d1898d5011.32fce7278b68d4ded24688514710e322" \
  -d "client_id=1000.9W93I9JDA3GN47P3ZBAWAEVCQI2RWU" \
  -d "client_secret=4a13cc8af6573803ea9084dca1931542648d96e4a0" \
  -d "grant_type=refresh_token"
```
**Résultat:** ✅ Token obtenu avec succès

### ✅ Test 2: Création d'utilisateur
```bash
curl -X POST "https://mail.zoho.eu/api/organization/20113501048/accounts" \
  -H "Authorization: Zoho-oauthtoken [TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Jean",
    "lastName": "Dupont",
    "primaryEmailAddress": "jean.dupont@liliwatt.fr",
    "password": "Liliwatt2026"
  }'
```
**Résultat:** ✅ Utilisateur créé (Status 201)
- Email: jean.dupont@liliwatt.fr
- Account ID: 8412233000000002002
- ZUID: 20113514806

### ✅ Test 3: Suppression d'utilisateur
```bash
curl -X DELETE "https://mail.zoho.eu/api/organization/20113501048/accounts" \
  -H "Authorization: Zoho-oauthtoken [TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{"emailList": ["jean.dupont@liliwatt.fr"]}'
```
**Résultat:** ✅ Utilisateur supprimé (Status 200)

## Corrections API Apportées

### 1. Champ email
- ❌ Avant: `emailAddress`
- ✅ Après: `primaryEmailAddress`

### 2. Champs requis
- ❌ Avant: displayName, role (causaient erreur PATTERN_NOT_MATCHED)
- ✅ Après: Uniquement firstName, lastName, primaryEmailAddress, password

### 3. Suppression d'utilisateur
- ❌ Avant: DELETE /accounts/{accountId}
- ✅ Après: DELETE /accounts avec JSON {"emailList": ["email@liliwatt.fr"]}

## Variables d'Environnement pour Render.com

```bash
# Flask
SECRET_KEY=<générer avec: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_PASSWORD=liliwatt2026

# Zoho Mail API
ZOHO_CLIENT_ID=1000.9W93I9JDA3GN47P3ZBAWAEVCQI2RWU
ZOHO_CLIENT_SECRET=4a13cc8af6573803ea9084dca1931542648d96e4a0
ZOHO_REFRESH_TOKEN=1000.b405dc6c268231a8f7f827d1898d5011.32fce7278b68d4ded24688514710e322
ZOHO_ORG_ID=20113501048

# Zoho SMTP (pour emails de bienvenue)
ZOHO_SMTP_USER=bo@liliwatt.fr
ZOHO_SMTP_PASS=<mot-de-passe-smtp-zoho>
```

## Déploiement sur Render.com

### Étape 1: Créer le Web Service
1. Aller sur https://dashboard.render.com
2. Cliquer sur "New +" → "Web Service"
3. Connecter le repository: `https://github.com/Johan1973polo/liliwatt-admin`

### Étape 2: Configuration
```
Name: liliwatt-admin
Region: Frankfurt (EU Central)
Branch: main
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
Instance Type: Free (ou Starter pour production)
```

### Étape 3: Variables d'environnement
Ajouter toutes les variables listées ci-dessus dans "Environment Variables"

### Étape 4: Déployer
Cliquer sur "Create Web Service"

L'application sera accessible sur: `https://liliwatt-admin.onrender.com`

## Fonctionnalités Validées

✅ Authentification admin sécurisée
✅ Création automatique de comptes Zoho
✅ Génération automatique d'emails (prenom.nom@liliwatt.fr)
✅ Génération automatique de mots de passe sécurisés (11 caractères: 2 maj, 4 min, 3 chiffres, 2 spéciaux)
✅ Normalisation des accents (é→e, à→a, etc.)
✅ Sauvegarde automatique dans Google Sheets (feuille COMMERCIAUX)
✅ Application automatique de signature HTML LILIWATT
✅ Email de bienvenue automatique avec identifiants (envoyé depuis bo@liliwatt.fr à l'email personnel)
✅ SMTP SSL configuré sur port 465 (timeout 25s)
✅ Envoi email en thread séparé pour performance optimale
✅ Liste des utilisateurs existants
✅ Suppression d'utilisateurs
✅ Interface responsive avec branding LILIWATT

## Signature Email Générée

Format HTML avec:
- Dégradé violet/fuchsia (#7c3aed → #d946ef)
- Nom, prénom, poste
- Téléphone cliquable
- Email cliquable
- Site web: www.liliwatt.fr
- Adresse: 59 rue de Ponthieu, Bureau 326, 75008 Paris
- Baseline: "18% d'économies en moyenne"

## Workflow de Création d'Utilisateur

### Formulaire
1. **Prénom** - Ex: Jean
2. **Nom** - Ex: Dupont
3. **Poste** - Ex: Business Developer
4. **Téléphone** - Ex: 07 00 00 00 00
5. **Email personnel** - Ex: jean.dupont@gmail.com (pour recevoir les identifiants)

### Process Automatique
1. Génération automatique de l'email pro: `prenom.nom@liliwatt.fr`
2. Normalisation des accents et espaces
3. Génération automatique d'un mot de passe sécurisé (11 caractères)
4. Création du compte Zoho Mail
5. **Sauvegarde dans Google Sheets** (feuille COMMERCIAUX)
6. Application de la signature HTML LILIWATT
7. Envoi de l'email de bienvenue à l'adresse personnelle avec:
   - Identifiant Zoho
   - Mot de passe généré
   - Lien vers mail.zoho.eu

### Sécurité Mot de Passe
- **Longueur:** 11 caractères
- **Composition:** 2 majuscules + 4 minuscules + 3 chiffres + 2 caractères spéciaux (@#$!%&)
- **Ordre:** Aléatoire (shuffle)
- **Exemple:** `Ax3@kpTs#9q`

## Performance et Optimisations

### Threading Email
L'envoi de l'email de bienvenue se fait dans un **thread séparé** (daemon) pour:
- Ne pas bloquer la réponse HTTP
- Éviter les timeouts sur Render.com (30s max)
- Retourner immédiatement les identifiants à l'admin
- Le worker continue l'envoi en arrière-plan

### SMTP Configuration
- **Port:** 465 (SSL)
- **Timeout:** 25 secondes
- **Host:** smtp.zoho.eu
- Si l'email échoue, l'utilisateur est quand même créé dans Zoho

### Google Sheets Integration
L'application sauvegarde automatiquement chaque nouvel utilisateur dans Google Sheets:

**Spreadsheet ID:** `1dVBjsqQKxgZ2JQmJ0Q9BvZJRw8YD6aF8hXNvKzLiLiw`
**Worksheet:** `COMMERCIAUX`

**Colonnes:**
1. **NOM** - Nom en majuscules
2. **PRENOM** - Prénom avec première lettre en majuscule
3. **MDP ZOHO** - Mot de passe généré
4. **EMAIL** - Adresse email Zoho (prenom.nom@liliwatt.fr)
5. **POSTE** - Fonction
6. **DATE** - Date et heure de création (JJ/MM/AAAA HH:MM)

**Service Account:**
- Email: `liliwatt-sheets@liliwatt.iam.gserviceaccount.com`
- Fichier: `liliwatt-eddcc0bc9e18.json` (non versionné)
- Permissions: Éditeur sur le Google Sheet

**Sur Render.com:**
1. Uploader le fichier JSON via l'interface Render
2. Placer dans le répertoire racine du projet
3. L'app le trouvera automatiquement

### Temps de Réponse Typiques
- Création utilisateur Zoho: ~2-3 secondes
- Application signature: ~500ms
- Réponse HTTP totale: **< 5 secondes**
- Envoi email (en arrière-plan): ~3-5 secondes

## URLs Importantes

- **Repository GitHub:** https://github.com/Johan1973polo/liliwatt-admin
- **Zoho Mail Admin:** https://mailadmin.zoho.eu
- **Zoho API Console:** https://api-console.zoho.eu

## Support Technique

En cas de problème:
1. Vérifier les logs sur Render.com
2. Vérifier que le refresh token est valide
3. Vérifier que l'Organization ID est correct
4. Tester les endpoints API directement avec curl

---

**Document créé le:** 1er avril 2026
**Status:** ✅ Prêt pour déploiement production
