from django.db import models

from core.models import Empresa


class Categoria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'nombre'], name='categoria_unica_por_empresa'),
        ]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos')
    # obligatorio en la práctica (ver ProductoForm.clean) - blank=True solo
    # para que full_clean() no choque cuando se genera a partir del
    # proveedor DESPUÉS de validar el form (ver crear_producto/editar_producto)
    codigo = models.CharField(max_length=30, blank=True)
    nombre = models.CharField(max_length=200)
    categorias = models.ManyToManyField(Categoria, blank=True, related_name='productos')
    proveedor = models.ForeignKey(
        'proveedores.Proveedor', null=True, blank=True, on_delete=models.SET_NULL, related_name='productos')
    precio_venta = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Precio unitario')
    precio_mayorista_pequeno = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Precio mayorista pequeño')
    precio_mayorista_grande = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, verbose_name='Precio mayorista grande')
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    unidad = models.CharField(max_length=20, default='unidad')
    imagen_url = models.URLField(blank=True, help_text='Ruta del archivo en media/.')
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='codigo_unico_por_empresa_producto'),
        ]

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'
