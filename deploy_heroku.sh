#!/bin/bash

echo "=========================================="
echo "DEPLOY SU HEROKU - Management System"
echo "=========================================="
echo ""

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Controlla se Heroku CLI è installato
echo -e "${YELLOW}1. Controllo Heroku CLI...${NC}"
if ! command -v heroku &> /dev/null
then
    echo -e "${RED}Heroku CLI non trovato!${NC}"
    echo "Installa con: curl https://cli-assets.heroku.com/install.sh | sh"
    exit 1
fi
echo -e "${GREEN}✓ Heroku CLI trovato${NC}"
echo ""

# 2. Login Heroku
echo -e "${YELLOW}2. Login Heroku...${NC}"
heroku login
echo ""

# 3. Chiedi nome app
echo -e "${YELLOW}3. Nome dell'app Heroku:${NC}"
read -p "Inserisci il nome dell'app (es: management-system-2024): " APP_NAME

# 4. Crea o usa app esistente
echo -e "${YELLOW}4. Creazione/verifica app...${NC}"
if heroku apps:info -a $APP_NAME &> /dev/null; then
    echo -e "${GREEN}✓ App $APP_NAME già esistente${NC}"
else
    echo "Creazione nuova app..."
    heroku create $APP_NAME
fi
echo ""

# 5. Aggiungi PostgreSQL
echo -e "${YELLOW}5. Configurazione PostgreSQL...${NC}"
if heroku addons:info postgresql -a $APP_NAME &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL già configurato${NC}"
else
    echo "Aggiunta addon PostgreSQL..."
    heroku addons:create heroku-postgresql:essential-0 -a $APP_NAME
fi
echo ""

# 6. Configura variabili d'ambiente
echo -e "${YELLOW}6. Configurazione variabili d'ambiente...${NC}"

# Genera SECRET_KEY
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

heroku config:set -a $APP_NAME \
  DEBUG=False \
  SECRET_KEY="$SECRET_KEY" \
  ALLOWED_HOSTS=".herokuapp.com" \
  DJANGO_SETTINGS_MODULE=management.settings_heroku \
  HEROKU_APP_NAME=$APP_NAME

echo -e "${GREEN}✓ Variabili configurate${NC}"
echo ""

# 7. Aggiungi remote Heroku
echo -e "${YELLOW}7. Configurazione remote Heroku...${NC}"
if git remote | grep -q heroku; then
    git remote remove heroku
fi
heroku git:remote -a $APP_NAME
echo -e "${GREEN}✓ Remote aggiunto${NC}"
echo ""

# 8. Deploy
echo -e "${YELLOW}8. Deploy su Heroku...${NC}"
echo "Questo potrebbe richiedere alcuni minuti..."
git push heroku main
echo ""

# 9. Migrazioni
echo -e "${YELLOW}9. Esecuzione migrazioni database...${NC}"
heroku run python manage.py migrate --settings=management.settings_heroku -a $APP_NAME
echo ""

# 10. Creazione superuser
echo -e "${YELLOW}10. Vuoi creare un superuser? (s/n)${NC}"
read -p "> " CREATE_SUPERUSER
if [ "$CREATE_SUPERUSER" = "s" ]; then
    heroku run python manage.py createsuperuser --settings=management.settings_heroku -a $APP_NAME
fi
echo ""

# 11. Apri app
echo -e "${GREEN}=========================================="
echo "DEPLOY COMPLETATO!"
echo "==========================================${NC}"
echo ""
echo "URL app: https://$APP_NAME.herokuapp.com"
echo ""
echo "Comandi utili:"
echo "  - Vedere logs: heroku logs --tail -a $APP_NAME"
echo "  - Aprire app: heroku open -a $APP_NAME"
echo "  - Shell Django: heroku run python manage.py shell --settings=management.settings_heroku -a $APP_NAME"
echo "  - Bash: heroku run bash -a $APP_NAME"
echo ""
echo -e "${YELLOW}Vuoi aprire l'app nel browser? (s/n)${NC}"
read -p "> " OPEN_APP
if [ "$OPEN_APP" = "s" ]; then
    heroku open -a $APP_NAME
fi
