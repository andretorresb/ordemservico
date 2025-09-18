from django.contrib import admin
from .models import Cliente, OrdemServico

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'email', 'telefone')
    search_fields = ('nome', 'email')

@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_cliente', 'status', 'data_abertura')
    list_filter = ('status',)
    search_fields = ('nome_cliente', 'descricao')
