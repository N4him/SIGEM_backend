import io
import json
import math
import threading
import socket
import logging
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger('apps.attendance')

# ── Lock global para thread safety ───────────────────────────────────────────
_drive_lock = threading.Lock()

# ── Timeout global para Drive ─────────────────────────────────────────────────
socket.setdefaulttimeout(15)  # 15 segundos máximo para cualquier llamada a Drive

# ── GPS ──────────────────────────────────────────────────────────────────────

def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def validate_location(lat: float, lon: float, room) -> bool:
    distance = haversine_distance(lat, lon, room.latitude, room.longitude)
    return distance <= room.allowed_radius_m


# ── Google Drive ──────────────────────────────────────────────────────────────

def get_drive_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from apps.attendance.models import SystemGoogleToken

    with _drive_lock:
        record = SystemGoogleToken.get()
        if not record:
            raise RuntimeError("No hay token. Ejecuta: python manage.py authorize_drive")

        data = json.loads(record.token_json)

        expiry = None
        if data.get('expiry'):
            expiry = datetime.fromisoformat(
                data['expiry'].replace('Z', '+00:00')
            ).replace(tzinfo=None)

        creds = Credentials(
            token=data['token'],
            refresh_token=data['refresh_token'],
            token_uri=data['token_uri'],
            client_id=data['client_id'],
            client_secret=data['client_secret'],
            scopes=data['scopes'],
            expiry=expiry,
        )

        if creds.expired and creds.refresh_token:
            logger.info("[Drive] Access token expirado, renovando automáticamente...")
            try:
                creds.refresh(Request())
                data['token'] = creds.token
                data['expiry'] = creds.expiry.isoformat() if creds.expiry else None
                record.token_json = json.dumps(data)
                record.save()
                logger.info("[Drive] Token renovado y guardado en DB ✓")
            except Exception as e:
                logger.error(f"[Drive] Error al renovar token: {e}", exc_info=True)
                raise

        return build('drive', 'v3', credentials=creds)


def get_or_create_folder(service, folder_name: str, parent_id: str) -> str:
    query = (
        f"name='{folder_name}' and "
        f"'{parent_id}' in parents and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false"
    )
    results = service.files().list(q=query, fields='files(id)').execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']

    metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id],
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    return folder['id']


def upload_photo_to_drive(photo_file, user, room) -> str:
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.errors import HttpError
        from apps.attendance.models import SystemGoogleToken

        logger.info(
            f"[Drive] Iniciando subida — sala: {room.name}, "
            f"monitor: {user.get_full_name()}"
        )

        service = get_drive_service()
        root_folder_id = settings.DRIVE_ROOT_FOLDER_ID
        if not root_folder_id:
            raise ValueError("DRIVE_ROOT_FOLDER_ID no está configurado en settings.")

        folder_name = room.name.replace(' ', '_')
        folder_id = get_or_create_folder(service, folder_name, root_folder_id)

        timestamp = timezone.now().strftime('%Y-%m-%d_%H-%M')
        monitor_name = f"{user.first_name}_{user.last_name}".replace(' ', '_')
        filename = f"{timestamp}_{monitor_name}.jpg"

        file_metadata = {'name': filename, 'parents': [folder_id]}
        photo_bytes = photo_file.read()

        media = MediaIoBaseUpload(
            io.BytesIO(photo_bytes),
            mimetype='image/jpeg',
            resumable=False,
        )

        try:
            uploaded = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
            ).execute()

        except socket.timeout:
            logger.error("[Drive] Timeout al subir foto — Drive tardó más de 15 segundos")
            return None

        except HttpError as e:
            if e.resp.status == 401:
                logger.warning("[Drive] Token inválido, forzando refresh...")
                with _drive_lock:
                    record = SystemGoogleToken.get()
                    data = json.loads(record.token_json)
                    creds = Credentials(
                        token=data['token'],
                        refresh_token=data['refresh_token'],
                        token_uri=data['token_uri'],
                        client_id=data['client_id'],
                        client_secret=data['client_secret'],
                        scopes=data['scopes'],
                    )
                    try:
                        creds.refresh(Request())
                        data['token'] = creds.token
                        data['expiry'] = creds.expiry.isoformat() if creds.expiry else None
                        record.token_json = json.dumps(data)
                        record.save()
                        logger.info("[Drive] Token renovado, reintentando subida...")
                    except Exception as refresh_err:
                        logger.error(
                            f"[Drive] Error al renovar token en retry: {refresh_err}",
                            exc_info=True
                        )
                        return None

                try:
                    service = build('drive', 'v3', credentials=creds)
                    media = MediaIoBaseUpload(
                        io.BytesIO(photo_bytes),
                        mimetype='image/jpeg',
                        resumable=False,
                    )
                    uploaded = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id',
                    ).execute()
                except socket.timeout:
                    logger.error("[Drive] Timeout en reintento de subida")
                    return None
            else:
                logger.error(f"[Drive] HttpError {e.resp.status}: {e}", exc_info=True)
                raise

        file_id = uploaded['id']

        try:
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
            ).execute()
        except socket.timeout:
            logger.warning(
                f"[Drive] Timeout al hacer pública la foto {file_id} — "
                "el archivo se subió pero no es público aún"
            )
        except Exception as perm_err:
            logger.warning(
                f"[Drive] Error al hacer pública la foto: {perm_err}"
            )

        url = f"https://drive.google.com/uc?id={file_id}"
        logger.info(f"[Drive] Foto subida correctamente — {filename}")
        return url

    except socket.timeout:
        logger.error("[Drive] Timeout general al conectar con Google Drive")
        return None

    except Exception as e:
        logger.error(f"[Drive] Error al subir foto: {e}", exc_info=True)
        return None