# Backend - Django + ML

## Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # (or venv\Scripts\activate on Windows)
pip install -r requirements-dev.txt
python manage.py migrate # (Make sure the DATABASE_URL is setup in the .env file before running this)
```

## Running the Django server
## After setup, start the server with:
```bash
python manage.py runserver
```

