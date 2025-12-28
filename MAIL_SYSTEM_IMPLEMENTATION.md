# Sistema Email Gmail-Style - Implementazione Completa

**Data**: 28 Dicembre 2025
**Status**: Backend ✅ Completo | Frontend 🚧 Da Completare

---

## 📊 Riepilogo Lavoro Completato

### ✅ Backend Implementato (100%)

#### 1. Servizio IMAP per Ricezione Email
**File**: `/mail/services/imap_service.py` (450+ righe)

**Funzionalità**:
- Connessione IMAP con supporto SSL/TLS
- Fetch messaggi nuovi da cartelle remote
- Parsing email multipart (HTML + testo)
- Estrazione e salvataggio allegati
- Sincronizzazione automatica con database
- Context manager support (`with ImapEmailService(config) as service`)
- Gestione errori e logging completo

**Metodi principali**:
```python
service = ImapEmailService(email_config)
service.connect()  # Connette al server
folders = service.list_folders()  # Lista cartelle IMAP
messages = service.fetch_new_messages(folder='INBOX', limit=50)
saved = service.sync_messages_to_db(messages)  # Salva nel DB
service.disconnect()
```

---

#### 2. Modelli Database Aggiornati

**EmailConfiguration** - Campi IMAP aggiunti:
```python
imap_server = models.CharField(default="imap.gmail.com")
imap_port = models.IntegerField(default=993)
imap_username = models.CharField()
imap_password = models.CharField()
imap_use_tls = models.BooleanField(default=False)
imap_use_ssl = models.BooleanField(default=True)
imap_enabled = models.BooleanField(default=False)
last_imap_sync = models.DateTimeField(null=True)
last_imap_error = models.TextField(blank=True)
```

**EmailLabel** - Nuovo modello per etichette colorate:
```python
id = models.UUIDField(primary_key=True)
configuration = models.ForeignKey(EmailConfiguration)
name = models.CharField(max_length=100)
slug = models.SlugField()
color = models.CharField(max_length=7, default="#4285f4")  # hex color
icon = models.CharField(default="tag")  # Feather icon name
order = models.IntegerField(default=0)
is_visible = models.BooleanField(default=True)
is_system = models.BooleanField(default=False)
message_count = models.IntegerField(default=0)
```

**EmailMessage** - Relazione Many-to-Many con labels:
```python
labels = models.ManyToManyField('EmailLabel', blank=True, related_name='messages')
```

**Migrations**: Tutte create e applicate ✅

---

#### 3. Views Django (Backend API)

**File**: `/mail/views.py` (+350 righe nuove)

**Views implementate**:

1. **`inbox(request)`** - Vista principale inbox
   - Filtri: search, label, unread_only
   - Paginazione (50 messaggi/pagina)
   - Query ottimizzate con select_related/prefetch_related
   - Contatori cartelle e labels con annotate
   - Template: `mail/inbox.html`

2. **`folder_view(request, folder_type)`** - Cartelle generiche
   - folder_type: `sent`, `drafts`, `trash`, `spam`
   - Usa stesso template inbox.html
   - Filtri dinamici in base a folder_type

3. **`bulk_action(request)` [POST]** - Azioni bulk
   - Azioni: `mark_read`, `mark_unread`, `delete`, `move_to_folder`, `add_label`, `remove_label`, `star`, `unstar`
   - Input JSON: `{action: "mark_read", message_ids: [uuid1, uuid2, ...]}`
   - Output: `{success: true, action: "mark_read", count: 5}`

4. **`save_draft(request)` [POST]** - Autosave bozze
   - Input: `{draft_id: uuid?, to: [], cc: [], subject: "", content_html: "", content_text: ""}`
   - Output: `{success: true, draft_id: "uuid", saved_at: "2025-12-28T..."}`
   - Supporta sia creazione che update bozze esistenti

5. **`api_fetch_emails(request)`** - Fetch manuale IMAP
   - Triggera fetch immediato nuove email
   - Output: `{success: true, new_messages: 5, synced_at: "..."}`

---

#### 4. URLs Configurati

**File**: `/mail/urls.py`

```python
# Nuove routes
path('inbox/', views.inbox, name='inbox'),
path('folder/<str:folder_type>/', views.folder_view, name='folder_view'),

# API endpoints
path('api/bulk-action/', views.bulk_action, name='bulk_action'),
path('api/save-draft/', views.save_draft, name='save_draft'),
path('api/fetch-emails/', views.api_fetch_emails, name='api_fetch_emails'),
```

**URLs disponibili**:
- `/mail/inbox/` - Inbox principale
- `/mail/folder/sent/` - Inviati
- `/mail/folder/drafts/` - Bozze
- `/mail/folder/trash/` - Cestino
- `/mail/folder/spam/` - Spam

---

#### 5. Management Command

**File**: `/mail/management/commands/fetch_emails.py`

**Usage**:
```bash
# Fetch per singolo utente
python manage.py fetch_emails --user username

# Fetch per tutti gli utenti con IMAP abilitato
python manage.py fetch_emails --all

# Con opzioni
python manage.py fetch_emails --all --limit 100 --folder INBOX
```

**Opzioni**:
- `--user USERNAME` - Fetch per utente specifico
- `--all` - Fetch per tutti gli utenti
- `--limit N` - Max messaggi per cartella (default: 50)
- `--folder FOLDER` - Cartella da cui fetch (default: INBOX)

**Output**:
```
Processing: user@example.com
✓ Connected to imap.gmail.com
  Fetching from folder: INBOX
  Found 15 new messages
✓ Saved 15/15 messages

SUMMARY
Total messages fetched: 15
✓ All configurations processed successfully
```

**Schedulare con Cron**:
```bash
# Fetch ogni 5 minuti
*/5 * * * * cd /path/to/Management3 && python manage.py fetch_emails --all >> /var/log/fetch_emails.log 2>&1
```

---

#### 6. Sidebar Link

**File**: `/templates/components/sidebar.html`

```html
<li class="nav-item">
    <a class="nav-link {% if request.resolver_match.namespace == 'mail' %}active{% endif %}"
       href="{% url 'mail:inbox' %}">
        <i data-feather="mail" class="feather"></i>
        <span>Email Inbox</span>
        {% if unread_emails_count %}
        <span class="badge bg-danger rounded-pill ms-auto">{{ unread_emails_count }}</span>
        {% endif %}
    </a>
</li>
```

Link nella sidebar principale porta direttamente a `/mail/inbox/` ✅

---

## 🚧 Frontend Da Completare

### Template HTML Mancanti

#### 1. Template Inbox Principale

**File da creare**: `/mail/templates/mail/inbox.html`

**Struttura richiesta** (Layout a 3 colonne tipo Gmail):

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Inbox - Email{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'mail/css/inbox.css' %}">
{% endblock %}

{% block content %}
<div class="email-container">
    <!-- ========================================
         COLONNA 1: SIDEBAR SINISTRA (250px)
         ======================================== -->
    <aside class="email-sidebar">
        <!-- Pulsante Scrivi -->
        <button class="btn btn-primary btn-compose mb-3 w-100">
            <i data-feather="edit" class="me-2"></i>Scrivi
        </button>

        <!-- Cartelle Principali -->
        <nav class="email-folders">
            <a href="{% url 'mail:inbox' %}"
               class="folder-item {% if current_folder == 'inbox' %}active{% endif %}">
                <i data-feather="inbox"></i>
                <span>Posta in arrivo</span>
                {% if total_unread > 0 %}
                <span class="badge bg-primary">{{ total_unread }}</span>
                {% endif %}
            </a>

            <a href="{% url 'mail:folder_view' 'sent' %}"
               class="folder-item {% if current_folder == 'sent' %}active{% endif %}">
                <i data-feather="send"></i>
                <span>Inviati</span>
            </a>

            <a href="{% url 'mail:folder_view' 'drafts' %}"
               class="folder-item {% if current_folder == 'drafts' %}active{% endif %}">
                <i data-feather="file-text"></i>
                <span>Bozze</span>
            </a>

            <a href="{% url 'mail:folder_view' 'trash' %}"
               class="folder-item {% if current_folder == 'trash' %}active{% endif %}">
                <i data-feather="trash-2"></i>
                <span>Cestino</span>
            </a>

            <a href="{% url 'mail:folder_view' 'spam' %}"
               class="folder-item {% if current_folder == 'spam' %}active{% endif %}">
                <i data-feather="alert-triangle"></i>
                <span>Spam</span>
            </a>
        </nav>

        <!-- Etichette/Labels -->
        {% if labels %}
        <div class="email-labels mt-4">
            <h6 class="labels-header">Etichette</h6>
            {% for label in labels %}
            <a href="?label={{ label.slug }}" class="label-item">
                <i data-feather="{{ label.icon }}" style="color: {{ label.color }}"></i>
                <span>{{ label.name }}</span>
                {% if label.unread_count > 0 %}
                <span class="badge">{{ label.unread_count }}</span>
                {% endif %}
            </a>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Storage Usage (opzionale) -->
        <div class="storage-info mt-4">
            <small class="text-muted">Spazio utilizzato</small>
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" role="progressbar" style="width: 45%"></div>
            </div>
            <small class="text-muted">4.5 GB di 15 GB</small>
        </div>
    </aside>

    <!-- ========================================
         COLONNA 2: LISTA MESSAGGI (400px)
         ======================================== -->
    <main class="email-list">
        <!-- Header Lista -->
        <div class="email-list-header">
            <div class="email-list-toolbar">
                <!-- Checkbox Select All -->
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="selectAll">
                </div>

                <!-- Azioni Bulk (nascoste se nessuna selezione) -->
                <div class="bulk-actions" id="bulkActions" style="display: none;">
                    <button class="btn btn-sm btn-light" onclick="bulkAction('mark_read')" title="Segna come letto">
                        <i data-feather="mail-open"></i>
                    </button>
                    <button class="btn btn-sm btn-light" onclick="bulkAction('mark_unread')" title="Segna come non letto">
                        <i data-feather="mail"></i>
                    </button>
                    <button class="btn btn-sm btn-light" onclick="bulkAction('delete')" title="Elimina">
                        <i data-feather="trash-2"></i>
                    </button>
                    <button class="btn btn-sm btn-light" onclick="bulkAction('star')" title="Aggiungi stella">
                        <i data-feather="star"></i>
                    </button>
                </div>

                <!-- Pulsante Sync -->
                <button class="btn btn-sm btn-light ms-auto" onclick="fetchEmails()" title="Sincronizza">
                    <i data-feather="refresh-cw" id="syncIcon"></i>
                </button>

                <!-- Search -->
                <div class="search-box ms-2">
                    <input type="text" class="form-control form-control-sm"
                           placeholder="Cerca email..."
                           value="{{ search_query }}">
                </div>
            </div>
        </div>

        <!-- Lista Messaggi -->
        <div class="email-items">
            {% for message in messages %}
            <div class="email-item {% if not message.is_read %}unread{% endif %}"
                 data-message-id="{{ message.id }}"
                 onclick="selectMessage('{{ message.id }}')">

                <!-- Checkbox -->
                <div class="form-check">
                    <input class="form-check-input message-checkbox"
                           type="checkbox"
                           value="{{ message.id }}"
                           onclick="event.stopPropagation()">
                </div>

                <!-- Star -->
                <button class="btn-star {% if message.is_flagged %}starred{% endif %}"
                        onclick="event.stopPropagation(); toggleStar('{{ message.id }}')">
                    <i data-feather="star"></i>
                </button>

                <!-- Mittente/Destinatario -->
                <div class="email-sender">
                    {% if current_folder == 'sent' %}
                        A: {{ message.to_addresses.0 }}
                    {% else %}
                        {{ message.from_address|truncatechars:30 }}
                    {% endif %}
                </div>

                <!-- Oggetto + Anteprima -->
                <div class="email-subject-preview">
                    <strong>{{ message.subject|truncatechars:50 }}</strong>
                    <span class="text-muted">- {{ message.content_text|striptags|truncatechars:80 }}</span>
                </div>

                <!-- Labels -->
                {% if message.labels.all %}
                <div class="email-labels-preview">
                    {% for label in message.labels.all|slice:":3" %}
                    <span class="label-badge" style="background-color: {{ label.color }}20; color: {{ label.color }}">
                        {{ label.name }}
                    </span>
                    {% endfor %}
                </div>
                {% endif %}

                <!-- Allegati -->
                {% if message.has_attachments %}
                <i data-feather="paperclip" class="text-muted"></i>
                {% endif %}

                <!-- Data -->
                <div class="email-date">
                    {{ message.received_at|date:"d M" }}
                </div>
            </div>
            {% empty %}
            <div class="empty-state">
                <i data-feather="inbox" class="text-muted" style="width: 48px; height: 48px;"></i>
                <p class="text-muted mt-3">Nessun messaggio</p>
            </div>
            {% endfor %}
        </div>

        <!-- Paginazione -->
        {% if messages.has_other_pages %}
        <div class="email-list-footer">
            <nav>
                <ul class="pagination pagination-sm mb-0">
                    {% if messages.has_previous %}
                    <li class="page-item">
                        <a class="page-link" href="?page={{ messages.previous_page_number }}">Precedente</a>
                    </li>
                    {% endif %}

                    <li class="page-item disabled">
                        <span class="page-link">{{ messages.number }} di {{ messages.paginator.num_pages }}</span>
                    </li>

                    {% if messages.has_next %}
                    <li class="page-item">
                        <a class="page-link" href="?page={{ messages.next_page_number }}">Successiva</a>
                    </li>
                    {% endif %}
                </ul>
            </nav>
        </div>
        {% endif %}
    </main>

    <!-- ========================================
         COLONNA 3: ANTEPRIMA MESSAGGIO (flex)
         ======================================== -->
    <aside class="email-preview" id="emailPreview">
        <div class="preview-placeholder">
            <i data-feather="mail" style="width: 64px; height: 64px;" class="text-muted"></i>
            <p class="text-muted mt-3">Seleziona un messaggio per visualizzarlo</p>
        </div>

        <!-- Contenuto dinamico caricato via JavaScript -->
        <div id="previewContent" style="display: none;">
            <!-- Header messaggio -->
            <div class="preview-header">
                <h5 id="previewSubject"></h5>
                <div class="preview-actions">
                    <button class="btn btn-sm btn-light" onclick="replyMessage()" title="Rispondi">
                        <i data-feather="corner-up-left"></i>
                    </button>
                    <button class="btn btn-sm btn-light" onclick="forwardMessage()" title="Inoltra">
                        <i data-feather="corner-up-right"></i>
                    </button>
                    <button class="btn btn-sm btn-light" onclick="deleteMessage()" title="Elimina">
                        <i data-feather="trash-2"></i>
                    </button>
                </div>
            </div>

            <!-- Info mittente -->
            <div class="preview-from">
                <strong id="previewFrom"></strong>
                <small class="text-muted">a me</small>
                <small class="text-muted ms-auto" id="previewDate"></small>
            </div>

            <!-- Corpo email -->
            <div class="preview-body" id="previewBody">
                <!-- HTML email content -->
            </div>

            <!-- Allegati -->
            <div class="preview-attachments" id="previewAttachments" style="display: none;">
                <!-- Attachments list -->
            </div>
        </div>
    </aside>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'mail/js/inbox.js' %}"></script>
{% endblock %}
```

---

### CSS Necessario

**File da creare**: `/mail/static/mail/css/inbox.css`

```css
/* ===========================================
   LAYOUT A 3 COLONNE TIPO GMAIL
   =========================================== */

.email-container {
    display: flex;
    height: calc(100vh - 60px); /* Toglie header */
    background: #f5f5f5;
}

/* SIDEBAR SINISTRA */
.email-sidebar {
    width: 250px;
    background: #fff;
    border-right: 1px solid #e0e0e0;
    padding: 20px;
    overflow-y: auto;
}

.btn-compose {
    border-radius: 24px;
    font-weight: 500;
    padding: 12px 24px;
    box-shadow: 0 2px 8px rgba(66, 133, 244, 0.25);
}

.btn-compose:hover {
    box-shadow: 0 4px 12px rgba(66, 133, 244, 0.35);
}

.email-folders {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.folder-item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border-radius: 8px;
    color: #5f6368;
    text-decoration: none;
    transition: background 0.2s;
}

.folder-item:hover {
    background: #f1f3f4;
    color: #202124;
}

.folder-item.active {
    background: #e8f0fe;
    color: #1a73e8;
    font-weight: 500;
}

.folder-item i {
    width: 20px;
    height: 20px;
    margin-right: 12px;
}

.folder-item span:first-of-type {
    flex: 1;
}

.folder-item .badge {
    font-size: 0.75rem;
    padding: 2px 6px;
}

.email-labels {
    padding-top: 16px;
    border-top: 1px solid #e0e0e0;
}

.labels-header {
    font-size: 0.75rem;
    text-transform: uppercase;
    color: #5f6368;
    margin-bottom: 8px;
    font-weight: 600;
}

.label-item {
    display: flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 8px;
    color: #5f6368;
    text-decoration: none;
    font-size: 0.9rem;
    transition: background 0.2s;
}

.label-item:hover {
    background: #f1f3f4;
}

.label-item i {
    width: 16px;
    height: 16px;
    margin-right: 8px;
}

/* LISTA MESSAGGI (COLONNA CENTRALE) */
.email-list {
    width: 400px;
    background: #fff;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.email-list-header {
    border-bottom: 1px solid #e0e0e0;
    padding: 12px 16px;
    background: #fff;
    position: sticky;
    top: 0;
    z-index: 10;
}

.email-list-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
}

.bulk-actions {
    display: flex;
    gap: 4px;
}

.bulk-actions .btn {
    padding: 4px 8px;
}

.search-box input {
    border-radius: 8px;
    width: 200px;
}

/* EMAIL ITEMS */
.email-items {
    flex: 1;
    overflow-y: auto;
}

.email-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    gap: 12px;
    transition: background 0.2s;
}

.email-item:hover {
    background: #f5f5f5;
    box-shadow: inset 0 0 0 1px #e0e0e0;
}

.email-item.unread {
    background: #f8f9fa;
    font-weight: 600;
}

.email-item.selected {
    background: #e8f0fe;
}

.email-item .form-check {
    margin: 0;
}

.btn-star {
    background: none;
    border: none;
    color: #5f6368;
    padding: 0;
    width: 20px;
    height: 20px;
}

.btn-star.starred {
    color: #f9ab00;
}

.btn-star i {
    width: 18px;
    height: 18px;
}

.email-sender {
    min-width: 150px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.email-subject-preview {
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.email-subject-preview strong {
    color: #202124;
}

.email-labels-preview {
    display: flex;
    gap: 4px;
}

.label-badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 12px;
    white-space: nowrap;
}

.email-date {
    color: #5f6368;
    font-size: 0.85rem;
    min-width: 50px;
    text-align: right;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 300px;
}

/* ANTEPRIMA MESSAGGIO (COLONNA DESTRA) */
.email-preview {
    flex: 1;
    background: #fff;
    overflow-y: auto;
    padding: 24px;
}

.preview-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
}

.preview-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e0e0e0;
}

.preview-header h5 {
    margin: 0;
    font-size: 1.25rem;
}

.preview-actions {
    display: flex;
    gap: 8px;
}

.preview-from {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 24px;
    padding: 12px;
    background: #f8f9fa;
    border-radius: 8px;
}

.preview-body {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #202124;
}

.preview-body img {
    max-width: 100%;
    height: auto;
}

.preview-attachments {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid #e0e0e0;
}

/* RESPONSIVE */
@media (max-width: 1024px) {
    .email-preview {
        display: none;
    }
    .email-list {
        width: auto;
        flex: 1;
    }
}

@media (max-width: 768px) {
    .email-sidebar {
        position: fixed;
        left: -250px;
        height: 100%;
        z-index: 1000;
        transition: left 0.3s;
    }

    .email-sidebar.show {
        left: 0;
    }

    .email-list {
        width: 100%;
    }
}
```

---

### JavaScript Necessario

**File da creare**: `/mail/static/mail/js/inbox.js`

```javascript
// ===========================================
// INBOX JAVASCRIPT - Gmail-Style Interface
// ===========================================

let selectedMessages = new Set();
let currentMessageId = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeFeatherIcons();
    setupEventListeners();
});

function initializeFeatherIcons() {
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

function setupEventListeners() {
    // Select All checkbox
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.message-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = this.checked;
                const messageId = cb.value;
                if (this.checked) {
                    selectedMessages.add(messageId);
                } else {
                    selectedMessages.delete(messageId);
                }
            });
            updateBulkActionsVisibility();
        });
    }

    // Individual message checkboxes
    document.querySelectorAll('.message-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const messageId = this.value;
            if (this.checked) {
                selectedMessages.add(messageId);
            } else {
                selectedMessages.delete(messageId);
            }
            updateBulkActionsVisibility();
        });
    });
}

function updateBulkActionsVisibility() {
    const bulkActions = document.getElementById('bulkActions');
    if (bulkActions) {
        bulkActions.style.display = selectedMessages.size > 0 ? 'flex' : 'none';
    }
}

// ===========================================
// AZIONI BULK
// ===========================================

async function bulkAction(action) {
    if (selectedMessages.size === 0) {
        alert('Seleziona almeno un messaggio');
        return;
    }

    const messageIds = Array.from(selectedMessages);

    try {
        const response = await fetch('/mail/api/bulk-action/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                action: action,
                message_ids: messageIds
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(`Azione "${action}" applicata a ${data.count} messaggi`, 'success');

            // Ricarica pagina dopo 500ms
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            showNotification('Errore: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Errore di connessione', 'error');
    }
}

// ===========================================
// ANTEPRIMA MESSAGGIO
// ===========================================

async function selectMessage(messageId) {
    currentMessageId = messageId;

    // Segna come selezionato
    document.querySelectorAll('.email-item').forEach(item => {
        item.classList.remove('selected');
    });
    const selectedItem = document.querySelector(`[data-message-id="${messageId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
        selectedItem.classList.remove('unread');
    }

    // Carica anteprima
    try {
        const response = await fetch(`/mail/messages/${messageId}/`);
        const html = await response.text();

        // Parse HTML per estrarre dati
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Mostra anteprima
        document.querySelector('.preview-placeholder').style.display = 'none';
        document.getElementById('previewContent').style.display = 'block';

        // Aggiorna contenuto (esempio semplificato)
        // In produzione, meglio usare una API che restituisce JSON

        // Segna come letto automaticamente
        markAsRead(messageId);

    } catch (error) {
        console.error('Error loading message:', error);
    }
}

async function markAsRead(messageId) {
    try {
        await fetch(`/mail/messages/${messageId}/mark-read/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
    } catch (error) {
        console.error('Error marking as read:', error);
    }
}

async function toggleStar(messageId) {
    try {
        const response = await fetch(`/mail/messages/${messageId}/toggle-star/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (data.success) {
            // Aggiorna UI
            const starBtn = event.currentTarget;
            if (data.is_starred) {
                starBtn.classList.add('starred');
            } else {
                starBtn.classList.remove('starred');
            }
            feather.replace();
        }
    } catch (error) {
        console.error('Error toggling star:', error);
    }
}

// ===========================================
// FETCH EMAIL (SYNC)
// ===========================================

async function fetchEmails() {
    const syncIcon = document.getElementById('syncIcon');
    syncIcon.classList.add('rotating');

    try {
        const response = await fetch('/mail/api/fetch-emails/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (data.success) {
            if (data.new_messages > 0) {
                showNotification(`${data.new_messages} nuovi messaggi ricevuti`, 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showNotification('Nessun nuovo messaggio', 'info');
            }
        } else {
            showNotification('Errore: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Errore di connessione', 'error');
    } finally {
        syncIcon.classList.remove('rotating');
    }
}

// ===========================================
// UTILITIES
// ===========================================

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showNotification(message, type = 'info') {
    // Usa Bootstrap toast o alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// CSS per icona rotante
const style = document.createElement('style');
style.textContent = `
    .rotating {
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
```

---

## 🎯 Prossimi Passi per Completare

### 1. Creare i file frontend
```bash
# Template
touch /mail/templates/mail/inbox.html

# CSS
mkdir -p /mail/static/mail/css
touch /mail/static/mail/css/inbox.css

# JavaScript
mkdir -p /mail/static/mail/js
touch /mail/static/mail/js/inbox.js
```

### 2. Copiare codice dai blocchi sopra nei rispettivi file

### 3. Testare l'interfaccia
```bash
# Avvia server
python manage.py runserver 0.0.0.0:8000

# Visita
http://127.0.0.1:8000/mail/inbox/
```

### 4. Configurare IMAP per test
- Andare su `/mail/config/`
- Inserire credenziali IMAP (Gmail, Outlook, etc.)
- Per Gmail: usare "App Password" non password normale

### 5. Fetch email
```bash
# Manuale
python manage.py fetch_emails --user username

# O click su pulsante Sync nell'interfaccia
```

---

## ✅ Checklist Finale

- [x] Servizio IMAP implementato
- [x] Modelli database aggiornati
- [x] Views backend create
- [x] URLs configurati
- [x] Management command creato
- [x] Link sidebar aggiunto
- [ ] Template inbox.html creato
- [ ] CSS inbox.css creato
- [ ] JavaScript inbox.js creato
- [ ] Test interfaccia completo

---

## 📚 Documentazione Tecnica

### Stack Tecnologico
- **Backend**: Django 5.0.8
- **Email**: IMAP (imaplib), SMTP (smtplib)
- **Frontend**: Bootstrap 5, Feather Icons
- **Database**: SQLite/PostgreSQL

### Configurazioni Consigliate

**Gmail**:
```
IMAP Server: imap.gmail.com
IMAP Port: 993
IMAP SSL: True
SMTP Server: smtp.gmail.com
SMTP Port: 587
SMTP TLS: True
```

**Outlook**:
```
IMAP Server: outlook.office365.com
IMAP Port: 993
IMAP SSL: True
SMTP Server: smtp.office365.com
SMTP Port: 587
SMTP TLS: True
```

### Performance Tips
- Usare `select_related()` e `prefetch_related()` per ottimizzare query
- Implementare caching per contatori cartelle
- Limitare fetch a 50 messaggi per volta
- Usare pagination per lista messaggi
- Considerare Celery per fetch asincrono in produzione

---

**Fine Documento** 🎉
