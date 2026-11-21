from django.db import models

from core.models import Empresa


class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='clientes')
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=30, blank=True)
    notas = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def telefono_whatsapp(self):
        """Solo dígitos - wa.me no acepta espacios, guiones ni el '+' del código de país."""
        return ''.join(ch for ch in self.telefono if ch.isdigit())
