"""
CORE ALLEGATI MIXINS - Mixin per Funzionalità Allegati
=====================================================

Mixin che aggiunge funzionalità allegati a qualsiasi modello Django.
Permette di gestire allegati universali senza modificare la struttura
del database dei modelli esistenti.

Usage:
    class MioModello(models.Model, AllegatiMixin):
        # ... campi del modello
        pass

Versione: 1.0
"""

from typing import List, Dict, Any, Optional, Union
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AllegatiMixin:
    """
    Mixin che aggiunge funzionalità allegati a qualsiasi modello Django.
    
    Metodi disponibili:
    - get_allegati(): QuerySet allegati dell'oggetto
    - allegati_count: Numero allegati
    - ha_allegati: Boolean se ha allegati
    - add_allegato(): Aggiunge allegato
    - get_allegati_by_type(): Filtra per tipo
    - get_allegati_recenti(): Allegati recenti
    """
    
    def get_allegati(self):
        """
        Ottieni tutti gli allegati di questo oggetto.
        
        Returns:
            QuerySet: QuerySet degli allegati ordinati per data creazione desc
        """
        from ..models.allegati import Allegato
        
        content_type = ContentType.objects.get_for_model(self.__class__)
        return Allegato.objects.filter(
            content_type=content_type,
            object_id=self.pk
        ).select_related('creato_da', 'modificato_da')
    
    @property
    def allegati_count(self):
        """
        Numero totale di allegati attivi.
        
        Returns:
            int: Numero allegati attivi
        """
        return self.get_allegati().attivi().count()
    
    @property
    def ha_allegati(self):
        """
        Verifica se l'oggetto ha allegati.
        
        Returns:
            bool: True se ha almeno un allegato attivo
        """
        return self.allegati_count > 0
    
    def get_allegati_by_type(self, tipo_pattern: str):
        """
        Ottieni allegati filtrati per tipo.
        Supporta wildcard con * (es: 'doc_*' per tutti i documenti).
        
        Args:
            tipo_pattern (str): Pattern tipo allegato (supporta * come wildcard)
            
        Returns:
            QuerySet: Allegati filtrati per tipo
            
        Examples:
            obj.get_allegati_by_type('doc_*')      # Tutti i documenti
            obj.get_allegati_by_type('email_*')    # Tutte le email
            obj.get_allegati_by_type('foto_generale') # Solo foto generali
        """
        return self.get_allegati().per_tipo(tipo_pattern)
    
    def get_allegati_documenti(self):
        """Ottieni solo allegati di tipo documento"""
        return self.get_allegati().documenti()
    
    def get_allegati_comunicazioni(self):
        """Ottieni solo allegati di comunicazione (email, sms, etc.)"""
        return self.get_allegati().comunicazioni()
    
    def get_allegati_media(self):
        """Ottieni solo allegati media (foto, video, audio)"""
        return self.get_allegati().media()
    
    def get_allegati_note(self):
        """Ottieni solo note e appunti"""
        return self.get_allegati().note()
    
    def get_allegati_con_file(self):
        """Ottieni solo allegati con file"""
        return self.get_allegati().con_file()
    
    def get_allegati_senza_file(self):
        """Ottieni solo allegati senza file (note testuali, link)"""
        return self.get_allegati().senza_file()
    
    def get_allegati_recenti(self, giorni: int = 7):
        """
        Ottieni allegati degli ultimi X giorni.
        
        Args:
            giorni (int): Numero giorni da considerare (default: 7)
            
        Returns:
            QuerySet: Allegati creati negli ultimi X giorni
        """
        return self.get_allegati().recenti(giorni)
    
    def get_allegati_scaduti(self):
        """Ottieni allegati scaduti"""
        return self.get_allegati().scaduti()
    
    def get_allegati_in_scadenza(self, giorni: int = 7):
        """
        Ottieni allegati in scadenza entro X giorni.
        
        Args:
            giorni (int): Giorni di preavviso scadenza (default: 7)
            
        Returns:
            QuerySet: Allegati in scadenza
        """
        return self.get_allegati().in_scadenza(giorni)
    
    def get_allegati_per_utente(self, user):
        """
        Ottieni allegati creati da un utente specifico.
        
        Args:
            user: User object
            
        Returns:
            QuerySet: Allegati creati dall'utente
        """
        return self.get_allegati().per_utente(user)
    
    def add_allegato(self, titolo: str, tipo_allegato: str, creato_da=None, **kwargs):
        """
        Aggiunge un allegato a questo oggetto.
        
        Args:
            titolo (str): Titolo dell'allegato
            tipo_allegato (str): Tipo allegato (vedi TIPO_ALLEGATO_CHOICES)
            creato_da: User che crea l'allegato
            **kwargs: Altri parametri dell'allegato (descrizione, file, etc.)
            
        Returns:
            Allegato: Oggetto allegato creato
            
        Example:
            dipendente.add_allegato(
                titolo="Contratto di lavoro",
                tipo_allegato="doc_contratto",
                descrizione="Contratto rinnovato 2024",
                file=file_obj,
                creato_da=request.user
            )
        """
        from ..models.allegati import Allegato
        
        content_type = ContentType.objects.get_for_model(self.__class__)
        
        allegato_data = {
            'content_type': content_type,
            'object_id': self.pk,
            'titolo': titolo,
            'tipo_allegato': tipo_allegato,
            'creato_da': creato_da,
            **kwargs
        }
        
        return Allegato.objects.create(**allegato_data)
    
    def add_allegato_documento(self, titolo: str, file, tipo_documento: str = 'doc_certificato', **kwargs):
        """
        Convenienza per aggiungere documento.
        
        Args:
            titolo (str): Titolo documento
            file: File object
            tipo_documento (str): Tipo documento (default: 'doc_certificato')
            **kwargs: Altri parametri
            
        Returns:
            Allegato: Allegato creato
        """
        return self.add_allegato(
            titolo=titolo,
            tipo_allegato=tipo_documento,
            file=file,
            **kwargs
        )
    
    def add_allegato_foto(self, titolo: str, file, tipo_foto: str = 'foto_generale', **kwargs):
        """
        Convenienza per aggiungere foto.
        
        Args:
            titolo (str): Titolo foto
            file: File immagine
            tipo_foto (str): Tipo foto (default: 'foto_generale')
            **kwargs: Altri parametri
            
        Returns:
            Allegato: Allegato creato
        """
        return self.add_allegato(
            titolo=titolo,
            tipo_allegato=tipo_foto,
            file=file,
            **kwargs
        )
    
    def add_allegato_nota(self, titolo: str, contenuto: str, tipo_nota: str = 'nota_interna', **kwargs):
        """
        Convenienza per aggiungere nota testuale.
        
        Args:
            titolo (str): Titolo nota
            contenuto (str): Contenuto testuale
            tipo_nota (str): Tipo nota (default: 'nota_interna')
            **kwargs: Altri parametri
            
        Returns:
            Allegato: Allegato creato
        """
        return self.add_allegato(
            titolo=titolo,
            tipo_allegato=tipo_nota,
            contenuto_testo=contenuto,
            **kwargs
        )
    
    def add_allegato_link(self, titolo: str, url: str, descrizione: str = '', **kwargs):
        """
        Convenienza per aggiungere link esterno.
        
        Args:
            titolo (str): Titolo link
            url (str): URL esterno
            descrizione (str): Descrizione opzionale
            **kwargs: Altri parametri
            
        Returns:
            Allegato: Allegato creato
        """
        return self.add_allegato(
            titolo=titolo,
            tipo_allegato='link_esterno',
            url_esterno=url,
            descrizione=descrizione,
            **kwargs
        )
    
    def add_allegato_email(self, titolo: str, tipo_email: str, contenuto: str = '', **kwargs):
        """
        Convenienza per aggiungere email.
        
        Args:
            titolo (str): Oggetto email
            tipo_email (str): 'email_inviata' o 'email_ricevuta'
            contenuto (str): Contenuto email
            **kwargs: Altri parametri
            
        Returns:
            Allegato: Allegato creato
        """
        if tipo_email not in ['email_inviata', 'email_ricevuta']:
            raise ValueError("tipo_email deve essere 'email_inviata' o 'email_ricevuta'")
        
        return self.add_allegato(
            titolo=titolo,
            tipo_allegato=tipo_email,
            contenuto_testo=contenuto,
            **kwargs
        )
    
    def rimuovi_allegato(self, allegato_id: int):
        """
        Rimuove (marca come eliminato) un allegato.
        
        Args:
            allegato_id (int): ID dell'allegato da rimuovere
            
        Returns:
            bool: True se rimosso con successo
        """
        try:
            allegato = self.get_allegati().get(pk=allegato_id)
            allegato.stato = 'eliminato'
            allegato.save()
            return True
        except:
            return False
    
    def elimina_allegato(self, allegato_id: int):
        """
        Elimina definitivamente un allegato.
        
        Args:
            allegato_id (int): ID dell'allegato da eliminare
            
        Returns:
            bool: True se eliminato con successo
        """
        try:
            allegato = self.get_allegati().get(pk=allegato_id)
            allegato.delete()
            return True
        except:
            return False
    
    def archivia_allegato(self, allegato_id: int):
        """
        Archivia un allegato (cambia stato in 'archiviato').
        
        Args:
            allegato_id (int): ID dell'allegato da archiviare
            
        Returns:
            bool: True se archiviato con successo
        """
        try:
            allegato = self.get_allegati().get(pk=allegato_id)
            allegato.stato = 'archiviato'
            allegato.save()
            return True
        except:
            return False
    
    def get_allegati_stats(self) -> Dict[str, Any]:
        """
        Ottieni statistiche allegati per questo oggetto.
        
        Returns:
            dict: Statistiche dettagliate degli allegati
            
        Example:
            stats = dipendente.get_allegati_stats()
            print(f"Totale: {stats['totale']}")
            print(f"Documenti: {stats['per_categoria']['documenti']}")
        """
        allegati = self.get_allegati().attivi()
        
        # Contatori base
        stats = {
            'totale': allegati.count(),
            'con_file': allegati.con_file().count(),
            'senza_file': allegati.senza_file().count(),
            'recenti': allegati.recenti(7).count(),
            'scaduti': allegati.scaduti().count(),
            'in_scadenza': allegati.in_scadenza(7).count(),
        }
        
        # Contatori per categoria
        stats['per_categoria'] = {
            'documenti': allegati.documenti().count(),
            'comunicazioni': allegati.comunicazioni().count(),
            'media': allegati.media().count(),
            'note': allegati.note().count(),
        }
        
        # Contatori per tipo
        from django.db.models import Count
        tipi = allegati.values('tipo_allegato').annotate(
            count=Count('tipo_allegato')
        ).order_by('-count')
        
        stats['per_tipo'] = {item['tipo_allegato']: item['count'] for item in tipi}
        
        # Contatori per stato
        from ..models.allegati import Allegato
        tutti_allegati = self.get_allegati()  # Include tutti gli stati
        
        stati = tutti_allegati.values('stato').annotate(
            count=Count('stato')
        )
        
        stats['per_stato'] = {item['stato']: item['count'] for item in stati}
        
        return stats
    
    def get_allegati_summary(self) -> str:
        """
        Ottieni summary testuale degli allegati.
        
        Returns:
            str: Summary formattato degli allegati
        """
        stats = self.get_allegati_stats()
        
        if stats['totale'] == 0:
            return "Nessun allegato presente"
        
        summary_parts = [f"{stats['totale']} allegati"]
        
        if stats['per_categoria']['documenti'] > 0:
            summary_parts.append(f"{stats['per_categoria']['documenti']} documenti")
        
        if stats['per_categoria']['media'] > 0:
            summary_parts.append(f"{stats['per_categoria']['media']} media")
        
        if stats['scaduti'] > 0:
            summary_parts.append(f"{stats['scaduti']} scaduti")
        
        if stats['in_scadenza'] > 0:
            summary_parts.append(f"{stats['in_scadenza']} in scadenza")
        
        return ", ".join(summary_parts)
    
    def get_allegati_per_sidebar(self, limit: int = 5):
        """
        Ottieni allegati formattati per sidebar widget.
        
        Args:
            limit (int): Numero massimo allegati da restituire
            
        Returns:
            QuerySet: Allegati più recenti limitati
        """
        return self.get_allegati().attivi()[:limit]
    
    def get_content_type_id(self):
        """
        Ottieni Content Type ID per questo oggetto.
        Utile nei template per costruire URL allegati.
        
        Returns:
            int: ID del ContentType
        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        return content_type.pk
    
    def get_model_verbose_name(self):
        """
        Ottieni nome verbose del modello.
        
        Returns:
            str: Nome verbose del modello
        """
        return self._meta.verbose_name
    
    def get_model_verbose_name_plural(self):
        """
        Ottieni nome verbose plurale del modello.
        
        Returns:
            str: Nome verbose plurale del modello
        """
        return self._meta.verbose_name_plural