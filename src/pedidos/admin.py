from django.contrib import admin

from .models import Pedido, PedidoLinea


class PedidoLineaInline(admin.TabularInline):
    model = PedidoLinea
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'cliente', 'estado', 'creado_en', 'completado_en')
    list_filter = ('empresa', 'estado')
    inlines = [PedidoLineaInline]
