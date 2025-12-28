"""
Engine di automazione per il sistema procurement.
Gestisce l'automazione dei processi quando preventivi e ordini di acquisto
vengono collegati ad asset come automezzi e stabilimenti.
"""

from typing import Any, Dict, List, Optional
from django.db import models, transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class ProcurementAutomationEngine:
    """
    Engine principale per l'automazione dei processi procurement.
    
    Gestisce:
    - Allegamento automatico di documenti
    - Creazione di notifiche
    - Sincronizzazione metadati
    - Aggiornamento stati
    - Workflow automation
    """
    
    def __init__(self):
        self.automation_tasks = []
        
    def process_procurement_target_link(self, procurement_instance):
        """
        Processo principale quando un procurement viene collegato ad un target.
        
        Args:
            procurement_instance: Istanza del modello con ProcurementTargetMixin
        """
        logger.info(f"Avvio automazione per {procurement_instance} → {procurement_instance.target}")
        
        try:
            with transaction.atomic():
                # 1. Sincronizza metadati
                self._sync_metadata(procurement_instance)
                
                # 2. Allega documenti automaticamente
                if procurement_instance.auto_attach_documents:
                    self._auto_attach_documents(procurement_instance)
                
                # 3. Crea notificazioni
                self._create_notifications(procurement_instance)
                
                # 4. Aggiorna stati correlati
                self._update_related_states(procurement_instance)
                
                # 5. Esegui workflow personalizzati
                self._execute_custom_workflows(procurement_instance)
                
                logger.info(f"Automazione completata per {procurement_instance}")
                
        except Exception as e:
            logger.error(f"Errore durante automazione per {procurement_instance}: {e}")
            raise
    
    def _sync_metadata(self, procurement_instance):
        """
        Sincronizza metadati tra procurement e target.
        """
        if not procurement_instance.target:
            return
        
        try:
            # Ottieni configurazione automazione per il tipo di target
            from core.registry import procurement_target_registry
            config = procurement_target_registry.get_automation_config_for_model(
                procurement_instance.target.__class__
            )
            
            if not config.get('sync_metadata', True):
                return
            
            # Sincronizzazioni specifiche per tipo
            self._sync_common_fields(procurement_instance)
            
            # Sincronizzazioni specifiche per automezzo
            if hasattr(procurement_instance.target, 'targa'):
                self._sync_automezzo_metadata(procurement_instance)
            
            # Sincronizzazioni specifiche per stabilimento
            elif hasattr(procurement_instance.target, 'nome') and 'stabilimento' in procurement_instance.target.__class__.__name__.lower():
                self._sync_stabilimento_metadata(procurement_instance)
            
            logger.debug(f"Metadati sincronizzati per {procurement_instance}")
            
        except Exception as e:
            logger.error(f"Errore sincronizzazione metadati: {e}")
    
    def _sync_common_fields(self, procurement_instance):
        """
        Sincronizza campi comuni tra procurement e target.
        """
        # Aggiorna note se campo presente
        if hasattr(procurement_instance, 'note_interne') and hasattr(procurement_instance.target, 'note'):
            if procurement_instance.note_interne and not procurement_instance.target.note:
                procurement_instance.target.note = f"Collegato a {procurement_instance._meta.verbose_name} #{procurement_instance.pk}"
                procurement_instance.target.save(update_fields=['note'])
    
    def _sync_automezzo_metadata(self, procurement_instance):
        """
        Sincronizzazioni specifiche per automezzi.
        """
        automezzo = procurement_instance.target
        
        # Se il preventivo/acquisto è per manutenzione, aggiorna stato automezzo
        if hasattr(procurement_instance, 'descrizione') and procurement_instance.descrizione:
            desc_lower = procurement_instance.descrizione.lower()
            manutenzione_keywords = ['manutenzione', 'riparazione', 'revisione', 'tagliando']
            
            if any(keyword in desc_lower for keyword in manutenzione_keywords):
                # Potrebbe essere utile flaggare che è in manutenzione
                logger.info(f"Automezzo {automezzo.targa} collegato a manutenzione: {procurement_instance}")
    
    def _sync_stabilimento_metadata(self, procurement_instance):
        """
        Sincronizzazioni specifiche per stabilimenti.
        """
        stabilimento = procurement_instance.target
        
        # Logica specifica per stabilimenti
        logger.info(f"Stabilimento {stabilimento.nome} collegato a: {procurement_instance}")
    
    def _auto_attach_documents(self, procurement_instance):
        """
        Allega automaticamente i documenti dal procurement al target.
        """
        if not hasattr(procurement_instance, 'allegati'):
            logger.debug("Procurement non ha sistema allegati")
            return
        
        try:
            target = procurement_instance.target
            
            # Verifica che il target abbia il sistema allegati
            if not hasattr(target, 'allegati'):
                logger.debug(f"Target {target} non ha sistema allegati")
                return
            
            # Ottieni tutti gli allegati del procurement
            procurement_allegati = procurement_instance.allegati.all()
            
            if not procurement_allegati.exists():
                logger.debug("Nessun allegato da copiare")
                return
            
            # Copia allegati al target
            allegati_copiati = 0
            for allegato in procurement_allegati:
                try:
                    # Verifica se allegato già presente
                    exists = target.allegati.filter(
                        titolo=allegato.titolo,
                        file=allegato.file
                    ).exists()
                    
                    if not exists:
                        # Crea copia dell'allegato per il target
                        new_allegato = allegato.__class__(
                            titolo=f"{allegato.titolo} (da {procurement_instance._meta.verbose_name})",
                            descrizione=f"Allegato automatico da {procurement_instance._meta.verbose_name} #{procurement_instance.pk}",
                            file=allegato.file,
                            content_type=ContentType.objects.get_for_model(target),
                            object_id=target.pk,
                            caricato_da=allegato.caricato_da,
                            caricato_il=timezone.now()
                        )
                        new_allegato.save()
                        allegati_copiati += 1
                        
                except Exception as e:
                    logger.error(f"Errore copia allegato {allegato}: {e}")
            
            if allegati_copiati > 0:
                logger.info(f"Copiati {allegati_copiati} allegati da {procurement_instance} a {target}")
            
        except Exception as e:
            logger.error(f"Errore allegamento automatico documenti: {e}")
    
    def _create_notifications(self, procurement_instance):
        """
        Crea notifiche per il collegamento.
        """
        try:
            from core.registry import procurement_target_registry
            config = procurement_target_registry.get_automation_config_for_model(
                procurement_instance.target.__class__
            )
            
            if not config.get('create_notification', True):
                return
            
            # Se è una richiesta preventivo e ha fornitori, invia email
            if (procurement_instance._meta.model_name == 'richiestapreventivo' and 
                hasattr(procurement_instance, 'fornitori')):
                self._send_preventivo_emails(procurement_instance)
            
            # Se esiste un sistema di notifiche, utilizzalo
            self._try_create_system_notification(procurement_instance)
            
            # Fallback: log notification
            self._create_log_notification(procurement_instance)
            
        except Exception as e:
            logger.error(f"Errore creazione notifiche: {e}")
    
    def _send_preventivo_emails(self, richiesta_preventivo):
        """
        Invia email di richiesta preventivo ai fornitori con allegati specifici.
        """
        try:
            from core.email_utils import procurement_email_service
            
            # Ottieni i fornitori collegati alla richiesta
            fornitori = richiesta_preventivo.fornitori.all()
            
            if not fornitori.exists():
                logger.info("Nessun fornitore collegato alla richiesta, email non inviate")
                return
            
            success_count = 0
            total_count = fornitori.count()
            
            for fornitore in fornitori:
                if hasattr(fornitore, 'email') and fornitore.email:
                    try:
                        success = procurement_email_service.invia_richiesta_preventivo_con_asset(
                            richiesta_preventivo, fornitore
                        )
                        if success:
                            success_count += 1
                            
                            # Aggiorna lo stato FornitorePreventivo
                            try:
                                fornitore_preventivo, created = richiesta_preventivo.fornitorepreventivo_set.get_or_create(
                                    fornitore=fornitore,
                                    defaults={
                                        'email_inviata': True,
                                        'data_invio': timezone.now()
                                    }
                                )
                                if not created:
                                    fornitore_preventivo.email_inviata = True
                                    fornitore_preventivo.data_invio = timezone.now()
                                    fornitore_preventivo.save()
                            except Exception as e:
                                logger.warning(f"Errore aggiornamento stato FornitorePreventivo: {e}")
                                
                    except Exception as e:
                        logger.error(f"Errore invio email a {fornitore.email}: {e}")
                else:
                    logger.warning(f"Fornitore {fornitore.nome} non ha email configurata")
            
            logger.info(f"📧 Email preventivo inviate: {success_count}/{total_count} fornitori")
            
            # Aggiorna stato richiesta se tutte le email sono state inviate
            if success_count > 0:
                richiesta_preventivo.data_invio_fornitori = timezone.now()
                if richiesta_preventivo.stato == 'BOZZA':
                    richiesta_preventivo.stato = 'INVIATO_FORNITORI'
                
                # Evita ricorsioni infinite
                richiesta_preventivo._skip_automation = True
                richiesta_preventivo.save()
            
        except Exception as e:
            logger.error(f"Errore invio email preventivi: {e}")
    
    def _try_create_system_notification(self, procurement_instance):
        """
        Prova a creare una notifica di sistema se disponibile.
        """
        try:
            # Prova a importare un eventuale sistema di notifiche
            # from notifications.models import Notification
            # Notification.objects.create(...)
            pass
        except ImportError:
            pass
    
    def _create_log_notification(self, procurement_instance):
        """
        Crea una notifica via log.
        """
        message = (
            f"🔗 Nuovo collegamento: {procurement_instance._meta.verbose_name} "
            f"#{procurement_instance.pk} collegato a {procurement_instance.target_display_name}"
        )
        logger.info(message)
    
    def _update_related_states(self, procurement_instance):
        """
        Aggiorna stati di record correlati.
        """
        try:
            # Aggiorna timestamp ultima modifica se disponibile
            if hasattr(procurement_instance.target, 'modified'):
                procurement_instance.target.modified = timezone.now()
                procurement_instance.target.save(update_fields=['modified'])
            
            # Logiche di stato specifiche
            self._update_procurement_state(procurement_instance)
            self._update_target_state(procurement_instance)
            
        except Exception as e:
            logger.error(f"Errore aggiornamento stati: {e}")
    
    def _update_procurement_state(self, procurement_instance):
        """
        Aggiorna stato del procurement.
        """
        # Se il procurement ha un campo stato, potrebbe essere utile aggiornarlo
        if hasattr(procurement_instance, 'stato'):
            # Logica per aggiornare stato in base al collegamento
            pass
    
    def _update_target_state(self, procurement_instance):
        """
        Aggiorna stato del target.
        """
        target = procurement_instance.target
        
        # Per automezzi: se è un acquisto di manutenzione, potrebbe influenzare disponibilità
        if hasattr(target, 'disponibile') and hasattr(procurement_instance, 'descrizione'):
            if procurement_instance.descrizione and 'manutenzione' in procurement_instance.descrizione.lower():
                # Potrebbe essere utile flaggare che necessita manutenzione
                pass
    
    def _execute_custom_workflows(self, procurement_instance):
        """
        Esegue workflow personalizzati basati su configurazione.
        """
        try:
            # Workflow basati sul tipo di procurement
            self._execute_preventivo_workflows(procurement_instance)
            self._execute_acquisto_workflows(procurement_instance)
            
            # Workflow basati sul tipo di target
            self._execute_target_specific_workflows(procurement_instance)
            
        except Exception as e:
            logger.error(f"Errore esecuzione workflow personalizzati: {e}")
    
    def _execute_preventivo_workflows(self, procurement_instance):
        """
        Workflow specifici per preventivi.
        """
        if 'preventivo' not in procurement_instance._meta.model_name.lower():
            return
        
        # Workflow preventivi
        logger.debug(f"Esecuzione workflow preventivo per {procurement_instance}")
    
    def _execute_acquisto_workflows(self, procurement_instance):
        """
        Workflow specifici per ordini di acquisto.
        """
        if 'acquisto' not in procurement_instance._meta.model_name.lower() and 'ordine' not in procurement_instance._meta.model_name.lower():
            return
        
        # Workflow ordini di acquisto
        logger.debug(f"Esecuzione workflow acquisto per {procurement_instance}")
    
    def _execute_target_specific_workflows(self, procurement_instance):
        """
        Workflow specifici per tipo di target.
        """
        target = procurement_instance.target
        
        # Workflow automezzi
        if hasattr(target, 'targa'):
            self._automezzo_workflows(procurement_instance, target)
        
        # Workflow stabilimenti
        elif hasattr(target, 'nome') and 'stabilimento' in target.__class__.__name__.lower():
            self._stabilimento_workflows(procurement_instance, target)
    
    def _automezzo_workflows(self, procurement_instance, automezzo):
        """
        Workflow specifici per automezzi.
        """
        # Workflow per manutenzioni
        if hasattr(procurement_instance, 'descrizione') and procurement_instance.descrizione:
            desc_lower = procurement_instance.descrizione.lower()
            
            # Se è relativo a manutenzione e si tratta di un ordine di acquisto approvato
            if any(keyword in desc_lower for keyword in ['manutenzione', 'riparazione', 'tagliando', 'revisione']):
                self._handle_manutenzione_workflow(procurement_instance, automezzo)
            
            # Workflow carburante
            elif 'carburante' in desc_lower or 'benzina' in desc_lower or 'diesel' in desc_lower:
                logger.info(f"Possibile acquisto carburante per automezzo {automezzo.targa}")
                # Qui potresti creare automaticamente un record di rifornimento
    
    def _handle_manutenzione_workflow(self, procurement_instance, automezzo):
        """
        Gestisce il workflow specifico per le manutenzioni automezzi.
        """
        # Se è un ordine di acquisto approvato, crea automaticamente la manutenzione
        if procurement_instance._meta.model_name == 'ordineacquisto':
            logger.info(f"🔧 Creazione manutenzione automatica per {automezzo.targa} da ordine {procurement_instance.numero_ordine}")
            
            try:
                # Importa il modello Manutenzione
                from django.apps import apps
                if apps.is_installed('automezzi'):
                    Manutenzione = apps.get_model('automezzi', 'Manutenzione')
                    
                    # Crea la manutenzione
                    manutenzione = Manutenzione.objects.create(
                        automezzo=automezzo,
                        descrizione=f"Manutenzione da ordine {procurement_instance.numero_ordine}",
                        data_prevista=procurement_instance.data_consegna_richiesta or timezone.now().date(),
                        costo=procurement_instance.importo_totale,
                        note_interne=f"Manutenzione generata automaticamente dall'ordine di acquisto {procurement_instance.numero_ordine}",
                        seguito_da=procurement_instance.creato_da,
                        stato='aperta'
                    )
                    
                    logger.info(f"✅ Manutenzione #{manutenzione.pk} creata automaticamente per {automezzo.targa}")
                    
                    # Allega l'ordine di acquisto alla manutenzione se possibile
                    self._attach_ordine_to_manutenzione(procurement_instance, manutenzione)
                    
                    # Allega l'ordine di acquisto anche al dettaglio automezzo
                    self._attach_ordine_to_automezzo(procurement_instance, automezzo)
                    
                    return manutenzione
                    
            except Exception as e:
                logger.error(f"Errore creazione manutenzione automatica: {e}")
        
        return None
    
    def _attach_ordine_to_manutenzione(self, ordine_acquisto, manutenzione):
        """
        Allega l'ordine di acquisto alla manutenzione come allegato.
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            
            # Verifica se esiste il sistema allegati
            from django.apps import apps
            if apps.is_installed('core'):
                Allegato = apps.get_model('core', 'Allegato')
                
                # Crea allegato per collegare ordine acquisto alla manutenzione
                allegato = Allegato.objects.create(
                    content_type=ContentType.objects.get_for_model(manutenzione),
                    object_id=manutenzione.pk,
                    titolo=f"Ordine di Acquisto {ordine_acquisto.numero_ordine}",
                    descrizione=f"Ordine di acquisto collegato automaticamente - Fornitore: {ordine_acquisto.fornitore.nome}",
                    tipo_allegato='doc_ordine',
                    stato='attivo',
                    caricato_da=ordine_acquisto.creato_da
                )
                
                logger.info(f"📎 Allegato ordine acquisto #{allegato.pk} collegato alla manutenzione")
                return allegato
                
        except Exception as e:
            logger.error(f"Errore allegamento ordine a manutenzione: {e}")
        
        return None
    
    def _attach_ordine_to_automezzo(self, ordine_acquisto, automezzo):
        """
        Allega l'ordine di acquisto al dettaglio automezzo come allegato.
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            
            # Verifica se esiste il sistema allegati
            from django.apps import apps
            if apps.is_installed('core'):
                Allegato = apps.get_model('core', 'Allegato')
                
                # Crea allegato per collegare ordine acquisto all'automezzo
                allegato = Allegato.objects.create(
                    content_type=ContentType.objects.get_for_model(automezzo),
                    object_id=automezzo.pk,
                    titolo=f"Ordine di Acquisto {ordine_acquisto.numero_ordine}",
                    descrizione=f"Ordine di acquisto per manutenzione - Fornitore: {ordine_acquisto.fornitore.nome} - €{ordine_acquisto.importo_totale}",
                    tipo_allegato='doc_ordine_manutenzione',
                    stato='attivo',
                    caricato_da=ordine_acquisto.creato_da
                )
                
                logger.info(f"📎 Allegato ordine acquisto #{allegato.pk} collegato all'automezzo {automezzo.targa}")
                return allegato
                
        except Exception as e:
            logger.error(f"Errore allegamento ordine ad automezzo: {e}")
        
        return None
    
    def _stabilimento_workflows(self, procurement_instance, stabilimento):
        """
        Workflow specifici per stabilimenti.
        """
        # Workflow specifici per stabilimenti
        logger.debug(f"Workflow stabilimento per {stabilimento.nome}")
    
    def get_automation_summary(self, procurement_instance) -> Dict[str, Any]:
        """
        Restituisce un riassunto delle automazioni disponibili per un procurement.
        """
        if not procurement_instance.target:
            return {'available_automations': []}
        
        try:
            from core.registry import procurement_target_registry
            config = procurement_target_registry.get_automation_config_for_model(
                procurement_instance.target.__class__
            )
            
            summary = {
                'target_type': procurement_instance.target_type_name,
                'target_name': procurement_instance.target_display_name,
                'automation_config': config,
                'available_automations': [
                    'sync_metadata' if config.get('sync_metadata', True) else None,
                    'auto_attach_documents' if procurement_instance.auto_attach_documents else None,
                    'create_notification' if config.get('create_notification', True) else None
                ],
                'last_automation': getattr(procurement_instance, '_last_automation', None)
            }
            
            # Rimuovi None
            summary['available_automations'] = [a for a in summary['available_automations'] if a]
            
            return summary
            
        except Exception as e:
            logger.error(f"Errore generazione summary automazione: {e}")
            return {'error': str(e)}
    
    def test_automation(self, procurement_instance, dry_run=True):
        """
        Testa l'automazione senza eseguire modifiche reali.
        Utile per debugging e validazione.
        """
        logger.info(f"Test automazione (dry_run={dry_run}) per {procurement_instance}")
        
        test_results = {
            'target': str(procurement_instance.target) if procurement_instance.target else None,
            'metadata_sync': False,
            'documents_to_attach': 0,
            'notifications_to_create': 0,
            'errors': []
        }
        
        try:
            if procurement_instance.target:
                test_results['metadata_sync'] = True
                
                if hasattr(procurement_instance, 'allegati'):
                    test_results['documents_to_attach'] = procurement_instance.allegati.count()
                
                test_results['notifications_to_create'] = 1
            
            if not dry_run:
                self.process_procurement_target_link(procurement_instance)
            
        except Exception as e:
            test_results['errors'].append(str(e))
        
        return test_results