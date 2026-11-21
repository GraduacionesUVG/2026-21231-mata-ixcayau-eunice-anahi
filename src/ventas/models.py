from django.db import models

from clientes.models import Cliente
from core.models import PerfilUsuario
from productos.models import Producto
from sucursales.models import Sucursal


class Venta(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='ventas')
    operador = models.ForeignKey(PerfilUsuario, null=True, on_delete=models.SET_NULL, related_name='ventas_registradas')
    cliente = models.ForeignKey(
        Cliente, null=True, blank=True, on_delete=models.SET_NULL, related_name='ventas',
        help_text='Vacío = venta anónima.')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']

    def __str__(self):
        return f'Venta #{self.pk} - {self.sucursal}'


class VentaLinea(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(Producto, null=True, blank=True, on_delete=models.SET_NULL)
    descripcion_libre = models.CharField(max_length=255, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=0)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Línea de venta'
        verbose_name_plural = 'Líneas de venta'

    def __str__(self):
        return self.descripcion

    @property
    def descripcion(self):
        return self.producto.nombre if self.producto else self.descripcion_libre

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
