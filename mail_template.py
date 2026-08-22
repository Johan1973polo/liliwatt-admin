"""
Gabarit unique des e-mails LILIWATT — deux thèmes, une seule structure.

  theme='sombre'  (défaut) : mails INTERNES — équipe, référents, back-office
  theme='clair'            : mails EXTERNES — candidats, invitations

Ne JAMAIS convertir avec ce gabarit : newsletter, bienvenue newsletter,
demande de parrainage. Ils gardent leur design d'origine.

Contraintes e-mail respectées :
  - tables uniquement (pas de flex/grid)
  - couleurs hexadécimales (rgba() est ignoré par Outlook)
  - aucun dégradé (Outlook ne les rend pas), aplats de couleur
  - styles inline (les <style> sont supprimés par Gmail)
  - les seules images sont celles du pied de page : le mail reste
    entièrement lisible si elles sont bloquées
"""

# ── Les deux palettes : le seul endroit où les couleurs sont définies ──
THEMES = {
    'sombre': {
        'fond_page':   '#17102e', 'fond_carte':  '#211846',
        'fond_entete': '#2a1f57', 'fond_bloc':   '#312468',
        'texte':       '#f2eefb', 'texte_fort':  '#ffffff',
        'texte_doux':  '#ddd3f2',
        'violet':      '#8b5cf6', 'accent':      '#c4a5fd',
        'lavande':     '#ddd0ff', 'libelle':     '#e0c9ff',
        'rose':        '#f9a8d4',
        'titre_entete': '#ffffff',
        'bouton_fond': '#ffffff', 'bouton_texte': '#5b21b6',
    },
    'clair': {
        'fond_page':   '#f5f3ff', 'fond_carte':  '#ffffff',
        'fond_entete': '#1e1b4b', 'fond_bloc':   '#f5f3ff',
        'texte':       '#332d5c', 'texte_fort':  '#1e1b4b',
        'texte_doux':  '#6b6490',
        'violet':      '#7c3aed', 'accent':      '#7c3aed',
        'lavande':     '#ddd0ff', 'libelle':     '#7c3aed',
        'rose':        '#d946ef',
        'titre_entete': '#ffffff',
        'bouton_fond': '#7c3aed', 'bouton_texte': '#ffffff',
    },
}

# Constantes exportées pour les appels accent(texte, COULEUR)
ROSE = 'rose'
TEXTE_FORT = 'texte_fort'
ACCENT = 'accent'

# ── Pied de page (images hébergées sur Render) ──
ASSETS = 'https://liliwatt-admin.onrender.com/static/newsletter'
FOND_PIED = '#1b1338'
PIED_TEXTE = '#ddd3f2'
PIED_MENTION = '#a99fc4'
PIED_ACCENT = '#c4a5fd'

RESEAUX = [
    ('LinkedIn',  'https://www.linkedin.com/company/liliwatt/',             'linkedin.png'),
    ('Instagram', 'https://www.instagram.com/liliwatt.fr/',                 'instagram.png'),
    ('X',         'https://x.com/liliwattfrance',                           'x.png'),
    ('YouTube',   'https://www.youtube.com/@liliwattfrance',                'youtube.png'),
    ('Facebook',  'https://www.facebook.com/profile.php?id=61577269553280', 'facebook.png'),
]

NAVIGATION = [
    ('Nos offres',        'https://liliwatt.fr/offres.html'),
    ('Qui sommes-nous ?', 'https://liliwatt.fr/a-propos.html'),
    ('Actualités',        'https://liliwatt.fr/actualites.html'),
    ('Contact',           'https://liliwatt.fr/contact.html'),
]

LILISTRAT_URL = 'https://lilistrat.fr'


def _p(theme):
    return THEMES[theme]


def mail_liliwatt(titre_accent, titre_blanc, corps, theme='sombre', avec_baseline=True):
    """Construit un e-mail LILIWATT complet.

    theme : 'sombre' pour l'interne, 'clair' pour les candidats et invitations
    """
    c = _p(theme)
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{c['fond_page']};margin:0;padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:{c['fond_carte']};border-radius:16px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">

  <tr>
    <td align="center" style="background-color:{c['fond_entete']};padding:32px 24px 24px;">
      <div style="font-size:34px;font-weight:800;color:{c['titre_entete']};letter-spacing:6px;line-height:1;">&#9889;&nbsp;LILIWATT&nbsp;&#9889;</div>
      <div style="font-size:11px;color:{c['lavande']};letter-spacing:3px;margin-top:8px;">COURTAGE &Eacute;NERGIE &bull; B2B &amp; B2C</div>
    </td>
  </tr>

  <tr>
    <td align="center" style="background-color:{c['fond_entete']};padding:0 24px 32px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border:2px solid {c['violet']};border-radius:12px;">
        <tr><td align="center" style="padding:20px 16px;">
          <span style="font-size:24px;font-weight:800;color:{c['accent'] if theme == 'sombre' else '#c4a5fd'};letter-spacing:2px;">{titre_accent} </span><span style="font-size:24px;font-weight:800;color:#ffffff;letter-spacing:2px;">{titre_blanc}</span>
        </td></tr>
      </table>
    </td>
  </tr>

  <tr>
    <td style="padding:36px 40px 28px;color:{c['texte']};font-size:15px;line-height:26px;">
{corps}
    </td>
  </tr>
{_baseline(theme) if avec_baseline else ''}{signature()}
</table>
</td></tr>
</table>'''


# ────────── Briques de contenu ──────────

def paragraphe(html, marge_bas=22, theme='sombre'):
    return f'      <p style="margin:0 0 {marge_bas}px;color:{_p(theme)["texte"]};">{html}</p>'


def accent(texte, couleur=ACCENT, theme='sombre'):
    """couleur : ACCENT, ROSE ou TEXTE_FORT."""
    return f'<strong style="color:{_p(theme)[couleur]};">{texte}</strong>'


def titre_section(texte, theme='sombre'):
    return f'      <p style="margin:0 0 14px;color:{_p(theme)["texte_fort"]};font-size:18px;font-weight:700;">{texte}</p>'


def bloc(contenu, theme='sombre'):
    c = _p(theme)
    return f'''      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{c['fond_bloc']};border-left:4px solid {c['violet']};border-radius:10px;margin:0 0 22px;">
        <tr><td style="padding:18px 20px;color:{c['texte']};font-size:14px;line-height:24px;">{contenu}</td></tr>
      </table>'''


def tableau_infos(lignes, theme='sombre'):
    c = _p(theme)
    corps = ''.join(
        f'<tr>'
        f'<td style="padding:6px 12px 6px 0;color:{c["libelle"]};font-weight:700;width:140px;font-size:13px;vertical-align:top;">{lib}</td>'
        f'<td style="padding:6px 0;color:{c["texte_fort"]};font-size:14px;">{val}</td>'
        f'</tr>'
        for lib, val in lignes
    )
    return f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{corps}</table>'


def bouton(libelle, url, theme='sombre'):
    c = _p(theme)
    return f'''      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:8px auto 24px;">
        <tr><td align="center" bgcolor="{c['bouton_fond']}" style="border-radius:50px;">
          <a href="{url}" style="display:inline-block;padding:15px 38px;color:{c['bouton_texte']};font-size:15px;font-weight:700;text-decoration:none;letter-spacing:0.5px;">{libelle}</a>
        </td></tr>
      </table>'''


def signature_equipe(theme='sombre'):
    c = _p(theme)
    return f'      <p style="margin:0;color:{c["texte"]};">Bien cordialement,<br><strong style="color:{c["accent"]};">L&rsquo;&eacute;quipe LILIWATT</strong></p>'


# ────────── Bandeau et signature ──────────

def _baseline(theme='sombre'):
    c = _p(theme)
    fond = c['fond_entete'] if theme == 'sombre' else '#ede9fe'
    txt = c['texte_doux'] if theme == 'sombre' else '#4c1d95'
    rose = c['rose']
    return f'''
  <tr>
    <td align="center" style="background-color:{fond};padding:18px 24px;">
      <div style="color:{txt};font-size:12px;line-height:22px;">
        Courtier &Eacute;nergie B2B &amp; B2C &nbsp;&middot;&nbsp; <span style="color:{rose};font-weight:700;">18&nbsp;% d&rsquo;&eacute;conomies en moyenne</span>
      </div>
      <div style="color:{txt};font-size:12px;line-height:22px;">
        Sans engagement &nbsp;&middot;&nbsp; Sans coupure &nbsp;&middot;&nbsp; 18+ fournisseurs compar&eacute;s
      </div>
    </td>
  </tr>'''


def signature():
    """Signature complète — identique dans les deux thèmes, présente dans
    TOUS les mails. Logo, réseaux, navigation, coordonnées, LILIWATT by LILISTRAT."""

    icones = ''.join(
        f'<td style="padding:0 7px;">'
        f'<a href="{url}" style="text-decoration:none;">'
        f'<img src="{ASSETS}/{img}" width="30" height="30" alt="{nom}" '
        f'style="display:block;border:0;width:30px;height:30px;"></a></td>'
        for nom, url, img in RESEAUX
    )

    nav = f'<span style="color:#8b5cf6;">&nbsp;|&nbsp;</span>'.join(
        f'<a href="{url}" style="color:#ffffff;text-decoration:none;font-size:13px;font-weight:600;">{lib}</a>'
        for lib, url in NAVIGATION
    )

    return f'''
  <tr>
    <td align="center" style="background-color:{FOND_PIED};padding:32px 24px 16px;">
      <a href="https://liliwatt.fr" style="text-decoration:none;">
        <img src="{ASSETS}/logo_blanc.png" width="170" alt="LILIWATT" style="display:block;border:0;width:170px;max-width:170px;margin:0 auto 22px;">
      </a>

      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto 22px;">
        <tr>{icones}</tr>
      </table>

      <div style="margin:0 0 18px;line-height:24px;">{nav}</div>

      <div style="color:{PIED_TEXTE};font-size:12px;line-height:21px;">
        LILIWATT &middot; 59 rue de Ponthieu, Bureau 326, 75008 Paris<br>
        <a href="mailto:contact@liliwatt.fr" style="color:{PIED_ACCENT};text-decoration:none;">contact@liliwatt.fr</a>
        &nbsp;&middot;&nbsp;
        <a href="tel:0184160856" style="color:{PIED_ACCENT};text-decoration:none;">01 84 16 08 56</a>
      </div>
    </td>
  </tr>

  <tr>
    <td align="center" style="background-color:{FOND_PIED};padding:0 24px 26px;">
      <a href="{LILISTRAT_URL}" style="text-decoration:none;">
        <span style="color:#ffffff;font-size:14px;font-weight:700;letter-spacing:1px;">LILIWATT</span><span style="color:{PIED_TEXTE};font-size:13px;"> by </span><span style="color:{PIED_ACCENT};font-size:14px;font-weight:700;letter-spacing:1px;text-decoration:underline;">LILISTRAT</span>
      </a>
      <div style="color:{PIED_MENTION};font-size:11px;line-height:18px;margin-top:10px;">
        LILISTRAT STRAT&Eacute;GIE SAS au capital de 10&nbsp;000&nbsp;&euro; &middot; SIREN 103&nbsp;572&nbsp;947<br>
        59 rue de Ponthieu, Bureau 326 &mdash; 75008 Paris
      </div>
    </td>
  </tr>'''
