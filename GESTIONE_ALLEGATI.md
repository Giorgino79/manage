# GESTIONE ALLEGATI - Sistema Universale
## 📎 Documentazione Completa per Sviluppatori

### **PANORAMICA SISTEMA**

Il sistema allegati del Management è progettato per essere **universale, modulare e riutilizzabile**. Permette di collegare allegati (file, note, email, media) a qualsiasi oggetto del sistema usando Django GenericForeignKey.

### **ARCHITETTURA**

```
core/
├── models/
│   └── allegati.py          # Modello Allegato universale
├── views/
│   └── allegati.py          # Views CRUD allegati
├── forms/
│   └── allegati.py          # Form per allegati
├── templates/
│   ├── allegati/
│   │   ├── allegato_list_widget.html      # Widget lista allegati
│   │   ├── allegato_modal_form.html       # Modal create/edit
│   │   ├── allegato_modal_detail.html     # Modal visualizzazione
│   │   ├── allegato_modal_delete.html     # Modal conferma elimina
│   │   └── allegato_item_card.html        # Card singolo allegato
│   └── includes/
│       └── allegati_scripts.js.html       # JavaScript allegati
├── templatetags/
│   └── allegati_tags.py     # Template tags riutilizzabili
├── mixins/
│   └── allegati.py          # AllegatiMixin per modelli
└── api/
    └── allegati.py          # API REST allegati
```

---

## **1. INTEGRAZIONE NEI MODELLI**

### **1.1 Mixin AllegatiMixin**
Ogni modello che deve avere allegati eredita da `AllegatiMixin`:

```python
# Esempio: dipendenti/models.py
class Dipendente(AbstractUser, AllegatiMixin):
    # ... campi del modello
    pass

# Esempio: automezzi/models.py  
class Automezzo(models.Model, AllegatiMixin):
    # ... campi del modello
    pass
```

### **1.2 Metodi Disponibili**
```python
obj = Dipendente.objects.get(pk=1)

# Ottenere allegati
allegati = obj.get_allegati()                    # QuerySet allegati
count = obj.allegati_count                       # Numero allegati
ha_allegati = obj.ha_allegati                    # Boolean

# Filtrare allegati
documenti = obj.get_allegati_by_type('doc_*')    # Documenti
foto = obj.get_allegati_by_type('foto')          # Foto
email = obj.get_allegati_by_type('email_*')     # Email

# Aggiungere allegato
obj.add_allegato(
    titolo="Contratto",
    tipo_allegato="doc_contratto",
    file=file_obj,
    creato_da=user
)
```

---

## **2. TEMPLATE INTEGRATION**

### **2.1 Widget Principale nei Detail Template**
In ogni template `*_detail.html` inserire:

```html
<!-- Esempio: dipendenti/dipendente_detail.html -->
{% extends 'base.html' %}
{% load allegati_tags %}

{% block content %}
<div class="container-fluid">
    <!-- Dati principali oggetto -->
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>👤 {{ dipendente.get_full_name }}</h5>
                </div>
                <div class="card-body">
                    <!-- Dati del dipendente -->
                    <p><strong>Email:</strong> {{ dipendente.email }}</p>
                    <p><strong>Telefono:</strong> {{ dipendente.telefono }}</p>
                    <!-- ... altri dati ... -->
                </div>
            </div>
        </div>
        
        <!-- SIDEBAR ALLEGATI -->
        <div class="col-md-4">
            {% allegati_widget dipendente %}
        </div>
    </div>
    
    <!-- SEZIONE ALLEGATI COMPLETA (opzionale) -->
    <div class="row mt-4">
        <div class="col-12">
            {% allegati_section dipendente show_grid=True %}
        </div>
    </div>
</div>

<!-- Include JavaScript allegati -->
{% include 'core/includes/allegati_scripts.js.html' %}
{% endblock %}
```

### **2.2 Template Tags Disponibili**

#### **Widget Compatto (Sidebar)**
```html
{% allegati_widget oggetto %}
{% allegati_widget oggetto can_add=True can_edit=False %}
{% allegati_widget oggetto types_filter="doc_,foto" %}
```

#### **Sezione Completa**
```html
{% allegati_section oggetto %}
{% allegati_section oggetto show_grid=True %}
{% allegati_section oggetto columns=3 %}
```

#### **Lista Semplice**
```html
{% allegati_list oggetto %}
{% allegati_list oggetto limit=5 %}
```

#### **Contatori**
```html
{% allegati_count oggetto %}
{% allegati_badge oggetto %}  <!-- Badge con numero -->
```

---

## **3. TIPI DI ALLEGATO**

### **3.1 Categorie Principali**

```python
TIPO_ALLEGATO_CHOICES = [
    # DOCUMENTI UFFICIALI
    ('doc_contratto', '📄 Contratto'),
    ('doc_fattura', '🧾 Fattura'), 
    ('doc_preventivo', '💰 Preventivo'),
    ('doc_ordine', '📋 Ordine'),
    ('doc_bolla', '📦 Bolla Consegna'),
    ('doc_certificato', '🏆 Certificato'),
    ('doc_libretto', '📓 Libretto'),
    ('doc_patente', '🪪 Patente'),
    ('doc_carta_identita', '🆔 Carta Identità'),
    ('doc_codice_fiscale', '📊 Codice Fiscale'),
    
    # COMUNICAZIONI
    ('email_inviata', '📧 Email Inviata'),
    ('email_ricevuta', '📨 Email Ricevuta'),
    ('sms_inviato', '💬 SMS Inviato'),
    ('chiamata', '☎️ Chiamata'),
    ('fax', '📠 Fax'),
    
    # MEDIA
    ('foto_documento', '📷 Foto Documento'),
    ('foto_generale', '🖼️ Fotografia'),
    ('video', '🎥 Video'),
    ('audio', '🎵 Audio'),
    ('screenshot', '🖥️ Screenshot'),
    
    # NOTE E PROMEMORIA
    ('nota_interna', '📝 Nota Interna'),
    ('nota_cliente', '💭 Nota Cliente'),
    ('promemoria', '⏰ Promemoria'),
    ('appunto', '✏️ Appunto'),
    
    # TECNICI E MANUTENZIONE
    ('scheda_tecnica', '⚙️ Scheda Tecnica'),
    ('manuale', '📖 Manuale'),
    ('report_tecnico', '🔧 Report Tecnico'),
    ('log_manutenzione', '🛠️ Log Manutenzione'),
    
    # COMMERCIALI
    ('listino', '💲 Listino Prezzi'),
    ('catalogo', '📚 Catalogo'),
    ('brochure', '📰 Brochure'),
    
    # LEGALI E ASSICURATIVI
    ('polizza', '🛡️ Polizza'),
    ('denuncia', '⚠️ Denuncia'),
    ('verbale', '📄 Verbale'),
    ('sentenza', '⚖️ Sentenza'),
    
    # ALTRO
    ('link_esterno', '🔗 Link Esterno'),
    ('backup', '💾 Backup'),
    ('altro', '📎 Altro'),
]
```

### **3.2 Filtri Intelligenti per Oggetto**

```python
# core/utils/allegati_filter.py
FILTRI_PER_MODELLO = {
    'dipendenti.dipendente': [
        'doc_contratto', 'doc_certificato', 'doc_patente', 
        'doc_carta_identita', 'doc_codice_fiscale',
        'foto_documento', 'nota_interna', 'email_*'
    ],
    
    'automezzi.automezzo': [
        'doc_libretto', 'doc_certificato', 'polizza',
        'foto_generale', 'scheda_tecnica', 'manuale',
        'log_manutenzione', 'report_tecnico'
    ],
    
    'vendite.ordinevendita': [
        'doc_ordine', 'doc_fattura', 'doc_bolla',
        'doc_preventivo', 'email_*', 'nota_cliente'
    ],
    
    'clienti.cliente': [
        'doc_contratto', 'email_*', 'chiamata',
        'nota_cliente', 'brochure', 'listino'
    ]
}
```

---

## **4. MODAL CRUD SYSTEM**

### **4.1 Modal Structure**

Tutti i CRUD (Create, Update, Delete) vengono gestiti tramite modal Bootstrap:

```html
<!-- Modal Add/Edit Allegato -->
<div class="modal fade" id="allegatoModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="fas fa-plus"></i> 
                    <span id="modal-title">Aggiungi Allegato</span>
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            
            <div class="modal-body">
                <!-- Form caricato via AJAX -->
                <div id="allegato-form-container">
                    <!-- Spinner loading -->
                </div>
            </div>
            
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    Annulla
                </button>
                <button type="button" class="btn btn-primary" id="save-allegato">
                    <i class="fas fa-save"></i> Salva
                </button>
            </div>
        </div>
    </div>
</div>
```

### **4.2 JavaScript Functions**

```javascript
// core/static/core/js/allegati.js
class AllegatiManager {
    constructor(objectId, contentTypeId) {
        this.objectId = objectId;
        this.contentTypeId = contentTypeId;
        this.baseUrl = `/core/allegati/`;
    }
    
    // Apri modal aggiungi
    openAddModal() {
        const url = `${this.baseUrl}add/?ct=${this.contentTypeId}&oid=${this.objectId}`;
        this.loadModal(url, 'Aggiungi Allegato');
    }
    
    // Apri modal modifica
    openEditModal(allegatoId) {
        const url = `${this.baseUrl}${allegatoId}/edit/`;
        this.loadModal(url, 'Modifica Allegato');
    }
    
    // Apri modal visualizzazione
    openDetailModal(allegatoId) {
        const url = `${this.baseUrl}${allegatoId}/detail/`;
        this.loadModal(url, 'Dettaglio Allegato');
    }
    
    // Elimina allegato
    deleteAllegato(allegatoId) {
        if (confirm('Sei sicuro di voler eliminare questo allegato?')) {
            fetch(`${this.baseUrl}${allegatoId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.refreshAllegatiList();
                    showToast('Allegato eliminato con successo', 'success');
                }
            });
        }
    }
}
```

---

## **5. URL PATTERNS**

```python
# core/urls.py - Sezione Allegati
urlpatterns = [
    # ... altri URL core
    
    # ALLEGATI CRUD
    path('allegati/add/', views.AllegatoCreateView.as_view(), name='allegato_create'),
    path('allegati/<int:pk>/edit/', views.AllegatoUpdateView.as_view(), name='allegato_update'), 
    path('allegati/<int:pk>/detail/', views.AllegatoDetailView.as_view(), name='allegato_detail'),
    path('allegati/<int:pk>/delete/', views.AllegatoDeleteView.as_view(), name='allegato_delete'),
    
    # ALLEGATI API
    path('api/allegati/', views.AllegatoListAPIView.as_view(), name='allegato_list_api'),
    path('api/allegati/<int:pk>/', views.AllegatoDetailAPIView.as_view(), name='allegato_detail_api'),
    
    # UTILITY
    path('allegati/download/<int:pk>/', views.allegato_download, name='allegato_download'),
    path('allegati/preview/<int:pk>/', views.allegato_preview, name='allegato_preview'),
]
```

---

## **6. PERMISSIONS E SECURITY**

### **6.1 Sistema Permessi**

```python
# core/permissions.py
class AllegatoPermissionMixin:
    """Mixin per controllo permessi allegati"""
    
    def check_object_permission(self, request, obj_parent):
        """Verifica permessi sull'oggetto parent"""
        model_name = obj_parent._meta.model_name
        app_label = obj_parent._meta.app_label
        
        # Permesso base: può vedere l'oggetto parent
        if not request.user.has_perm(f'{app_label}.view_{model_name}'):
            return False
            
        # Per modifica/elimina: deve poter modificare parent
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return request.user.has_perm(f'{app_label}.change_{model_name}')
            
        return True
```

### **6.2 Validazione Upload**

```python
# core/validators.py
ALLOWED_EXTENSIONS = {
    'documenti': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
    'immagini': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
    'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv'],
    'audio': ['.mp3', '.wav', '.ogg', '.flac'],
    'archivi': ['.zip', '.rar', '.7z', '.tar', '.gz'],
}

MAX_FILE_SIZE = {
    'default': 10 * 1024 * 1024,    # 10MB
    'video': 100 * 1024 * 1024,     # 100MB  
    'archivi': 50 * 1024 * 1024,    # 50MB
}
```

---

## **7. ESEMPI UTILIZZO**

### **7.1 Template Dipendente Detail**

```html
<!-- dipendenti/templates/dipendenti/dipendente_detail.html -->
{% extends 'base.html' %}
{% load allegati_tags %}

{% block content %}
<div class="row">
    <!-- Info Dipendente -->
    <div class="col-md-8">
        <!-- ... dati dipendente ... -->
    </div>
    
    <!-- Allegati Sidebar -->
    <div class="col-md-4">
        {% allegati_widget dipendente can_add=True can_edit=user.is_staff %}
    </div>
</div>

<!-- Script allegati -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    window.allegatiManager = new AllegatiManager(
        {{ dipendente.pk }}, 
        {{ dipendente|content_type_id }}
    );
});
</script>
{% endblock %}
```

### **7.2 Template Automezzo Detail**

```html
<!-- automezzi/templates/automezzi/automezzo_detail.html -->
{% extends 'base.html' %}
{% load allegati_tags %}

{% block content %}
<div class="row">
    <!-- Info Automezzo -->
    <div class="col-md-9">
        <!-- ... dati automezzo ... -->
    </div>
    
    <!-- Allegati Sidebar -->
    <div class="col-md-3">
        {% allegati_widget automezzo types_filter="doc_libretto,polizza,foto_generale,scheda_tecnica" %}
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    window.allegatiManager = new AllegatiManager(
        {{ automezzo.pk }}, 
        {{ automezzo|content_type_id }}
    );
});
</script>
{% endblock %}
```

---

## **8. BEST PRACTICES**

### **8.1 Naming Convention**
- Modal ID: `allegatoModal`
- CSS Classes: `allegato-*` (allegato-card, allegato-list, allegato-widget)
- JavaScript: `AllegatiManager` class
- URLs: `allegato_*` (allegato_create, allegato_update, etc.)

### **8.2 Performance**
- Query ottimizzate con `select_related('creato_da', 'content_type')`
- Paginazione per liste lunghe (>50 allegati)
- Lazy loading per preview immagini
- Cache per contatori allegati

### **8.3 UX Guidelines**
- Modal responsive per mobile
- Progress bar per upload file grandi
- Preview inline per immagini/PDF
- Drag & drop per upload multipli
- Toast notifications per feedback

### **8.4 Sicurezza**
- Validazione MIME type server-side
- Scan antivirus per upload (opzionale)
- Controllo dimensioni file
- Sanitizzazione nomi file
- Token CSRF per tutte le operazioni

---

## **9. TESTING**

### **9.1 Test Models**
```python
# core/tests/test_allegati_models.py
class AllegatiModelTestCase(TestCase):
    def test_allegato_creation(self)
    def test_generic_foreign_key(self)
    def test_allegati_mixin_methods(self)
```

### **9.2 Test Views**  
```python
# core/tests/test_allegati_views.py
class AllegatiViewTestCase(TestCase):
    def test_allegato_create_modal(self)
    def test_allegato_update_modal(self)
    def test_allegato_delete_permission(self)
```

### **9.3 Test JavaScript**
```javascript
// core/static/core/js/tests/allegati.test.js
describe('AllegatiManager', function() {
    it('should open add modal');
    it('should handle file upload');
    it('should refresh list after save');
});
```

---

**Questa documentazione serve come riferimento completo per implementare e utilizzare il sistema allegati in tutto il progetto Management. Seguendo queste guidelines, ogni nuovo modulo avrà automaticamente funzionalità allegati complete e consistenti.**