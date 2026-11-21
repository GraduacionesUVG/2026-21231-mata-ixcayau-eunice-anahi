from django.urls import path

from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.dashboard_sucursal, name='dashboard'),
    path('consolidado/', views.reporte_consolidado, name='consolidado'),
    path('entrada/', views.entrada_mercaderia, name='entrada'),
    path('transferencia/', views.transferencia, name='transferencia'),
    path('historial/', views.historial_movimientos, name='historial'),
    path('stock/<int:pk>/minimo/', views.actualizar_minimo, name='actualizar_minimo'),
]
