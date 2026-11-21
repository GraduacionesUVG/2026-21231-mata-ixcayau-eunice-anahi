from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.lista_vendedores, name='lista'),
    path('nuevo/', views.crear_vendedor, name='crear'),
    path('<int:pk>/toggle/', views.toggle_vendedor, name='toggle'),
    path('operador/', views.seleccionar_operador, name='seleccionar_operador'),
    path('operador/salir/', views.cerrar_operador, name='cerrar_operador'),
]
