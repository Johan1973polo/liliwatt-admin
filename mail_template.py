"""
Gabarit unique des e-mails LILIWATT — charte sombre néon.

Tous les mails automatisés passent par mail_liliwatt(). Les couleurs et la
structure ne sont définies qu'ICI : une modification de charte se fait en un
seul endroit.

Contraintes e-mail respectées :
  - tables uniquement (pas de flex/grid)
  - couleurs hexadécimales (rgba() est ignoré par Outlook)
  - aucun dégradé (Outlook ne les rend pas), aplats de couleur
  - aucune image distante : le texte reste lisible images bloquées
  - styles inline (les <style> sont supprimés par Gmail)
"""

# ── Palette : le seul endroit où les couleurs sont définies ──
FOND_PAGE     = '#0a0616'
FOND_CARTE    = '#120b26'
FOND_ENTETE   = '#160d2e'
FOND_BLOC     = '#1a1033'
FOND_PIED     = '#0d0819'

TEXTE         = '#e9e4f5'
TEXTE_FORT    = '#ffffff'
TEXTE_DOUX    = '#cbc3e3'
TEXTE_MENTION = '#7e718f'

VIOLET        = '#7c3aed'
VIOLET_CLAIR  = '#a855f7'
LAVANDE       = '#c4b5fd'
MAUVE         = '#c084fc'
ROSE          = '#f472b6'

_BASELINE = ('Courtier &Eacute;nergie B2B &amp; B2C &nbsp;&bull;&nbsp; '
             '<span style="color:%s;">18%% d\'&eacute;conomies en moyenne</span> &nbsp;&bull;&nbsp; '
             'Sans engagement &nbsp;&bull;&nbsp; Sans coupure &nbsp;&bull;&nbsp; '
             '18+ fournisseurs compar&eacute;s') % ROSE


def mail_liliwatt(titre_accent, titre_blanc, corps, avec_coordonnees=True, avec_baseline=True):
    """Construit un e-mail LILIWATT complet.

    titre_accent : première partie du titre, en violet   (ex. "FIN DE")
    titre_blanc  : seconde partie du titre, en blanc     (ex. "COLLABORATION")
    corps        : HTML libre, déjà mis en forme — utiliser les briques
                   paragraphe(), bloc(), bouton(), tableau_infos()
    """
    coordonnees = _coordonnees() if avec_coordonnees else ''
    baseline = f'''
  <tr>
    <td align="center" style="background-color:{FOND_ENTETE};padding:16px 24px;">
      <span style="color:{TEXTE_DOUX};font-size:11px;line-height:20px;">{_BASELINE}</span>
    </td>
  </tr>''' if avec_baseline else ''

    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{FOND_PAGE};margin:0;padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:{FOND_CARTE};border-radius:16px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">

  <tr>
    <td align="center" style="background-color:{FOND_ENTETE};padding:32px 24px 24px;">
      <div style="font-size:34px;font-weight:800;color:{TEXTE_FORT};letter-spacing:6px;line-height:1;">&#9889;&nbsp;LILIWATT&nbsp;&#9889;</div>
      <div style="font-size:11px;color:{LAVANDE};letter-spacing:3px;margin-top:8px;">COURTAGE &Eacute;NERGIE &bull; B2B &amp; B2C</div>
    </td>
  </tr>

  <tr>
    <td align="center" style="background-color:{FOND_ENTETE};padding:0 24px 32px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border:2px solid {VIOLET};border-radius:12px;">
        <tr><td align="center" style="padding:20px 16px;">
          <span style="font-size:24px;font-weight:800;color:{VIOLET_CLAIR};letter-spacing:2px;">{titre_accent} </span><span style="font-size:24px;font-weight:800;color:{TEXTE_FORT};letter-spacing:2px;">{titre_blanc}</span>
        </td></tr>
      </table>
    </td>
  </tr>

  <tr>
    <td style="padding:36px 40px 28px;color:{TEXTE};font-size:15px;line-height:26px;">
{corps}
    </td>
  </tr>
{coordonnees}{baseline}
  <tr>
    <td align="center" style="background-color:{FOND_PIED};padding:16px 24px;">
      <span style="color:{TEXTE_MENTION};font-size:11px;line-height:18px;">
        LILIWATT &mdash; LILISTRAT STRAT&Eacute;GIE SAS<br>
        59 rue de Ponthieu, Bureau 326 &mdash; 75008 Paris
      </span>
    </td>
  </tr>

</table>
</td></tr>
</table>'''


# ────────── Briques de contenu ──────────

def paragraphe(html, marge_bas=22):
    return f'      <p style="margin:0 0 {marge_bas}px;">{html}</p>'


def accent(texte, couleur=VIOLET_CLAIR):
    """Met un fragment en valeur dans un paragraphe."""
    return f'<strong style="color:{couleur};">{texte}</strong>'


def bloc(contenu, bordure=VIOLET):
    """Encadré sombre à liseré violet — identifiants, récapitulatifs."""
    return f'''      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{FOND_BLOC};border-left:4px solid {bordure};border-radius:10px;margin:0 0 22px;">
        <tr><td style="padding:18px 20px;color:{TEXTE};font-size:14px;line-height:24px;">{contenu}</td></tr>
      </table>'''


def tableau_infos(lignes):
    """lignes : liste de (libellé, valeur HTML)."""
    corps = ''.join(
        f'<tr><td style="padding:5px 0;color:{MAUVE};font-weight:700;width:140px;font-size:13px;">{lib}</td>'
        f'<td style="padding:5px 0;color:{TEXTE_FORT};font-size:14px;">{val}</td></tr>'
        for lib, val in lignes
    )
    return f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{corps}</table>'


def bouton(libelle, url):
    """Bouton blanc sur fond sombre — bien rendu partout, Outlook compris."""
    return f'''      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:8px auto 24px;">
        <tr><td align="center" bgcolor="{TEXTE_FORT}" style="border-radius:50px;">
          <a href="{url}" style="display:inline-block;padding:15px 38px;color:{VIOLET};font-size:15px;font-weight:700;text-decoration:none;letter-spacing:0.5px;">{libelle}</a>
        </td></tr>
      </table>'''


def signature_equipe():
    equipe = accent('L&rsquo;&eacute;quipe LILIWATT')
    return f'      <p style="margin:0;">Bien cordialement,<br>{equipe}</p>'


def _coordonnees():
    def case(libelle, valeur, padding_bas):
        return (f'<td width="50%" style="padding:{padding_bas};color:{TEXTE};font-size:13px;line-height:20px;" valign="top">'
                f'<div style="color:{MAUVE};font-size:11px;letter-spacing:1.5px;font-weight:700;">{libelle}</div>'
                f'<div style="margin-top:4px;color:{TEXTE_FORT};">{valeur}</div></td>')

    tel = f'<a href="tel:0184160856" style="color:{TEXTE_FORT};text-decoration:none;">01 84 16 08 56</a>'
    mail = f'<a href="mailto:bo@liliwatt.fr" style="color:{TEXTE_FORT};text-decoration:none;">bo@liliwatt.fr</a>'
    web = f'<a href="https://www.liliwatt.fr" style="color:{TEXTE_FORT};text-decoration:none;">www.liliwatt.fr</a>'

    return f'''
  <tr>
    <td style="padding:0 24px 24px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{FOND_BLOC};border-radius:12px;">
        <tr>{case('T&Eacute;L&Eacute;PHONE', tel, '18px 20px')}{case('EMAIL', mail, '18px 20px')}</tr>
        <tr>{case('WEB', web, '0 20px 18px')}{case('ADRESSE', '59 rue de Ponthieu<br>75008 Paris', '0 20px 18px')}</tr>
      </table>
    </td>
  </tr>'''
