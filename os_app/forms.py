# os_app/forms.py
from django import forms

class OrdemServicoForm(forms.Form):
    descricaoobjeto = forms.CharField(max_length=300, required=False, label='Descrição do objeto')
    defeito = forms.CharField(widget=forms.Textarea(attrs={'rows':4}), required=False, label='Defeito')
    idusuario = forms.IntegerField(required=False, label='Usuário')

    # ----- CAMPOS ADICIONAIS (mantidos) -----
    placa = forms.CharField(max_length=32, required=False, label='Placa')
    localizacao = forms.CharField(max_length=100, required=False, label='Localização')

    previsao_data = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Previsão (data)')
    previsao_hora = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}), label='Previsão (hora)')

    pertencentes = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), required=False, label='Pertences')
    observacoes = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), required=False, label='Observações')

    entrada = forms.DecimalField(required=False, max_digits=18, decimal_places=2, label='Entrada (R$)')

    proprietario = forms.CharField(max_length=120, required=False, label='Proprietário')
    cond_pagto = forms.CharField(max_length=50, required=False, label='Condição Pagto')
    natureza = forms.CharField(max_length=80, required=False, label='Natureza')

    vendedor = forms.CharField(max_length=120, required=False, label='Vendedor')
    tecnico = forms.CharField(max_length=120, required=False, label='Técnico')

    # (opcional) campo cliente / contato
    nome_cliente = forms.CharField(max_length=200, required=False, label='Nome / Cliente')
    email_cliente = forms.EmailField(required=False, label='Email do cliente')
