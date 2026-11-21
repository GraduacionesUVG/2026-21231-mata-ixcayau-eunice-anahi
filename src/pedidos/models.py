from django.db import models

from clientes.models import Cliente
from core.models import Empresa, PerfilUsuario
from productos.models import Producto
from sucursales.models import Sucursal


class Pedido(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='pedidos')
    cliente = models.ForeignKey(
        Cliente, null=True, blank=True, on_delete=models.SET_NULL, related_name='pedidos',
        help_text='Vacío = pedido sin cliente asociado (solo para reabastecer inventario).')
    # de dónde sale/a dónde entra el inventario si este pedido se completa y
    # se pasa a venta - ver pedidos/views.py:convertir_a_venta
    sucursal = models.ForeignKey(
        Sucursal, null=True, blank=True, on_delete=models.SET_NULL, related_name='pedidos')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    creado_por = models.ForeignKey(PerfilUsuario, null=True, on_delete=models.SET_NULL, related_name='pedidos_creados')
    creado_en = models.DateTimeField(auto_now_add=True)
    completado_en = models.DateTimeField(null=True, blank=True)
    # si este pedido se pasó a venta, queda enlazado aquí - evita pasarlo dos veces
    venta_generada = models.OneToOneField(
        'ventas.Venta', null=True, blank=True, on_delete=models.SET_NULL, related_name='pedido_origen')

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-creado_en']

    def __str__(self):
        return f'Pedido #{self.pk}'


class PedidoLinea(models.Model):
    RECIBIDO_CHOICES = [
        ('no', 'No recibido'),
        ('parcial', 'Recibido parcial'),
        ('completo', 'Recibido completo'),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    # SET_NULL (no CASCADE): si el producto se borra, la línea del pedido
    # (y su historial de fechas) queda como registro, igual que en VentaLinea.
    producto = models.ForeignKey(Producto, null=True, on_delete=models.SET_NULL, related_name='lineas_pedido')
    cantidad = models.DecimalField(max_digits=12, decimal_places=0)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    ya_pedido = models.BooleanField(default=False)
    ya_pedido_en = models.DateTimeField(null=True, blank=True)

    recibido = models.CharField(max_length=20, choices=RECIBIDO_CHOICES, default='no')
    recibido_en = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Línea de pedido'
        verbose_name_plural = 'Líneas de pedido'
        ordering = ['id']

    def __str__(self):
        return f'{self.producto} x {self.cantidad}'

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
