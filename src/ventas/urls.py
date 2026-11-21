from django.urls import path

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.lista_ventas, name='lista'),
    path('cierre/', views.cierre_diario, name='cierre_diario'),
    path('nueva/', views.registrar_venta, name='registrar'),
    path('<int:pk>/', views.detalle_venta, name='detalle'),
    path('<int:pk>/pdf/', views.detalle_venta_pdf, name='detalle_pdf'),
]
