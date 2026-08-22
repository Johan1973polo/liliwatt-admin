/**
 * Propage automatiquement une modification de la colonne N (TELEPHONE)
 * du Sheet MDP ZOHO VENDEURS vers liliwatt-admin, qui met a jour :
 *   - le Sheet (idempotent)
 *   - le CRM Neon
 *   - la signature Zoho du vendeur
 *
 * INSTALLATION :
 *   1. Ouvrir le Sheet MDP ZOHO VENDEURS
 *   2. Extensions > Apps Script
 *   3. Coller ce code
 *   4. Parametres > Proprietes du script :
 *        ADMIN_URL   = https://liliwatt-admin.onrender.com
 *        HOOK_KEY    = (meme valeur que SHEET_HOOK_KEY sur Render)
 *   5. Declencheurs > Ajouter un declencheur :
 *        Fonction       : onEditTelephone
 *        Evenement      : Sur modification
 *        Type           : A partir de la feuille de calcul
 *   NE PAS nommer la fonction onEdit() : un trigger simple ne peut pas
 *   appeler UrlFetchApp. Il faut un trigger INSTALLABLE.
 */

function onEditTelephone(e) {
  // Ignorer si pas la Feuille 1
  var sheet = e.range.getSheet();
  if (sheet.getName() !== 'Feuille 1') return;

  // Ignorer si pas la colonne N (14)
  var col = e.range.getColumn();
  if (col !== 14) return;

  // Ignorer la ligne 1 (en-tetes)
  var row = e.range.getRow();
  if (row <= 1) return;

  // Lire l'email en colonne D de la meme ligne
  var email = sheet.getRange(row, 4).getValue();
  if (!email || email.toString().indexOf('@') === -1) return;
  email = email.toString().trim().toLowerCase();

  // Normaliser le telephone
  var tel = (e.range.getValue() || '').toString().replace(/[\s.\-]/g, '');
  if (!tel) return;

  // Valider le format francais
  if (!/^0[1-9][0-9]{8}$/.test(tel)) {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      'Format invalide : ' + tel + ' — attendu : 10 chiffres commencant par 0',
      'Telephone', 5
    );
    return;
  }

  // Appeler liliwatt-admin
  var props = PropertiesService.getScriptProperties();
  var url = props.getProperty('ADMIN_URL') || 'https://liliwatt-admin.onrender.com';
  var key = props.getProperty('HOOK_KEY');
  if (!key) {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      'HOOK_KEY non configure dans les proprietes du script',
      'Erreur', 5
    );
    return;
  }

  try {
    var response = UrlFetchApp.fetch(url + '/api/corriger-telephone', {
      method: 'post',
      contentType: 'application/json',
      headers: { 'X-API-Key': key },
      payload: JSON.stringify({ email: email, nouveau_telephone: tel }),
      muteHttpExceptions: true
    });

    var code = response.getResponseCode();
    var body = JSON.parse(response.getContentText());

    if (code === 200 && body.success && !body.partial) {
      SpreadsheetApp.getActiveSpreadsheet().toast(
        'Telephone de ' + email + ' mis a jour (Sheet + CRM + Zoho)',
        'Succes', 3
      );
    } else if (body.partial) {
      var erreurs = (body.errors || []).join(', ');
      SpreadsheetApp.getActiveSpreadsheet().toast(
        'Partiel : ' + erreurs,
        'Attention', 5
      );
    } else {
      SpreadsheetApp.getActiveSpreadsheet().toast(
        'Erreur ' + code + ' : ' + (body.error || 'inconnue'),
        'Echec', 5
      );
    }
  } catch (err) {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      'Erreur reseau : ' + err.message,
      'Echec', 5
    );
  }
}
