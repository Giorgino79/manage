# Sistema di Gestione Costi Aziendali - Architettura Procurement

## Panoramica

Il sistema di gestione costi aziendali implementa un'architettura scalabile per collegare automaticamente preventivi e ordini di acquisto ad asset aziendali come automezzi, stabilimenti e futuri tipi di beni. L'obiettivo è creare un sistema integrato che permetta di tracciare i costi per ogni asset e automatizzare i processi di documentazione.

## Architettura del Sistema

### 1. ProcurementTargetMixin

Il mixin base che fornisce la funzionalità di collegamento generico:

```python
from core.mixins.procurement import ProcurementTargetMixin

class RichiestaPreventivo(ProcurementTargetMixin, models.Model):
    # I tuoi campi esistenti...
    pass
```

**Funzionalità fornite:**
- Generic Foreign Key per collegamento a qualsiasi asset registrato
- Validazione automatica del tipo di target
- Proprietà di accesso rapido (`target_display_name`, `target_type_name`)
- Metodi helper per gestione collegamenti
- Trigger automatico dell'automazione al salvataggio

**Campi aggiunti:**
- `target_content_type`: Tipo dell'asset collegato
- `target_object_id`: ID specifico dell'asset
- `target`: Generic Foreign Key per accesso diretto
- `auto_attach_documents`: Flag per automazione documenti

### 2. ProcurementTargetRegistry

Registry centralizzato per gestire i tipi di asset supportati:

```python
from core.registry import procurement_target_registry

# Registrazione automatica nei file apps.py
procurement_target_registry.register(
    Automezzo,
    display_name="Automezzo",
    icon="fas fa-car",
    description="Veicoli e mezzi aziendali",
    form_widget_config={
        'search_fields': ['targa', 'marca', 'modello'],
        'display_field': 'targa',
        'default_filters': {'attivo': True}
    }
)
```

**Funzionalità:**
- Registrazione dinamica di nuovi tipi di asset
- Configurazione per widget di ricerca nei form
- Validazione dei target supportati
- Metadati per interfaccia utente (icone, nomi display)

### 3. ProcurementAutomationEngine

Engine per automazione dei processi:

```python
from core.automation.procurement import ProcurementAutomationEngine

engine = ProcurementAutomationEngine()
engine.process_procurement_target_link(preventivo_instance)
```

**Processi automatici:**
- Sincronizzazione metadati tra procurement e target
- Allegamento automatico documenti
- Creazione notifiche
- Aggiornamento stati correlati
- Workflow personalizzati per tipo

### 4. SmartTargetSelectorWidget

Widget intelligente per selezione target nei form:

```python
from core.forms.procurement import ProcurementTargetFormMixin

class PreventovoForm(ProcurementTargetFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_target_fields()
```

**Caratteristiche:**
- Selezione a due step: tipo asset → oggetto specifico
- Ricerca dinamica tramite AJAX
- Validazione automatica
- Interfaccia user-friendly

## Implementazione per Nuove App

### Passo 1: Preparazione del Modello

Per rendere un modello compatibile come target procurement, non sono necessarie modifiche al modello stesso. Il collegamento avviene tramite Generic Foreign Key.

### Passo 2: Registrazione nell'App Config

Modifica il file `apps.py` della tua app:

```python
from django.apps import AppConfig

class TuaAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tua_app'
    
    def ready(self):
        try:
            from core.registry import procurement_target_registry
            from .models import TuoModello
            
            procurement_target_registry.register(
                TuoModello,
                display_name="Nome Visualizzato",
                icon="fas fa-icon-name",  # Icona FontAwesome
                description="Descrizione del tipo di asset",
                form_widget_config={
                    'search_fields': ['campo1', 'campo2'],  # Campi per ricerca
                    'display_field': 'nome',  # Campo principale per display
                    'default_filters': {'attivo': True}  # Filtri di default
                },
                automation_config={
                    'auto_attach_documents': True,
                    'create_notification': True,
                    'sync_metadata': True
                }
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Errore registrazione procurement target: {e}")
```

### Passo 3: Aggiornamento Form (Opzionale)

Se vuoi aggiungere la selezione target ai form della tua app:

```python
from core.forms.procurement import ProcurementTargetFormMixin

class TuoForm(ProcurementTargetFormMixin, forms.ModelForm):
    class Meta:
        model = TuoModello
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_target_fields()  # Aggiunge i campi per selezione target
        
        if self.instance.pk:
            self.setup_target_fields_from_instance(self.instance)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance = self.save_target_fields(instance)
        
        if commit:
            instance.save()
        
        return instance
```

## Configurazione Avanzata

### Workflow Personalizzati

È possibile estendere l'automazione per workflow specifici:

```python
# In core/automation/procurement.py
def _execute_custom_workflows(self, procurement_instance):
    target = procurement_instance.target
    
    # Workflow specifico per il tuo tipo di asset
    if isinstance(target, TuoModello):
        self._tuo_workflow_personalizzato(procurement_instance, target)

def _tuo_workflow_personalizzato(self, procurement_instance, target):
    # Logica personalizzata
    if 'manutenzione' in procurement_instance.descrizione.lower():
        # Esempio: crea automaticamente un record di manutenzione
        pass
```

### Campi di Ricerca Personalizzati

Configura come vengono cercati i tuoi asset:

```python
form_widget_config={
    'search_fields': ['codice', 'nome', 'descrizione'],
    'display_field': 'nome',
    'display_template': '{nome} ({codice})',  # Template personalizzato
    'default_filters': {
        'attivo': True,
        'tipo': 'specifico'
    },
    'ordering': ['nome', 'codice']
}
```

### Automazione Documenti

L'automazione documenti può essere configurata per tipo:

```python
automation_config={
    'auto_attach_documents': True,
    'sync_metadata': True,
    'create_notification': True,
    'document_types': ['contratto', 'fattura'],  # Tipi specifici
    'notification_recipients': ['responsabile_asset']
}
```

## Utilizzo del Sistema

### 1. Creazione Preventivo con Target

```python
# Nel form di creazione preventivo
preventivo = RichiestaPreventivo.objects.create(
    titolo="Manutenzione Automezzo",
    descrizione="Tagliando periodico",
    # ... altri campi
)

# Collega all'automezzo
automezzo = Automezzo.objects.get(targa='AB123CD')
preventivo.attach_target(automezzo)

# L'automazione si attiva automaticamente:
# - Documenti allegati all'automezzo
# - Notifiche create
# - Metadati sincronizzati
```

### 2. Ricerca Preventivi per Asset

```python
# Trova tutti i preventivi collegati a un automezzo
automezzo = Automezzo.objects.get(targa='AB123CD')
ct = ContentType.objects.get_for_model(automezzo)

preventivi = RichiestaPreventivo.objects.filter(
    target_content_type=ct,
    target_object_id=automezzo.id
)
```

### 3. Dashboard Costi per Asset

```python
def get_costi_automezzo(automezzo):
    ct = ContentType.objects.get_for_model(automezzo)
    
    preventivi = RichiestaPreventivo.objects.filter(
        target_content_type=ct,
        target_object_id=automezzo.id
    )
    
    ordini = OrdineAcquisto.objects.filter(
        target_content_type=ct,
        target_object_id=automezzo.id
    )
    
    return {
        'preventivi': preventivi,
        'ordini': ordini,
        'costo_totale': sum(o.importo_totale for o in ordini),
        'preventivi_pending': preventivi.filter(stato='BOZZA').count()
    }
```

## Esempi Pratici

### Collegamento Automatico Manutenzioni

Quando un ordine di acquisto viene creato per un automezzo con descrizione contenente "manutenzione":

1. Il sistema rileva la parola chiave
2. Allega automaticamente i documenti all'automezzo
3. Crea una notifica al responsabile automezzi
4. Aggiorna le note dell'automezzo

### Gestione Costi Stabilimento

Per gli acquisti collegati a stabilimenti:

1. I documenti vengono allegati al record stabilimento
2. Le fatture sono disponibili nella sezione documenti
3. Report automatici sui costi per stabilimento
4. Tracking delle spese per centro di costo

### Integrazione con Futuri Asset

Per aggiungere supporto a "Macchinari":

```python
# In macchinari/apps.py
def ready(self):
    from core.registry import procurement_target_registry
    from .models import Macchinario
    
    procurement_target_registry.register(
        Macchinario,
        display_name="Macchinario",
        icon="fas fa-cogs",
        description="Macchinari industriali",
        form_widget_config={
            'search_fields': ['codice', 'nome', 'modello'],
            'display_field': 'codice'
        }
    )
```

Il macchinario sarà automaticamente disponibile come target nei preventivi e ordini di acquisto.

## Vantaggi del Sistema

1. **Scalabilità**: Facile aggiunta di nuovi tipi di asset
2. **Automazione**: Processi automatici per efficienza operativa
3. **Tracciabilità**: Collegamenti diretti tra costi e asset
4. **Integrazione**: Sistema unificato per tutti i tipi di procurement
5. **Flessibilità**: Configurazione personalizzabile per ogni tipo
6. **Consistenza**: Interfaccia uniforme per tutti gli asset

## Manutenzione del Sistema

### Monitoring

```python
from core.registry import procurement_target_registry

# Statistiche del registry
stats = procurement_target_registry.get_statistics()
print(f"Asset registrati: {stats['total_registered']}")
print(f"App coinvolte: {stats['apps']}")
```

### Debug

```python
from core.automation.procurement import ProcurementAutomationEngine

engine = ProcurementAutomationEngine()
risultati = engine.test_automation(preventivo, dry_run=True)
print("Test automazione:", risultati)
```

### Troubleshooting

I log dell'automazione sono disponibili con:

```python
import logging
logger = logging.getLogger('core.automation.procurement')
```

Problemi comuni:
- Modello non registrato: Verificare apps.py
- Automazione non attivata: Controllare `auto_attach_documents` flag
- Target non trovato: Verificare esistenza e validità dell'asset