# os_app/forms.py
from django import forms

class OrdemServicoForm(forms.Form):
    descricaoobjeto = forms.CharField(max_length=300, required=False, label='Descrição do objeto')
    defeito = forms.CharField(widget=forms.Textarea(attrs={'rows':4}), required=False, label='Defeito')
    idusuario = forms.IntegerField(required=False, label='Usuário')