from django.urls import path
from . import views

app_name = 'os_app'

urlpatterns = [
    path('abrir/', views.abrir_os, name='abrir_os'),
    path('sucesso/<int:pk>/', views.sucesso, name='sucesso'),
    path('', views.listar_os, name='listar_os'),
    path('editar/<int:pk>/', views.editar_os, name='editar_os'),
    path('cancelar/<int:pk>/', views.cancelar_os, name='cancelar_os'),

    # APIs AJAX para objetos (usadas pelo JS do formulário)
    path('api/objetos/por-proprietario/<int:cliente_id>/', views.objetos_por_proprietario, name='api_objetos_por_proprietario'),
    path('api/objetos/<int:pk>/', views.objeto_detail, name='api_objeto_detail'),
]
