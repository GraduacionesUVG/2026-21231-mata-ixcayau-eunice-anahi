from django.contrib import admin

from .models import Empresa, PerfilUsuario


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_negocio', 'color_tema', 'onboarding_completo', 'creado_en')


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'empresa', 'rol', 'sucursal', 'activo', 'creado_en')
    list_filter = ('rol', 'activo', 'empresa')
