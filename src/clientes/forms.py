from django import forms

from .models import Cliente

INPUT_ATTRS = {'class': 'fm-input'}


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'notas', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs=INPUT_ATTRS),
            'telefono': forms.TextInput(attrs=INPUT_ATTRS),
            'notas': forms.Textarea(attrs={**INPUT_ATTRS, 'rows': 3}),
        }
