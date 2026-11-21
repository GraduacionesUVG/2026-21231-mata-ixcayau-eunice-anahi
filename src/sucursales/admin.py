from django.contrib import admin

from .models import Almacen, Sucursal


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'empresa', 'tiene_punto_venta', 'creado_en')
    list_filter = ('empresa', 'tiene_punto_venta')


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sucursal')
