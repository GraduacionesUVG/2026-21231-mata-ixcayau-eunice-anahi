from django.urls import path

from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard_reportes, name='dashboard'),
    path('pdf/', views.dashboard_reportes_pdf, name='dashboard_pdf'),
]
