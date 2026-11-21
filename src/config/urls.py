from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # /admin/ y el login de dueños/vendedores usan el mismo auth nativo de
    # Django; /admin/ requiere superusuario (createsuperuser), el resto usa
    # PerfilUsuario para rol/empresa/sucursal.
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('sucursales/', include('sucursales.urls')),
    path('productos/', include('productos.urls')),
    path('proveedores/', include('proveedores.urls')),
    path('inventario/', include('inventario.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('ventas/', include('ventas.urls')),
    path('clientes/', include('clientes.urls')),
    path('reportes/', include('reportes.urls')),
    path('pedidos/', include('pedidos.urls')),
]

if settings.DEBUG:
    # en producción esto lo serviría nginx/whitenoise, no Django
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
