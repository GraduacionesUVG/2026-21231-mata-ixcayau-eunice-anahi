from django import forms

from .models import Sucursal

INPUT_ATTRS = {'class': 'fm-input'}


class SucursalForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ['nombre', 'codigo', 'direccion', 'ciudad', 'tiene_punto_venta']
        widgets = {
            'nombre': forms.TextInput(attrs=INPUT_ATTRS),
            'codigo': forms.TextInput(attrs=INPUT_ATTRS),
            'direccion': forms.TextInput(attrs=INPUT_ATTRS),
            'ciudad': forms.TextInput(attrs=INPUT_ATTRS),
        }
