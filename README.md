# SIGEM Backend

**SIGEM** (Sistema de Gestión de Monitores) es una API REST construida con Django y Django REST Framework para administrar la asistencia de monitores universitarios: registro de entrada/salida con validación por geolocalización, evidencia fotográfica respaldada en Google Drive, gestión de salas y reportes administrativos.

Desarrollado para la **Escuela de Ingeniería de Sistemas y Computación de la Universidad del Valle**.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.15-ff1709?logo=django&logoColor=white)
![License](https://img.shields.io/badge/license-Unlicensed-lightgrey)

---

## Tabla de contenido

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Modelo de dominio](#modelo-de-dominio)
- [Puesta en marcha](#puesta-en-marcha)
- [Variables de entorno](#variables-de-entorno)
- [Integración con Google Drive](#integración-con-google-drive)
- [Referencia de la API](#referencia-de-la-api)
- [Permisos y roles](#permisos-y-roles)
- [Manejo de errores](#manejo-de-errores)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Características

- 🔐 **Autenticación JWT** (access/refresh) con login por correo electrónico.
- 📍 **Check-in / check-out geolocalizado**: valida que el monitor esté dentro de un radio permitido alrededor de la sala (distancia Haversine).
- 📸 **Evidencia fotográfica** subida automáticamente a una carpeta de Google Drive organizada por sala, con manejo de tokens OAuth2 persistidos en base de datos y renovación automática.
- 🏫 **Gestión de salas** con coordenadas y radio de tolerancia configurable por sala.
- 🧑‍💼 **Panel administrativo**: alta/baja de monitores, activación/desactivación, reportes filtrables (semanal, mensual, por rango, por sala o por monitor) con exportación a CSV.
- 📊 **Resumen semanal de horas** trabajadas por monitor.
- 🚦 **Rate limiting** en el check-in para evitar abuso del endpoint.
- 🧾 **Manejo de errores uniforme** en toda la API mediante un exception handler personalizado.
- 🗂️ Roles diferenciados (`monitor` / `admin`) con permisos declarativos vía DRF.

## Arquitectura

El proyecto sigue una estructura Django modular por dominio (`apps/`), con un núcleo compartido (`core/`) responsable de configuración global, permisos y manejo de excepciones.

```
Cliente (web/móvil)
        │  JWT Bearer
        ▼
   core/urls.py  ──►  apps.users     (auth, perfil, admin de usuarios)
                 ──►  apps.rooms     (catálogo de salas)
                 ──►  apps.attendance(check-in/out, reportes, Google Drive)
                       │
                       └──► Google Drive API (evidencia fotográfica)
```

Tareas asíncronas y programadas quedan preparadas mediante `django-q2` (incluido en dependencias) para trabajos en segundo plano.

## Stack tecnológico

| Categoría         | Tecnología                                         |
|-------------------|-----------------------------------------------------|
| Framework         | Django 4.2 · Django REST Framework 3.15             |
| Autenticación     | djangorestframework-simplejwt (JWT)                  |
| Base de datos     | PostgreSQL (psycopg2-binary)                         |
| Almacenamiento    | Google Drive API (google-api-python-client)          |
| Archivos estáticos| WhiteNoise                                            |
| CORS              | django-cors-headers                                   |
| Rate limiting     | django-ratelimit                                       |
| Tareas en segundo plano | django-q2                                        |
| Servidor WSGI     | Gunicorn                                              |
| Configuración     | python-decouple (variables de entorno)                |

## Modelo de dominio

**`CustomUser`** (`apps.users`)
- PK `UUID`, autenticación por `email`.
- Rol `monitor` o `admin` (`Role` choices).
- Propiedades de conveniencia `is_monitor` / `is_admin`.

**`Room`** (`apps.rooms`)
- Nombre, ubicación, `latitude` / `longitude` y `allowed_radius_m` (radio de tolerancia GPS, por defecto 50 m).

**`AttendanceRecord`** (`apps.attendance`)
- PK `UUID`, relacionado con `CustomUser` y `Room` (`PROTECT` para preservar histórico).
- Estados de jornada: `open` / `closed`.
- Estados de foto: `pending`, `uploaded`, `failed`, `na`.
- Coordenadas de entrada y salida, horas trabajadas calculadas automáticamente (`calculate_hours`).

**`SystemGoogleToken`** (`apps.attendance`)
- Almacena las credenciales OAuth2 de la cuenta de servicio/usuario autorizado para Google Drive, con renovación automática del `access_token`.

## Puesta en marcha

### Requisitos previos

- Python 3.10+
- PostgreSQL
- Cuenta de Google Cloud con la API de Drive habilitada (solo si se usará subida de fotos)

### Instalación

```bash
git clone https://github.com/N4him/SIGEM_backend.git
cd SIGEM_backend

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuración

Crea un archivo `.env` en la raíz del proyecto (ver [Variables de entorno](#variables-de-entorno)) y luego:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La API quedará disponible en `http://localhost:8000/`.

## Variables de entorno

| Variable                        | Descripción                                              | Valor por defecto                    |
|----------------------------------|-----------------------------------------------------------|----------------------------------------|
| `SECRET_KEY`                    | Clave secreta de Django                                   | inseguro (cambiar en producción)      |
| `DEBUG`                         | Modo debug                                                 | `True`                                 |
| `ALLOWED_HOSTS`                 | Hosts permitidos, separados por coma                       | `*`                                     |
| `DB_NAME`                       | Nombre de la base de datos PostgreSQL                       | —                                       |
| `DB_USER`                       | Usuario de PostgreSQL                                       | —                                       |
| `DB_PASSWORD`                   | Contraseña de PostgreSQL                                     | —                                       |
| `DB_HOST`                       | Host de PostgreSQL                                           | —                                       |
| `DB_PORT`                       | Puerto de PostgreSQL                                          | `5432`                                  |
| `CORS_ALLOWED_ORIGINS`          | Orígenes permitidos, separados por coma                      | `http://localhost:3000`                |
| `CORS_ALLOW_ALL_ORIGINS`       | Permitir todos los orígenes (solo desarrollo)                | `True`                                   |
| `GOOGLE_APPLICATION_CREDENTIALS`| Ruta al archivo de credenciales de Google                    | `credentials/drive_service_account.json` |
| `DRIVE_ROOT_FOLDER_ID`          | ID de la carpeta raíz de Google Drive donde se organizan las fotos por sala | — |

> **Nota:** el proyecto define `DATABASES` dos veces en `core/settings.py` (SQLite y luego PostgreSQL); la segunda asignación sobreescribe la primera, por lo que **PostgreSQL es obligatorio** salvo que se ajuste la configuración.

## Integración con Google Drive

La subida de evidencia fotográfica utiliza OAuth2 con credenciales persistidas en la tabla `SystemGoogleToken`, evitando reautorizaciones manuales frecuentes.

1. Descarga el archivo `credentials.json` de un proyecto de Google Cloud con la API de Drive habilitada y colócalo en `credentials/credentials.json`.
2. Ejecuta el comando de autorización (abre un flujo OAuth local una sola vez):

   ```bash
   python manage.py authorize_drive
   ```

3. El token resultante se guarda en base de datos y se renueva automáticamente en cada solicitud expirada.

Las fotos se organizan en subcarpetas por sala dentro de `DRIVE_ROOT_FOLDER_ID`, con nombre de archivo `AAAA-MM-DD_HH-MM_Nombre_Apellido.jpg`, y se marcan públicas para lectura (`anyone: reader`) para poder consultarlas desde los reportes.

Si la subida falla (timeout, error de token, etc.), el check-out **no se bloquea**: el registro queda marcado con `photo_status = failed` y el proceso continúa.

## Referencia de la API

Todas las rutas están prefijadas según lo definido en `core/urls.py`. Las respuestas exitosas siguen, en general, el formato `{"success": true, ...}`.

### Autenticación — `/api/auth/`

| Método | Endpoint          | Descripción                          | Auth |
|--------|-------------------|---------------------------------------|------|
| POST   | `/register/`      | Registro de un nuevo monitor           | No   |
| POST   | `/login/`         | Login (email + password) → tokens JWT  | No   |
| POST   | `/refresh/`       | Renovar access token                   | No   |
| GET/PATCH | `/me/`         | Ver / actualizar perfil propio          | Sí   |

### Salas — `/api/rooms/`

| Método | Endpoint | Descripción                     | Auth              |
|--------|----------|-----------------------------------|--------------------|
| GET    | `/`      | Listar salas activas                | Monitor o Admin     |

### Asistencia — `/api/attendance/`

| Método | Endpoint            | Descripción                                                    | Auth    |
|--------|---------------------|-------------------------------------------------------------------|---------|
| POST   | `/checkin/`         | Registrar entrada (valida GPS, 10 solicitudes/min por usuario)      | Monitor |
| POST   | `/checkout/`        | Registrar salida (foto opcional, sube a Drive)                     | Monitor |
| GET    | `/my-records/`      | Historial propio, filtrable por `from` / `to`                       | Monitor |
| GET    | `/weekly-summary/`  | Horas trabajadas de lunes a sábado de la semana actual               | Monitor |

### Administración — `/api/admin/`

| Método         | Endpoint                     | Descripción                                          | Auth  |
|-----------------|-------------------------------|--------------------------------------------------------|-------|
| GET             | `/users/`                    | Listar monitores                                        | Admin |
| POST            | `/users/create/`             | Crear nuevo monitor                                      | Admin |
| GET/PATCH/DELETE| `/users/<uuid:pk>/`          | Ver, actualizar o eliminar un monitor                     | Admin |
| PATCH           | `/users/<uuid:pk>/toggle/`   | Activar/desactivar un monitor                             | Admin |
| GET             | `/reports/`                  | Reportes de asistencia (`filter`, `from`, `to`, `room_id`, `user_id`, `export=csv\|json`) | Admin |
| GET             | `/reports/filters/`          | Opciones disponibles para filtrar (salas y monitores)      | Admin |

## Permisos y roles

Definidos en `core/permissions.py`:

- **`IsMonitor`**: usuario autenticado, activo y con rol `monitor`.
- **`IsAdmin`**: usuario autenticado, activo y con rol `admin`.
- **`IsMonitorOrAdmin`**: cualquier usuario autenticado y activo.

Por defecto, toda la API requiere autenticación (`IsAuthenticated`) salvo los endpoints explícitamente marcados como públicos (registro y login).

## Manejo de errores

Un `EXCEPTION_HANDLER` personalizado (`core/exceptions.py`) envuelve todas las respuestas de error de DRF en un formato consistente:

```json
{
  "success": false,
  "errors": { "...": "detalle del error" },
  "status_code": 400
}
```

## Estructura del proyecto

```
SIGEM_backend/
├── core/
│   ├── settings.py       # Configuración global (DB, JWT, CORS, logging, Drive)
│   ├── urls.py           # Enrutamiento raíz
│   ├── permissions.py    # Permisos por rol
│   └── exceptions.py     # Manejo uniforme de errores
├── apps/
│   ├── users/            # Autenticación, perfil y administración de monitores
│   ├── rooms/             # Catálogo de salas con geolocalización
│   └── attendance/        # Check-in/out, integración con Google Drive, reportes
│       └── management/commands/authorize_drive.py
├── manage.py
└── requirements.txt
```

---

Desarrollado para la gestión de monitorías de la **Universidad del Valle**.
