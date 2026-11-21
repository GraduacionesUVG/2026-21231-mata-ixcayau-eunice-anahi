from django.contrib import admin

from .models import MovimientoStock, Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('producto', 'sucursal', 'cantidad', 'stock_minimo')
    list_filter = ('sucursal',)


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'sucursal_origen', 'sucursal_destino', 'cantidad', 'creado_en')
    list_filter = ('tipo', 'empresa')
