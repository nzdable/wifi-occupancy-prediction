# Backend Architecture

## Overview

The backend is built with **Django 5.2** and provides REST APIs for WiFi occupancy prediction. It serves a Next.js frontend and integrates with an LSTM machine learning model for occupancy forecasting.

## Project Structure

```
backend/
├── manage.py                                    # Django CLI
├── requirements.txt                             # Python dependencies
├── wifi_occupancy_prediction_project/           # Main Django project config
│   ├── settings.py                              # Django settings
│   ├── urls.py                                  # URL routing (root level)
│   ├── wsgi.py                                  # Production WSGI server entry
│   └── asgi.py                                  # Async server entry (optional)
├── api/                                         # Main API app
│   ├── models.py                                # Database models (currently empty)
│   ├── views.py                                 # API endpoints
│   ├── urls.py                                  # API route definitions
│   ├── admin.py                                 # Django admin config
│   ├── apps.py                                  # App configuration
│   ├── migrations/                              # Database migration history
│   └── services/
│       └── model_service.py                     # ML model prediction service
└── artifacts/                                   # (Generated) ML model files
    ├── lstm_model_v1.h5                         # Trained LSTM model
    ├── scaler_v1.pkl                            # Feature scaler
    └── config_v1.json                           # Model configuration
```

## Core Components

### 1. **Settings & Configuration** (`settings.py`)

**Installed Apps:**

- Django core apps (admin, auth, sessions, etc.)
- `rest_framework` - REST API framework
- `corsheaders` - Cross-Origin Resource Sharing
- `allauth` + `allauth.socialaccount.providers.google` - Social authentication (Google OAuth)

**Middleware Stack:**

```
CORS → Security → WhiteNoise (static files) → Sessions → Auth → Allauth
```

**Database:**

- Default: SQLite (`db.sqlite3`)
- Supports PostgreSQL via `DATABASE_URL` env var using `dj_database_url`

**Authentication:**

- Django's built-in user auth
- Google OAuth via django-allauth
- JWT support via `djangorestframework_simplejwt` (installed but not fully configured in routes yet)

---

### 2. **URL Routing**

#### Root URLs (`wifi_occupancy_prediction_project/urls.py`)

| Route        | Purpose                                                             |
| ------------ | ------------------------------------------------------------------- |
| `/`          | Redirects to frontend URL (from `FRONTEND_URL` setting)             |
| `/accounts/` | Django-allauth authentication endpoints (Google OAuth, login, etc.) |
| `/admin/`    | Django admin panel                                                  |
| `/api/`      | Main API namespace (includes `api/urls.py`)                         |
| `/whoami/`   | Returns authenticated user info or `{"authenticated": false}`       |

#### API URLs (`api/urls.py`)

| Route        | Handler  | Purpose               |
| ------------ | -------- | --------------------- |
| `/api/ping/` | `ping()` | Health check endpoint |

**Future routes** would go here (e.g., `/api/predict/`, `/api/occupancy/`, etc.)

---

### 3. **API Endpoints**

#### Health Check

```
GET /api/ping/
Response: {"ok": true, "service": "django-backend"}
```

Used by load balancers and monitoring tools to verify the backend is running.

#### User Authentication

```
GET /whoami/
Response (authenticated):
  {"authenticated": true, "email": "user@example.com"}
Response (not authenticated):
  {"authenticated": false}
```

---

### 4. **ML Model Service** (`api/services/model_service.py`)

**Purpose:** Wrapper around the trained LSTM model for occupancy prediction.

**Class: `LSTMOccupancyService`**

**Initialization:**

- Loads pre-trained LSTM model from `lstm_model_v1.h5`
- Loads feature scaler from `scaler_v1.pkl` (MinMaxScaler or StandardScaler)
- Loads config from `config_v1.json`
- Instantiated globally as `service` (singleton pattern)

**Methods:**

1. **`predict_next(seq_24: list[float]) -> float`**

   - Takes last 24 hourly occupancy values
   - Returns predicted occupancy for the next hour
   - Process:
     1. Validate input sequence length (must be exactly 24)
     2. Reshape to (24, 1)
     3. Scale using trained scaler
     4. Reshape to (1, 24, 1) for LSTM input (batch, timesteps, features)
     5. Predict and inverse-scale result

2. **`predict_multi(seq_24: list[float], steps: int = 3) -> list[float]`**
   - Predicts multiple hours ahead (e.g., next 3 hours)
   - Uses naive recursive approach: feeds each prediction back into next iteration
   - Returns list of predictions

**Constants:**

```python
SEQ_LEN = 24  # Must match the model training sequence length
```

---

## Technology Stack

| Layer               | Technology                       | Version                      |
| ------------------- | -------------------------------- | ---------------------------- |
| **Framework**       | Django                           | 5.2.7                        |
| **API**             | Django REST Framework            | 3.16.1                       |
| **Auth**            | django-allauth                   | 65.12.0                      |
| **CORS**            | django-cors-headers              | 4.9.0                        |
| **Database**        | SQLite (dev) / PostgreSQL (prod) | -                            |
| **Database Driver** | psycopg                          | 3.2.10                       |
| **ML Model**        | TensorFlow/Keras                 | (inferred from `.h5` format) |
| **Server**          | Gunicorn                         | 23.0.0                       |
| **Static Files**    | WhiteNoise                       | 6.11.0                       |
| **Utils**           | requests                         | 2.32.5                       |

---

## Request Flow

```
Client (Frontend/Browser)
    ↓
CORS Middleware (validates origin)
    ↓
Django URL Router
    ├─ /accounts/ → Allauth OAuth flow
    ├─ /whoami/ → whoami() view → Auth check
    ├─ /api/ping/ → ping() view
    └─ /admin/ → Django Admin
    ↓
API View/Handler
    ↓
Response (JSON or redirect)
    ↓
Client
```

---

## Environment Variables

| Variable        | Purpose                              | Default                                                 |
| --------------- | ------------------------------------ | ------------------------------------------------------- |
| `SECRET_KEY`    | Django secret (for CSRF, sessions)   | `"dev-only-change-me"` ⚠️                               |
| `DEBUG`         | Enable debug mode                    | `"false"`                                               |
| `ALLOWED_HOSTS` | Allowed domains                      | `"wifi-occupancy-prediction-production.up.railway.app"` |
| `DATABASE_URL`  | PostgreSQL connection string         | Uses SQLite if not set                                  |
| `FRONTEND_URL`  | Next.js frontend URL (for redirects) | Not shown in settings snippet                           |

---

## Development Workflow

### Local Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Running with Task

```bash
# From VS Code, run task "DJANGO: runserver"
# Backend runs on http://localhost:8000
```

### Database Migrations

```bash
python manage.py makemigrations    # Create migration files
python manage.py migrate            # Apply migrations
```

---

## Production Deployment

**WSGI Server:** Gunicorn (as specified in `Procfile`)

**Static Files:** WhiteNoise handles compression and serving

**Database:** PostgreSQL via Railway (or configured via `DATABASE_URL`)

**Security Notes:**

- ⚠️ Change `SECRET_KEY` in production
- ⚠️ Set `DEBUG = False` in production
- ⚠️ Update `ALLOWED_HOSTS` for your domain
- CORS headers should be configured for frontend domain

---

## Future Enhancements

Based on current setup, likely next endpoints:

1. **POST `/api/predict/`** - Submit occupancy sequence and get prediction
2. **GET `/api/predict/<id>/`** - Retrieve prediction history
3. **POST `/api/occupancy/`** - Log actual occupancy readings
4. **GET `/api/occupancy/<id>/`** - Retrieve occupancy records
5. **Admin panel** - Manage models, view metrics

---

## Key Architectural Decisions

| Decision                         | Rationale                                     |
| -------------------------------- | --------------------------------------------- |
| Django + DRF                     | Rapid development, built-in ORM, auth, admin  |
| SQLite (dev) / PostgreSQL (prod) | Flexibility for different environments        |
| Singleton ML Service             | Model stays in memory for fast predictions    |
| LSTM Sequence Length = 24        | Hourly predictions use 24-hour history        |
| Allauth + Google OAuth           | Reduces auth complexity, password-less option |
| WhiteNoise                       | Static file serving without separate CDN      |
