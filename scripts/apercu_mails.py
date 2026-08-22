#!/usr/bin/env python3
"""Génère les 8 mails admin en HTML avec des données factices."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mail_template import mail_liliwatt, paragraphe, accent, bloc, tableau_infos, bouton, signature_equipe, VIOLET, ROSE, TEXTE_FORT

OUT = '/tmp/apercu_mails'
os.makedirs(OUT, exist_ok=True)

def write(name, title, html):
    path = os.path.join(OUT, f'admin_{name}.html')
    with open(path, 'w') as f:
        f.write(html)
    print(f'  {path} — {title}')

# On importe app.py pour utiliser les vraies fonctions
# Mais c'est une app Flask, on ne peut pas l'importer directement.
# On reconstruit les mails avec les mêmes helpers, en reproduisant la logique.

# 1. send_welcome_email
corps = (
    paragraphe(f'Bonjour {accent("Marie")},') +
    paragraphe('Bienvenue chez LILIWATT ! Votre espace collaborateur est pr&ecirc;t.') +
    bloc(tableau_infos([
        ('Plateforme', f'<a href="https://liliwatt-crm.vercel.app" style="color:{VIOLET};text-decoration:none;">liliwatt-crm.vercel.app</a>'),
        ('Email', 'marie.dupont@liliwatt.fr'),
        ('Mot de passe', 'Xk9#mP2v!'),
    ])) +
    bouton('Acc&eacute;der &agrave; mon espace', 'https://liliwatt-crm.vercel.app') +
    bloc(tableau_infos([
        ('Zoho Mail', 'marie.dupont@liliwatt.fr'),
        ('Mot de passe', 'Xk9#mP2v!'),
        ('Connexion', f'<a href="https://mail.zoho.eu" style="color:{VIOLET};text-decoration:none;">mail.zoho.eu</a>'),
    ])) +
    bloc(tableau_infos([
        ('Lien RGPD', f'<a href="https://liliwatt-courtier.onrender.com/rgpd/abc123" style="color:{VIOLET};text-decoration:none;">Ouvrir</a>'),
        ('R&eacute;f&eacute;rent', 'chloe.didier@liliwatt.fr'),
    ])) +
    signature_equipe()
)
write('01_bienvenue', 'VOTRE ESPACE LILIWATT', mail_liliwatt('VOTRE', 'ESPACE LILIWATT', corps))

# 2. notification bo@
corps = (
    paragraphe(f'{accent("Marie DUPONT")} a &eacute;t&eacute; ajout&eacute;(e) &agrave; l\'&eacute;quipe.') +
    bloc(tableau_infos([
        ('Email', 'marie.dupont@liliwatt.fr'),
        ('Mot de passe', 'Xk9#mP2v!'),
        ('Connexion', f'<a href="https://mail.zoho.eu" style="color:{VIOLET};text-decoration:none;">mail.zoho.eu</a>'),
    ])) +
    bloc(tableau_infos([
        ('Poste', 'Courti&egrave;re en &eacute;nergie'),
        ('T&eacute;l&eacute;phone', '0612345678'),
        ('R&eacute;f&eacute;rent', 'chloe.didier@liliwatt.fr'),
        ('Lien RGPD', f'<a href="https://liliwatt-courtier.onrender.com/rgpd/abc123" style="color:{VIOLET};text-decoration:none;">Ouvrir</a>'),
        ('Drive', f'<a href="https://drive.google.com/drive/folders/xxx" style="color:{VIOLET};text-decoration:none;">Ouvrir le dossier</a>'),
    ]))
)
write('02_notif_bo', 'NOUVEAU COMMERCIAL', mail_liliwatt('NOUVEAU', 'COMMERCIAL', corps))

# 3. recrue au référent
corps = (
    paragraphe('Bonjour,') +
    paragraphe('Un nouveau commercial vient d\'&ecirc;tre ajout&eacute; &agrave; votre &eacute;quipe&nbsp;:') +
    bloc(tableau_infos([
        ('Nom', 'Marie DUPONT'),
        ('Poste', 'Courti&egrave;re en &eacute;nergie'),
        ('T&eacute;l&eacute;phone', '0612345678'),
        ('Email', f'<a href="mailto:marie.dupont@liliwatt.fr" style="color:{VIOLET};text-decoration:none;">marie.dupont@liliwatt.fr</a>'),
    ])) +
    paragraphe(f'{accent("&#128222; Merci de prendre contact avec Marie au plus vite pour l\'accueillir et organiser son int&eacute;gration.", ROSE)}')
)
write('03_recrue_referent', 'NOUVELLE RECRUE', mail_liliwatt('NOUVELLE', 'RECRUE', corps))

# 4. envoyer_referent_phase1
corps = (
    paragraphe('Bonjour,') +
    paragraphe('Un nouveau candidat est &agrave; &eacute;valuer pour votre &eacute;quipe.') +
    bloc(tableau_infos([
        ('Nom', 'Pierre MARTIN'),
        ('Email', 'pierre.martin@gmail.com'),
        ('T&eacute;l&eacute;phone', '0698765432'),
        ('Exp&eacute;rience', '3 ans en vente B2B'),
    ])) +
    bouton('Voir le CV', 'https://drive.google.com/file/xxx') +
    bouton('Rejoindre la salle Meet', 'https://meet.google.com/abc-defg-hij') +
    signature_equipe()
)
write('04_profil_candidat', 'PROFIL CANDIDAT', mail_liliwatt('PROFIL', 'CANDIDAT', corps))

# 5. inviter_phase1
corps = (
    paragraphe(f'Bonjour {accent("Pierre")},') +
    paragraphe('Nous avons le plaisir de vous inviter &agrave; une session de pr&eacute;sentation LILIWATT.') +
    bloc(tableau_infos([
        ('Date', 'Lundi 25 ao&ucirc;t 2026'),
        ('Heure', '14h00'),
        ('Dur&eacute;e', '45 minutes'),
    ])) +
    bouton('Rejoindre la session', 'https://meet.google.com/abc-defg-hij') +
    signature_equipe()
)
write('05_invitation_session', 'INVITATION SESSION', mail_liliwatt('INVITATION', 'SESSION', corps))

# 6. inviter_candidat_script (Carole Andria)
corps = (
    paragraphe(f'Bonjour {accent("Sophie")},') +
    paragraphe('Suite &agrave; votre candidature, nous souhaitons vous pr&eacute;senter LILIWATT lors d\'une session en visio.') +
    bloc(tableau_infos([
        ('Date', 'Mardi 26 ao&ucirc;t 2026'),
        ('Heure', '10h00'),
        ('Dur&eacute;e', '30 minutes'),
    ])) +
    bouton('Rejoindre la session', 'https://meet.google.com/xyz-uvwx-yz') +
    paragraphe(f'Carole Andria<br>{accent("carole.andria@liliwatt.fr")}')
)
write('06_invitation_session_ca', 'INVITATION SESSION (CA)', mail_liliwatt('INVITATION', 'SESSION', corps))

# 7. newsletter
corps = (
    paragraphe(f'Chers partenaires,') +
    paragraphe('Voici les derni&egrave;res actualit&eacute;s du march&eacute; de l\'&eacute;nergie.') +
    bloc(
        f'{accent("March&eacute; de l\'&eacute;lectricit&eacute;")}<br><br>'
        'Les prix spot ont baiss&eacute; de 12% ce mois-ci, portant le MWh &agrave; 58&euro;.'
    ) +
    bloc(
        f'{accent("Gaz naturel")}<br><br>'
        'Le PEG reste stable autour de 32&euro;/MWh, avec une tendance baissi&egrave;re.'
    ) +
    paragraphe(f'<a href="https://liliwatt-admin.onrender.com/newsletter/unsub?t=xxx&e=test@test.com" style="color:{VIOLET};font-size:12px;">Se d&eacute;sinscrire</a>', 8)
)
write('07_newsletter', 'LA LETTRE LILIWATT', mail_liliwatt('LA LETTRE', 'LILIWATT', corps))

# 8. bienvenue newsletter
corps = (
    paragraphe(f'Bonjour,') +
    paragraphe('Bienvenue dans la newsletter LILIWATT ! Vous recevrez r&eacute;guli&egrave;rement nos analyses du march&eacute; de l\'&eacute;nergie.') +
    paragraphe(f'<a href="https://liliwatt-admin.onrender.com/newsletter/unsub?t=xxx&e=test@test.com" style="color:{VIOLET};font-size:12px;">Se d&eacute;sinscrire</a>', 8)
)
write('08_bienvenue_newsletter', 'BIENVENUE CHEZ LILIWATT', mail_liliwatt('BIENVENUE', 'CHEZ LILIWATT', corps))

print(f'\n✅ {8} fichiers générés dans {OUT}')
