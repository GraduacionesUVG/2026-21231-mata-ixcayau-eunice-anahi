from django.contrib import admin

from .models import Venta, VentaLinea


class VentaLineaInline(admin.TabularInline):
    model = VentaLinea
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'sucursal', 'operador', 'total', 'fecha')
    list_filter = ('sucursal',)
    inlines = [VentaLineaInline]
