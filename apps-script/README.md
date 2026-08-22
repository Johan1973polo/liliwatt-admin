# Apps Script — Synchronisation telephone

## Ou est-ce installe ?

Le script `telephone-sync.gs` est attache au Google Sheet **MDP ZOHO VENDEURS**
(ID: `11gVGMBtqMUhPh70yjMgjW-yLDht6fO0KqWJAF53ASXk`).

Acces : ouvrir le Sheet > Extensions > Apps Script.

## Ce qu'il fait

Quand la colonne N (TELEPHONE) est modifiee a la main dans la Feuille 1,
le script appelle `POST /api/corriger-telephone` sur liliwatt-admin (Render).

Cette route met a jour :
- le Sheet (idempotent — la valeur est deja la)
- le CRM Neon (via `/api/crm/update-phone`)
- la signature Zoho du vendeur (GET puis PUT sur LILIWATT)

## Configuration requise

### Proprietes du script (Parametres > Proprietes du script)

| Cle         | Valeur                                      |
|-------------|---------------------------------------------|
| `ADMIN_URL` | `https://liliwatt-admin.onrender.com`       |
| `HOOK_KEY`  | Meme valeur que `SHEET_HOOK_KEY` sur Render |

### Variable d'environnement Render (liliwatt-admin)

| Cle              | Valeur                    |
|------------------|---------------------------|
| `SHEET_HOOK_KEY` | Une cle secrete partagee  |

### Declencheur

- Fonction : `onEditTelephone`
- Evenement : Sur modification (pas onEdit simple)
- Source : A partir de la feuille de calcul

## Pour redeployer

1. Copier le contenu de `telephone-sync.gs`
2. Le coller dans Apps Script du Sheet
3. Verifier les proprietes du script
4. Verifier que le declencheur installable existe
