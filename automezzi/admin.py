from django.contrib import admin
from .models import *

admin.site.register(Automezzo)
admin.site.register(Manutenzione)
admin.site.register(EventoAutomezzo)
admin.site.register(Rifornimento)