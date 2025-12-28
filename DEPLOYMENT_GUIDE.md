# Guida al Deployment

## 1. Push su GitHub

### Opzione A: Usando lo script automatico (RACCOMANDATO)

```bash
./push_github.sh
```

Lo script ti guiderà attraverso tutti i passaggi.

### Opzione B: Manualmente

1. **Autenticazione GitHub**

   Se usi HTTPS, avrai bisogno di un Personal Access Token:
   - Vai su https://github.com/settings/tokens
   - Click su "Generate new token (classic)"
   - Seleziona scope: `repo` (full control of private repositories)
   - Copia il token generato

2. **Push manuale**

   ```bash
   git push -u origin main
   ```

   Quando richiesto:
   - Username: `Giorgino79`
   - Password: Il tuo Personal Access Token (NON la password di GitHub!)

### Opzione C: Usando SSH (alternativa senza token)

1. **Genera chiave SSH** (se non l'hai già):
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Aggiungi la chiave a GitHub**:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   Copia l'output e aggiungilo su https://github.com/settings/keys

3. **Cambia remote in SSH**:
   ```bash
   git remote set-url origin git@github.com:Giorgino79/manage.git
   ```

4. **Push**:
   ```bash
   git push -u origin main
   ```

---

## 2. Deploy su Heroku

### Opzione A: Usando lo script automatico (RACCOMANDATO)

```bash
./deploy_heroku.sh
```

Lo script farà tutto automaticamente:
- Verifica Heroku CLI
- Login
- Creazione app
- Configurazione PostgreSQL
- Setup variabili d'ambiente
- Deploy
- Migrazioni database
- Creazione superuser

### Opzione B: Manualmente

#### Prerequisiti

1. **Installa Heroku CLI**:
   ```bash
   curl https://cli-assets.heroku.com/install.sh | sh
   ```

2. **Login**:
   ```bash
   heroku login
   ```

#### Passi per il Deploy

1. **Crea app Heroku**:
   ```bash
   heroku create nome-tua-app
   ```

2. **Aggiungi PostgreSQL**:
   ```bash
   heroku addons:create heroku-postgresql:essential-0 -a nome-tua-app
   ```

3. **Configura variabili d'ambiente**:
   ```bash
   # Genera SECRET_KEY
   SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

   # Imposta variabili
   heroku config:set -a nome-tua-app \
     DEBUG=False \
     SECRET_KEY="$SECRET_KEY" \
     ALLOWED_HOSTS=".herokuapp.com" \
     DJANGO_SETTINGS_MODULE=management.settings_heroku \
     HEROKU_APP_NAME=nome-tua-app
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

5. **Migrazioni**:
   ```bash
   heroku run python manage.py migrate --settings=management.settings_heroku -a nome-tua-app
   ```

6. **Crea superuser**:
   ```bash
   heroku run python manage.py createsuperuser --settings=management.settings_heroku -a nome-tua-app
   ```

7. **Apri app**:
   ```bash
   heroku open -a nome-tua-app
   ```

---

## 3. Configurazione Email (Opzionale)

Per abilitare l'invio di email tramite Gmail:

1. **Abilita "App Password" su Gmail**:
   - Vai su https://myaccount.google.com/security
   - Abilita verifica in due passaggi
   - Genera "App Password"

2. **Configura su Heroku**:
   ```bash
   heroku config:set -a nome-tua-app \
     EMAIL_HOST=smtp.gmail.com \
     EMAIL_PORT=587 \
     EMAIL_USE_TLS=True \
     EMAIL_HOST_USER=tua-email@gmail.com \
     EMAIL_HOST_PASSWORD=tua-app-password
   ```

---

## 4. Comandi Utili Heroku

### Visualizzare i logs
```bash
heroku logs --tail -a nome-tua-app
```

### Eseguire comandi Django
```bash
# Shell Django
heroku run python manage.py shell --settings=management.settings_heroku -a nome-tua-app

# Creare dati di test
heroku run python manage.py loaddata fixture.json --settings=management.settings_heroku -a nome-tua-app

# Raccogliere file statici
heroku run python manage.py collectstatic --noinput --settings=management.settings_heroku -a nome-tua-app
```

### Accedere al database
```bash
heroku pg:psql -a nome-tua-app
```

### Restart app
```bash
heroku restart -a nome-tua-app
```

### Scalare dynos
```bash
# Vedere dynos attuali
heroku ps -a nome-tua-app

# Scalare
heroku ps:scale web=1 -a nome-tua-app
```

---

## 5. Troubleshooting

### App non si avvia
1. Controlla i logs: `heroku logs --tail -a nome-tua-app`
2. Verifica Procfile: deve puntare a `management.wsgi`
3. Verifica settings: `DJANGO_SETTINGS_MODULE=management.settings_heroku`

### Errori di database
1. Verifica che PostgreSQL sia attivo: `heroku addons -a nome-tua-app`
2. Controlla DATABASE_URL: `heroku config:get DATABASE_URL -a nome-tua-app`
3. Rilancia migrazioni

### File statici non caricano
1. Verifica WhiteNoise in MIDDLEWARE (settings_heroku.py)
2. Raccogli statici: `heroku run python manage.py collectstatic --noinput --settings=management.settings_heroku`
3. Controlla che STATIC_ROOT sia configurato

### Errori 500
1. Abilita temporaneamente DEBUG:
   ```bash
   heroku config:set DEBUG=True -a nome-tua-app
   ```
2. Controlla logs dettagliati
3. **IMPORTANTE**: Disabilita DEBUG dopo il fix!
   ```bash
   heroku config:set DEBUG=False -a nome-tua-app
   ```

---

## 6. Workflow Consigliato

### Sviluppo Locale
```bash
# Crea branch feature
git checkout -b feature/nome-feature

# Lavora...
git add .
git commit -m "Descrizione modifiche"

# Testa localmente
python manage.py runserver

# Merge su main
git checkout main
git merge feature/nome-feature
```

### Deploy in Produzione
```bash
# Push su GitHub
./push_github.sh
# oppure
git push origin main

# Deploy su Heroku
git push heroku main

# Verifica
heroku logs --tail -a nome-tua-app
heroku open -a nome-tua-app
```

---

## 7. Best Practices

1. **Mai committare**:
   - `.env` files
   - `db.sqlite3`
   - Secret keys
   - Credentials

2. **Prima di ogni deploy**:
   - Testa in locale
   - Controlla migrazioni: `python manage.py makemigrations --check`
   - Verifica requirements.txt aggiornato

3. **Backup Database**:
   ```bash
   heroku pg:backups:capture -a nome-tua-app
   heroku pg:backups:download -a nome-tua-app
   ```

4. **Monitoraggio**:
   - Controlla logs regolarmente
   - Imposta alerting per errori critici
   - Monitora uso risorse su Heroku dashboard

---

## Supporto

Per problemi o domande:
- Documentazione Heroku: https://devcenter.heroku.com/
- Documentazione Django: https://docs.djangoproject.com/
- GitHub Issues: https://github.com/Giorgino79/manage/issues
