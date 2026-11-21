from django.urls import path

from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.lista_productos, name='lista'),
    path('nuevo/', views.crear_producto, name='crear'),
    path('<int:pk>/editar/', views.editar_producto, name='editar'),
    path('<int:pk>/detalle/', views.detalle_producto_json, name='detalle_json'),
    path('<int:pk>/historial-stock/', views.historial_stock_json, name='historial_stock_json'),
    path('etiquetas/zpl/', views.generar_etiquetas_zpl, name='etiquetas_zpl'),
    path('categorias/nueva/', views.crear_categoria, name='crear_categoria'),
    path('reporte/', views.reporte_productos, name='reporte'),
    path('reporte/pdf/', views.reporte_productos_pdf, name='reporte_pdf'),
]
