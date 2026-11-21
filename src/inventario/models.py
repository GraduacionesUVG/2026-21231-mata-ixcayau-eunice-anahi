from django.db import models

from core.models import Empresa, PerfilUsuario
from productos.models import Producto
from proveedores.models import Proveedor
from sucursales.models import Sucursal


class Stock(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='stock')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stock')
    cantidad = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    class Meta:
        verbose_name = 'Stock'
        verbose_name_plural = 'Stock'
        constraints = [
            models.UniqueConstraint(fields=['sucursal', 'producto'], name='stock_unico_sucursal_producto'),
        ]

    def __str__(self):
        return f'{self.producto} @ {self.sucursal}: {self.cantidad}'

    @property
    def bajo_minimo(self):
        return self.cantidad <= self.stock_minimo


class MovimientoStock(models.Model):
    TIPO = [
        ('entrada', 'Entrada'),
        ('transferencia', 'Transferencia'),
        ('venta', 'Venta'),
        ('ajuste', 'Ajuste'),
    ]
    INTENCION = [
        ('a_ventas', 'A ventas'),
        ('guardar', 'Guardar'),
        ('otro', 'Otro'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos_stock')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO)
    sucursal_origen = models.ForeignKey(
        Sucursal, null=True, blank=True, on_delete=models.SET_NULL, related_name='movimientos_salida')
    sucursal_destino = models.ForeignKey(
        Sucursal, null=True, blank=True, on_delete=models.SET_NULL, related_name='movimientos_entrada')
    proveedor = models.ForeignKey(Proveedor, null=True, blank=True, on_delete=models.SET_NULL)
    cantidad = models.DecimalField(max_digits=12, decimal_places=0)
    intencion = models.CharField(max_length=20, choices=INTENCION, blank=True)
    nota = models.CharField(max_length=255, blank=True)
    usuario = models.ForeignKey(PerfilUsuario, null=True, on_delete=models.SET_NULL)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de stock'
        verbose_name_plural = 'Movimientos de stock'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.producto} ({self.cantidad})'
