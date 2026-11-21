from django.urls import path

from . import views

app_name = 'pedidos'

urlpatterns = [
    path('', views.lista_pedidos, name='lista'),
    path('nuevo/', views.crear_pedido, name='crear'),
    path('pendientes-por-proveedor/pdf/', views.pendientes_por_proveedor_pdf, name='pendientes_por_proveedor_pdf'),
    path('<int:pk>/', views.detalle_pedido, name='detalle'),
    path('<int:pk>/completar/', views.completar_pedido, name='completar'),
    path('<int:pk>/pasar-a-venta/', views.convertir_a_venta, name='convertir_a_venta'),
    path('<int:pk>/pdf/', views.pedido_pdf, name='pedido_pdf'),
    path('linea/<int:pk>/actualizar/', views.actualizar_linea, name='actualizar_linea'),
]
