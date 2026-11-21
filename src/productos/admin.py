from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'empresa', 'precio_venta', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('codigo', 'nombre')
