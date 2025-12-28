# 🚀 BEF MANAGEMENT SYSTEM - TODO & ARCHITETTURA MODULARE

## 📋 PRINCIPI ARCHITETTURALI

### 🎯 OBIETTIVO PRINCIPALE
Creare un sistema ERP modulare composto da:
- **CORNICE** (Management): Sistema base con auth, utilities, eventi
- **MODULI** indipendenti: Apps business logic completamente standalone

### 🏗️ STRUTTURA MODULARE TARGET
```
bef-core/           # CORNICE BASE
├── dipendenti/     # 👥 Gestione utenti e autenticazione
├── core/           # 🛠️ Utilities, PDF, email, eventi, interfacce
└── base/           # 📋 Modelli base, abstract models

bef-anagrafica/     # 📊 MODULO CLIENTI/FORNITORI
bef-inventory/      # 📦 MODULO MAGAZZINO (prodotti + scorte + stabilimenti)
bef-purchasing/     # 🛒 MODULO ACQUISTI
bef-sales/          # 💰 MODULO VENDITE + FATTURAZIONE
bef-logistics/      # 🚛 MODULO LOGISTICA (ricezioni + distribuzione + automezzi)
bef-finance/        # 💳 MODULO CONTABILITÀ
```

---

## 🎨 REGOLE CSS OBBLIGATORIE

### ⚠️ REGOLA ASSOLUTA: SOLO STYLE.CSS
- **DIVIETO ASSOLUTO** di CSS inline (`style=""`) nei template
- **DIVIETO ASSOLUTO** di tag `<style>` nei template
- **TUTTO** deve essere definito in `/static/css/style.css`

### 📝 LINEE GUIDA CSS
1. **RIUTILIZZABILITÀ**: Ogni classe CSS deve essere riutilizzabile in contesti diversi
2. **NAMING CONVENTION**: Usa nomi semantici, non specifici dell'app
   ```css
   /* ✅ CORRETTO */
   .dashboard-card { ... }
   .form-section { ... }
   .table-actions { ... }
   
   /* ❌ SBAGLIATO */
   .vendite-ordine-card { ... }
   .dipendenti-form-speciale { ... }
   ```

3. **ORGANIZZAZIONE**: Mantieni la struttura esistente nel CSS:
   - Reset & Base
   - Layout
   - Typography  
   - Forms
   - Buttons
   - Tables
   - Cards
   - Navigation
   - Modals
   - Utilities
   - App-specific (solo se necessario)

4. **RESPONSIVE FIRST**: Tutte le nuove regole devono essere mobile-first
5. **ACCESSIBILITÀ**: Focus states e screen reader support obbligatori

### 🔧 PROCESSO AGGIUNTA CSS
1. Identifica la categoria nella struttura esistente
2. Crea classe riutilizzabile con nome semantico
3. Aggiungi al file `/static/css/style.css` nella sezione appropriata
4. Documenta con commento se necessario
5. Testa responsive e accessibilità

---

## 📚 LIBRERIE & DIPENDENZE OBBLIGATORIE

### 🎯 CORNICE BASE (Management)
```txt
# CORE DJANGO
Django==5.2.6
python-dotenv==1.1.0
django-environ==0.11.2

# FORMS & UI  
django-crispy-forms==2.3
crispy-bootstrap5==2024.2
django-bootstrap5==24.2
django-widget-tweaks==1.5.0

# API & REST
djangorestframework==3.15.2
django-cors-headers==4.7.0

# UTILITIES
django-extensions==3.2.3
django-mathfilters==1.0.0
python-dateutil==2.8.2
pytz==2024.1
humanize==4.12.3

# DEBUGGING (solo dev)
django-debug-toolbar==4.4.6

# FRONTEND ASSETS
fontawesomefree==6.6.0
```

### 🗄️ DATABASE & PRODUZIONE
```txt
# DATABASE
psycopg2-binary==2.9.10  # PostgreSQL
dj-database-url==2.3.0

# PRODUZIONE
gunicorn==23.0.0
whitenoise==6.9.0

# STORAGE & FILES
pillow==10.4.0
django-storages==1.14.4
```

### ⚡ FUNZIONALITÀ AVANZATE (Opzionali per moduli)
```txt
# FILTERING & SEARCH
django-filter==24.2
django-select2==8.4.0

# PDF GENERATION
xhtml2pdf==0.2.17
reportlab==4.4.0

# HISTORY & AUDIT
django-simple-history==3.8.0

# ASYNC & TASKS
celery==5.3.4
redis==5.0.8
channels==4.1.0

# TIMEZONE
django-timezone-field==7.1

# HTTP REQUESTS
requests==2.32.3
```

---

## 🔧 SETUP NUOVO PROGETTO MODULARE

### 1️⃣ CORNICE BASE
```bash
# Crea progetto Django
django-admin startproject management

# Installa dipendenze core
pip install Django python-dotenv django-crispy-forms crispy-bootstrap5

# Crea apps cornice
python manage.py startapp dipendenti
python manage.py startapp core
```

### 2️⃣ CONFIGURAZIONE INIZIALE
```python
# settings.py - CONFIGURAZIONE MINIMA
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    
    # Cornice
    'dipendenti',
    'core',
]

# CSS Framework
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Static files
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
```

### 3️⃣ SISTEMA EVENTI (core/events.py)
```python
class EventRegistry:
    _handlers = {}
    
    @classmethod
    def register(cls, event_type, handler):
        cls._handlers.setdefault(event_type, []).append(handler)
    
    @classmethod
    def emit(cls, event_type, data):
        for handler in cls._handlers.get(event_type, []):
            handler(data)
```

---

## 📋 TODO IMPLEMENTAZIONE

### ✅ COMPLETATO
- [x] Progetto Management creato
- [x] CSS unificato estratto e organizzato
- [x] Analisi dipendenze BEF2 esistente
- [x] Documentazione architettura modulare

### 🔄 IN CORSO
- [ ] Setup cornice base (dipendenti + core)
- [ ] Sistema eventi per comunicazione inter-moduli
- [ ] Template base unificati
- [ ] Interfacce standard per moduli

### 📅 DA FARE
- [ ] **FASE 1: CORNICE**
  - [ ] App `dipendenti` - User model + auth
  - [ ] App `core` - Events + utilities + PDF
  - [ ] Template base con CSS unificato
  - [ ] Sistema registry per moduli

- [ ] **FASE 2: PRIMO MODULO**
  - [ ] Estrazione app `anagrafica` da BEF2
  - [ ] Refactoring per indipendenza
  - [ ] Event handlers per comunicazione
  - [ ] Test integrazione con cornice

- [ ] **FASE 3: MODULI BUSINESS**
  - [ ] `bef-inventory` (prodotti + scorte + stabilimenti)
  - [ ] `bef-purchasing` (acquisti)
  - [ ] `bef-sales` (vendite + fatturazione)
  - [ ] `bef-logistics` (logistica completa)

- [ ] **FASE 4: MIGRAZIONE**
  - [ ] Script migrazione dati da BEF2
  - [ ] Test performance sistema modulare
  - [ ] Documentazione deployment
  - [ ] Training team sviluppo

---

## 🚨 PRIORITÀ CRITICHE

### 1. **CSS DISCIPLINE** 📊
- Rispettare rigorosamente le regole CSS
- Nessuna eccezione per "velocità" o "urgenza"
- Code review obbligatorio per modifiche CSS

### 2. **MODULARITÀ** 🧩
- Ogni modulo deve funzionare standalone
- Zero import diretti tra moduli business
- Solo comunicazione via eventi

### 3. **TESTING** 🧪
- Test integrazione tra moduli
- Test performance con moduli disattivati
- Test deployment modulare

### 4. **DOCUMENTAZIONE** 📝
- Interfacce pubbliche di ogni modulo
- Event types e payload
- Guide setup per nuovi moduli

---

## 📞 SUPPORTO & RISORSE

### 🔗 Bootstrap 5.3.0
- [Documentazione ufficiale](https://getbootstrap.com/docs/5.3/)
- CSS già incluso nel file unificato

### 🎨 FontAwesome 6.6.0
- [Icons reference](https://fontawesome.com/icons)
- Libreria già inclusa

### 📚 Django Best Practices
- [Django Documentation](https://docs.djangoproject.com/)
- [REST Framework](https://www.django-rest-framework.org/)

---

**Ultimo aggiornamento**: $(date +"%Y-%m-%d %H:%M")  
**Versione architettura**: 1.0  
**Responsabile**: Team Development BEF