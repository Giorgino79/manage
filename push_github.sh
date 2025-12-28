#!/bin/bash

echo "=========================================="
echo "PUSH SU GITHUB - Management System"
echo "=========================================="
echo ""

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Repository URL
REPO_URL="https://github.com/Giorgino79/manage.git"

# 1. Verifica git
echo -e "${YELLOW}1. Verifica repository git...${NC}"
if [ ! -d .git ]; then
    echo -e "${RED}Errore: Non è un repository git!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Repository git trovato${NC}"
echo ""

# 2. Verifica remote
echo -e "${YELLOW}2. Configurazione remote GitHub...${NC}"
if git remote | grep -q origin; then
    echo -e "${GREEN}✓ Remote 'origin' già configurato${NC}"
    CURRENT_REMOTE=$(git remote get-url origin)
    echo "  URL attuale: $CURRENT_REMOTE"

    if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
        echo -e "${YELLOW}Aggiorno URL remote...${NC}"
        git remote set-url origin $REPO_URL
    fi
else
    echo "Aggiunta remote 'origin'..."
    git remote add origin $REPO_URL
    echo -e "${GREEN}✓ Remote aggiunto${NC}"
fi
echo ""

# 3. Verifica branch
echo -e "${YELLOW}3. Verifica branch...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
echo "Branch corrente: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Cambio branch a 'main'...${NC}"
    git branch -M main
fi
echo -e "${GREEN}✓ Branch: main${NC}"
echo ""

# 4. Mostra status
echo -e "${YELLOW}4. Status repository:${NC}"
git status --short
echo ""

# 5. Chiedi se ci sono file da committare
UNCOMMITTED=$(git status --porcelain | wc -l)
if [ $UNCOMMITTED -gt 0 ]; then
    echo -e "${YELLOW}Ci sono $UNCOMMITTED file non committati.${NC}"
    echo "Vuoi committar li tutti? (s/n)"
    read -p "> " COMMIT_ALL

    if [ "$COMMIT_ALL" = "s" ]; then
        git add .
        echo "Messaggio del commit:"
        read -p "> " COMMIT_MSG
        git commit -m "$COMMIT_MSG

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
        echo -e "${GREEN}✓ Commit creato${NC}"
    fi
    echo ""
fi

# 6. Push
echo -e "${YELLOW}5. Push su GitHub...${NC}"
echo "Repository: $REPO_URL"
echo "Branch: main"
echo ""
echo "NOTA: Ti verrà chiesto di autenticarti."
echo "Se usi HTTPS, inserisci:"
echo "  Username: Giorgino79"
echo "  Password: Il tuo Personal Access Token (non la password!)"
echo ""
echo "Per creare un token: https://github.com/settings/tokens"
echo ""
echo -e "${YELLOW}Procedere con il push? (s/n)${NC}"
read -p "> " DO_PUSH

if [ "$DO_PUSH" = "s" ]; then
    git push -u origin main

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}=========================================="
        echo "PUSH COMPLETATO!"
        echo "==========================================${NC}"
        echo ""
        echo "Repository: https://github.com/Giorgino79/manage"
        echo ""
    else
        echo ""
        echo -e "${RED}=========================================="
        echo "ERRORE DURANTE IL PUSH"
        echo "==========================================${NC}"
        echo ""
        echo "Se hai problemi di autenticazione:"
        echo "1. Genera un Personal Access Token su GitHub"
        echo "2. Usa SSH invece di HTTPS:"
        echo "   git remote set-url origin git@github.com:Giorgino79/manage.git"
        echo ""
    fi
else
    echo "Push annullato."
fi
