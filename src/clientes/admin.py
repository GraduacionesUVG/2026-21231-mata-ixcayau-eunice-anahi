from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'empresa', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('nombre', 'telefono')
