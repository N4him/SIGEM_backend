import math
from django.utils import timezone
from django.conf import settings


# ── GPS ──────────────────────────────────────────────────────────────────────

def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Distancia en metros entre dos coordenadas GPS usando fórmula Haversine."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def validate_location(lat: float, lon: float, room) -> bool:
    """Verifica que el usuario esté dentro del radio permitido de la sala."""
    distance = haversine_distance(lat, lon, room.latitude, room.longitude)
    return distance <= room.allowed_radius_m


# ── Google Drive ──────────────────────────────────────────────────────────────

def get_drive_service():
    import pickle
    import os
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = None

    token_path = 'credentials/token.pickle'
    creds_path = 'credentials/credentials.json'

    # 1. Cargar token si existe
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # 2. Si no hay credenciales válidas
    if not creds or not creds.valid:
        # 🔄 refrescar si se puede
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 🔥 LOGIN SOLO LA PRIMERA VEZ
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path,
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        # 💾 guardar token
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)


def get_folder(service, folder_name: str, parent_id: str) -> str:
    query = (
        f"name='{folder_name}' and "
        f"'{parent_id}' in parents and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false"
    )

    results = service.files().list(
        q=query,
        fields='files(id)',
    ).execute()

    files = results.get('files', [])

    if files:
        return files[0]['id']

    # 🔴 Aquí ya NO crea nada
    return None

def upload_photo_to_drive(photo_file, user, room) -> str:
    print(f"[Drive] Iniciando subida — sala: {room.name}, monitor: {user.get_full_name()}")

    try:
        from googleapiclient.http import MediaIoBaseUpload
        import io

        service = get_drive_service()
        root_folder_id = settings.DRIVE_ROOT_FOLDER_ID

        # Carpeta por sala
        folder_name = room.name.replace(' ', '_')
        folder_id = get_folder(service, folder_name, root_folder_id)

        # Nombre del archivo con timestamp y monitor
        timestamp = timezone.now().strftime('%Y-%m-%d_%H-%M')
        monitor_name = f"{user.first_name}_{user.last_name}".replace(' ', '_')
        filename = f"{timestamp}_{monitor_name}.jpg"

        file_metadata = {
            'name': filename,
            'parents': [folder_id],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(photo_file.read()),
            mimetype='image/jpeg',
            resumable=False
        )
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
        ).execute()

        file_id = uploaded['id']

        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"

    except Exception as e:
        import traceback
        print(f"[Drive] Error al subir foto: {e}")
        print(f"[Drive] Detalle: {traceback.format_exc()}")
        return ''