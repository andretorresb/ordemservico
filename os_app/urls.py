from django.urls import path
from . import views

app_name = 'os_app'

urlpatterns = [
    path('abrir/', views.abrir_os, name='abrir_os'),
    path('sucesso/<int:pk>/', views.sucesso, name='sucesso'),
    path('', views.listar_os, name='listar_os'),
    path('editar/<int:pk>/', views.editar_os, name='editar_os'),
    path('remover/<int:pk>/', views.remover_os, name='remover_os'),
]
