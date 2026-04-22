"""
Service de création automatique de salles Google Meet
pour les référents LILIWATT.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uuid
import os
import json

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]
ADMIN_EMAIL = 'contact@liliwatt.fr'


def _get_credentials():
    """Charge les credentials depuis fichier local ou variable d'env."""
    # Fichier local
    local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'liliwatt-eddcc0bc9e18.json')
    if os.path.exists(local_file):
        return service_account.Credentials.from_service_account_file(local_file, scopes=SCOPES)

    # Variable d'env (pour Render)
    creds_json = os.environ.get('GOOGLE_CREDS_JSON', '')
    if creds_json:
        creds_dict = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

    raise Exception('Aucun credentials Google trouvé')


def get_calendar_service():
    credentials = _get_credentials()
    delegated = credentials.with_subject(ADMIN_EMAIL)
    return build('calendar', 'v3', credentials=delegated)


def create_referent_meet_room(prenom, nom, email):
    """Crée la salle Meet permanente d'un référent."""
    service = get_calendar_service()

    now = datetime.utcnow()
    start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    end = start.replace(hour=19, minute=0)

    title = f"🎥 Salon de {prenom}"
    description = (
        f"Salon de visio permanent de {prenom} {nom}\n"
        f"Email référent : {email}\n\n"
        f"Les vendeurs de l'équipe rejoignent via le CRM."
    )

    event = {
        'summary': title,
        'description': description,
        'start': {'dateTime': start.isoformat() + 'Z', 'timeZone': 'Europe/Paris'},
        'end': {'dateTime': end.isoformat() + 'Z', 'timeZone': 'Europe/Paris'},
        'recurrence': ['RRULE:FREQ=DAILY'],
        'attendees': [{'email': email, 'responseStatus': 'accepted'}],
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        },
        'guestsCanModify': False,
        'guestsCanInviteOthers': True
    }

    result = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1,
        sendUpdates='none'
    ).execute()

    meet_link = result.get('hangoutLink')
    event_id = result.get('id')
    print(f"✅ Salle Meet créée pour {prenom} {nom}: {meet_link}")

    return {'meet_link': meet_link, 'event_id': event_id}
