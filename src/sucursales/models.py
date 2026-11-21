from django.db import models

from core.models import Empresa


class Sucursal(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=5, help_text='Máximo 5 caracteres, ej: SUC1.')
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=120, blank=True)
    # si es False, es un almacén central sin venta directa al público
    tiene_punto_venta = models.BooleanField(
        default=True, verbose_name='¿Tiene punto de venta?')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='codigo_unico_por_empresa'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'


class Almacen(models.Model):
    """Se genera automáticamente al crear una Sucursal (ver crear_sucursal)."""
    sucursal = models.OneToOneField(Sucursal, on_delete=models.CASCADE, related_name='almacen')
    nombre = models.CharField(max_length=150)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'

    def __str__(self):
        return self.nombre
