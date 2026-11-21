from django.conf import settings
from django.db import models


class Empresa(models.Model):
    TIPO_NEGOCIO = [
        ('retail', 'Tienda / Retail'),
        ('servicios', 'Servicios'),
        ('taller', 'Taller / Manufactura'),
        ('otro', 'Otro'),
    ]
    COLOR_TEMA = [
        ('purple', 'Violeta'),
        ('blue', 'Azul'),
        ('green', 'Verde'),
        ('teal', 'Turquesa'),
        ('orange', 'Naranja'),
        ('red', 'Rojo'),
        ('dark', 'Gris oscuro'),
    ]
    COLOR_HEX = {
        'purple': '#714B67', 'blue': '#1F6FEB', 'green': '#2E7D32',
        'teal': '#00897B', 'orange': '#EF6C00', 'red': '#C62828', 'dark': '#37474F',
    }

    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=120, blank=True)
    tipo_negocio = models.CharField(max_length=20, choices=TIPO_NEGOCIO, blank=True)
    color_tema = models.CharField(max_length=20, choices=COLOR_TEMA, default='purple')
    logo_url = models.URLField(blank=True, help_text='Ruta del archivo en media/.')

    # controla qué tarjetas se muestran activas en el panel
    modulo_clientes = models.BooleanField(default=True)
    modulo_productos = models.BooleanField(default=True)
    modulo_inventario = models.BooleanField(default=True)
    modulo_ventas = models.BooleanField(default=True)
    modulo_reportes = models.BooleanField(default=True)
    modulo_codigo_barras = models.BooleanField(default=True)
    modulo_pedidos = models.BooleanField(default=True)

    onboarding_completo = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre

    @property
    def color_hex(self):
        return self.COLOR_HEX.get(self.color_tema, self.COLOR_HEX['purple'])


class PerfilUsuario(models.Model):
    """Datos de negocio (rol, empresa, sucursal, PIN) del usuario de Django auth."""
    ROLES = [
        ('dueno', 'Dueño'),
        ('vendedor', 'Vendedor'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    nombre = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField()
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios')
    rol = models.CharField(max_length=20, choices=ROLES, default='dueno')
    sucursal = models.ForeignKey(
        'sucursales.Sucursal', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='vendedores',
        help_text='Solo aplica a usuarios con rol Vendedor.')
    activo = models.BooleanField(default=True, help_text='En False, pierde el acceso de inmediato.')
    pin = models.CharField(max_length=128, blank=True, help_text='Hash del PIN de 4 dígitos.')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def __str__(self):
        return f'{self.nombre or self.email} ({self.get_rol_display()})'
