from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return self.nome

class OrdemServico(models.Model):
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('em_andamento', 'Em andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    nome_cliente = models.CharField(max_length=200)
    email_cliente = models.EmailField(blank=True, null=True)
    descricao = models.TextField()
    data_abertura = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aberta')

    # ----- NOVOS CAMPOS (adicionados) -----
    # identificação / vínculo com pedido do sistema legado
    idpedido = models.IntegerField(null=True, blank=True)

    # infos do objeto / veículo
    placa = models.CharField(max_length=32, null=True, blank=True)
    descricao_objeto = models.CharField(max_length=200, null=True, blank=True)
    localizacao_obj = models.CharField(max_length=100, null=True, blank=True)

    # previsões / horários
    previsao_data = models.DateField(null=True, blank=True)
    previsao_hora = models.TimeField(null=True, blank=True)

    # responsáveis (podem ser ids ou nomes dependendo do seu fluxo)
    idresponsavel = models.IntegerField(null=True, blank=True)
    idusuario = models.IntegerField(null=True, blank=True)
    idmecanico = models.IntegerField(null=True, blank=True)

    # textos longos do sistema legado
    defeito = models.TextField(null=True, blank=True)
    pertencentes = models.TextField(null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)

    # financeiro
    entrada = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    # campos adicionais vistos na sua tela
    proprietario = models.CharField(max_length=120, null=True, blank=True)
    cond_pagto = models.CharField(max_length=50, null=True, blank=True)
    natureza = models.CharField(max_length=80, null=True, blank=True)
    vendedor = models.CharField(max_length=120, null=True, blank=True)
    tecnico = models.CharField(max_length=120, null=True, blank=True)

    # timestamps de controle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'OS #{self.id} - {self.nome_cliente}'