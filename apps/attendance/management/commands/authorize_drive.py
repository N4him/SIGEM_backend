from django.core.management.base import BaseCommand
from google_auth_oauthlib.flow import InstalledAppFlow
from apps.attendance.models import SystemGoogleToken

SCOPES = ['https://www.googleapis.com/auth/drive']

class Command(BaseCommand):
    help = 'Autoriza Google Drive (una sola vez)'

    def handle(self, *args, **options):
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials/credentials.json',
            SCOPES
        )
        creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
        SystemGoogleToken.save_from_creds(creds)
        self.stdout.write(self.style.SUCCESS('✓ Token guardado en base de datos'))