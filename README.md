Repository for our thesis on WiFi-based occupancy prediction at Ateneo de Davao University, utilizing an attention-enhanced CNN-LSTM architecture.

## ⚙️ Local Environment Setup

### 1. Prerequisites
Ensure you have the following installed:
- **Docker** & **Docker Compose**
- **Node.js** (for optional local frontend development)
- **Python 3.11+** (for optional local backend development)
- **Postgresql 17+** (for optional local Database Connection)

---

### 2. Clone the repository
vsCode
git clone https://github.com/nzdable/wifi-occupancy-prediction.git

### 3. Setting up the .env files for the respective folders

Copy the environment files provided
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env

Frontend .env

NEXT_PUBLIC_GOOGLE_CLIENT_ID=Your_Google_Client_ID_Here

NEXT_PUBLIC_GOOGLE_CLIENT_SECRET=Your_Google_Client_Secret_Here

NEXT_PUBLIC_API_URL=http://localhost:8000

API_URL=http://127.0.0.1:8000
Backend .env

SECRET_KEY=Run this command in the VS Code terminal and paste the result
## python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

DEBUG=true (false for deployment)

ALLOWED_HOSTS=127.0.0.1,localhost

FRONTEND_URL=http://localhost:3000

GOOGLE_CLIENT_ID=Your_Google_Client_ID_Here

GOOGLE_CLIENT_SECRET=Your_Google_Client_Secret_Here

DATABASE_URL=postgresql://user:pass@host:5432/dbname

### 4. Run the docker environment
Run in the terminal

docker compose up --build
