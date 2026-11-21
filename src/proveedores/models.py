from django.core.validators import RegexValidator
from django.db import models

from core.models import Empresa


class Proveedor(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='proveedores')
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(
        max_length=4,
        validators=[RegexValidator(r'^[A-Z]+$', 'Solo letras, sin números ni símbolos.')],
        help_text='Hasta 4 letras. Se usa como prefijo del código de los productos de este proveedor.',
    )
    telefono = models.CharField(max_length=30, blank=True)
    # siguiente número a usar al generar el código de un producto de este
    # proveedor (código + número) - ver productos/services.py
    contador_productos = models.PositiveIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='codigo_unico_por_empresa_proveedor'),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        # por si algo guarda directo por ORM sin pasar por el form (ej. un
        # script) - el código siempre queda en mayúsculas
        if self.codigo:
            self.codigo = self.codigo.upper()
        super().save(*args, **kwargs)

    @property
    def telefono_whatsapp(self):
        """Solo dígitos - wa.me no acepta espacios, guiones ni el '+' del código de país."""
        return ''.join(ch for ch in self.telefono if ch.isdigit())
