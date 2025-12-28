# Management System

Sistema di gestione aziendale completo sviluppato con Django 5.0.8.

## Funzionalità

### Moduli Implementati

1. **Preventivi**
   - Gestione richieste preventivo
   - Invio automatico ai fornitori via email
   - Sistema di valutazione con parametri personalizzabili
   - Ranking automatico dei preventivi
   - Workflow completo: Creazione → Invio → Raccolta → Valutazione → Approvazione

2. **Automezzi**
   - Gestione flotta veicoli
   - Tracciamento rifornimenti e consumi
   - Pianificazione e gestione manutenzioni
   - Storico eventi e documentazione
   - Report e statistiche

3. **Mail**
   - Integrazione IMAP/SMTP
   - Gestione inbox con fetch manuale
   - Invio email con template
   - Log e code di invio
   - Statistiche utilizzo

4. **Dipendenti**
   - Sistema di timbratura presenze
   - Gestione profili dipendenti
   - Report presenze
   - Giornate lavorative

5. **Altri Moduli**
   - Anagrafica (Clienti e Fornitori)
   - Acquisti
   - Fatturazione
   - Stabilimenti
   - Core utilities

## Tecnologie Utilizzate

- **Backend**: Django 5.0.8
- **Database**: PostgreSQL (production), SQLite (development)
- **Email**: IMAP/SMTP integration
- **UI**: Bootstrap 5, Font Awesome
- **PDF**: ReportLab
- **Excel**: Pandas, OpenPyXL, XlsxWriter
- **Task Queue**: Celery, Redis
- **Server**: Gunicorn, WhiteNoise

## Setup Locale

### Prerequisiti
- Python 3.12.2
- PostgreSQL (per produzione)

### Installazione

1. Clona il repository:
```bash
git clone https://github.com/Giorgino79/manage.git
cd manage
```

2. Crea virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows
```

3. Installa dipendenze:
```bash
pip install -r requirements.txt
```

4. Configura variabili d'ambiente (.env):
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

5. Esegui migrazioni:
```bash
python manage.py migrate
```

6. Crea superuser:
```bash
python manage.py createsuperuser
```

7. Avvia server:
```bash
python manage.py runserver
```

## Deploy su Heroku

### Setup Heroku

1. Installa Heroku CLI:
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

2. Login:
```bash
heroku login
```

3. Crea app:
```bash
heroku create nome-app
```

4. Aggiungi PostgreSQL:
```bash
heroku addons:create heroku-postgresql:essential-0
```

5. Configura variabili d'ambiente:
```bash
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
heroku config:set ALLOWED_HOSTS=.herokuapp.com
heroku config:set DJANGO_SETTINGS_MODULE=management.settings_heroku
```

6. Deploy:
```bash
git push heroku main
```

7. Esegui migrazioni:
```bash
heroku run python manage.py migrate --settings=management.settings_heroku
```

8. Crea superuser:
```bash
heroku run python manage.py createsuperuser --settings=management.settings_heroku
```

### Configurazione Email (Opzionale)

Per abilitare l'invio email:
```bash
heroku config:set EMAIL_HOST=smtp.gmail.com
heroku config:set EMAIL_PORT=587
heroku config:set EMAIL_USE_TLS=True
heroku config:set EMAIL_HOST_USER=your-email@gmail.com
heroku config:set EMAIL_HOST_PASSWORD=your-app-password
```

## Struttura Progetto

```
Management3/
├── acquisti/          # Gestione ordini acquisto
├── anagrafica/        # Clienti e fornitori
├── automezzi/         # Gestione flotta veicoli
├── core/              # Utilities core
├── dipendenti/        # Gestione dipendenti e presenze
├── fatturazione/      # Gestione fatture
├── mail/              # Sistema email
├── management/        # Settings Django
├── preventivi/        # Gestione preventivi
├── stabilimenti/      # Gestione stabilimenti
├── templates/         # Template globali
├── manage.py
├── requirements.txt
├── Procfile           # Heroku process file
└── runtime.txt        # Python version
```

## Crediti

Sistema sviluppato con l'assistenza di Claude Code (Anthropic).

## Licenza

Proprietario - Tutti i diritti riservati
