# os_app/forms.py
from django import forms

class OrdemServicoForm(forms.Form):
    # campos relacionados ao objeto / descrição
    idobjeto = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        label='ID Objeto'
    )
    tipo_objeto = forms.CharField(
        max_length=80, required=False, label='Tipo',
        widget=forms.TextInput(attrs={'class':'form-control', 'id':'id_tipo_objeto'})
    )
    marca = forms.CharField(
        max_length=80, required=False, label='Marca',
        widget=forms.TextInput(attrs={'class':'form-control', 'id':'id_marca'})
    )
    modelo = forms.CharField(
        max_length=120, required=False, label='Modelo',
        widget=forms.TextInput(attrs={'class':'form-control', 'id':'id_modelo'})
    )

    descricaoobjeto = forms.CharField(
        max_length=300, required=False, label='Descrição do objeto',
        widget=forms.TextInput(attrs={'class':'form-control', 'id':'id_descricaoobjeto'})
    )
    defeito = forms.CharField(
        widget=forms.Textarea(attrs={'rows':4, 'class':'form-control'}),
        required=False, label='Defeito'
    )
    idusuario = forms.IntegerField(
        required=False, label='Usuário',
        widget=forms.NumberInput(attrs={'class':'form-control'})
    )

    placa = forms.CharField(
        max_length=32, required=False, label='Placa',
        widget=forms.TextInput(attrs={'class':'form-control', 'id':'id_placa'})
    )
    localizacao = forms.CharField(
        max_length=100, required=False, label='Localização',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )

    previsao_data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date','class':'form-control'}),
        label='Previsão (data)'
    )
    previsao_hora = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time','class':'form-control'}),
        label='Previsão (hora)'
    )

    pertencentes = forms.CharField(
        widget=forms.Textarea(attrs={'rows':2,'class':'form-control'}),
        required=False, label='Pertences'
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows':2,'class':'form-control'}),
        required=False, label='Observações'
    )

    entrada = forms.DecimalField(
        required=False, max_digits=18, decimal_places=2, label='Entrada (R$)',
        widget=forms.NumberInput(attrs={'class':'form-control','step':'0.01'})
    )

    proprietario = forms.CharField(
        max_length=120, required=False, label='Proprietário',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    cond_pagto = forms.CharField(
        max_length=50, required=False, label='Condição Pagto',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    natureza = forms.CharField(
        max_length=80, required=False, label='Natureza',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )

    vendedor = forms.CharField(
        max_length=120, required=False, label='Vendedor',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    tecnico = forms.CharField(
        max_length=120, required=False, label='Técnico',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )

    nome_cliente = forms.CharField(
        max_length=200, required=False, label='Nome / Cliente',
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    email_cliente = forms.EmailField(
        required=False, label='Email do cliente',
        widget=forms.EmailInput(attrs={'class':'form-control'})
    )
