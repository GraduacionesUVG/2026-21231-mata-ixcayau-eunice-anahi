from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('onboarding/marca/', views.onboarding_marca, name='onboarding_marca'),
    path('onboarding/negocio/', views.onboarding_negocio, name='onboarding_negocio'),
    path('onboarding/modulos/', views.onboarding_modulos, name='onboarding_modulos'),
    path('', views.panel, name='panel'),
    path('empresa/', views.editar_empresa, name='editar_empresa'),
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    path('perfil/editar/', views.editar_datos_personales, name='editar_datos_personales'),
]
