from django import forms
from django.contrib.auth.password_validation import validate_password

from sucursales.models import Sucursal

INPUT_ATTRS = {'class': 'fm-input'}


class VendedorForm(forms.Form):
    nombre = forms.CharField(label='Nombre completo', widget=forms.TextInput(attrs=INPUT_ATTRS))
    email = forms.EmailField(label='Correo (usuario de acceso)', widget=forms.EmailInput(attrs=INPUT_ATTRS))
    password = forms.CharField(
        label='Contraseña temporal', widget=forms.PasswordInput(attrs=INPUT_ATTRS))
    sucursal = forms.ModelChoiceField(
        queryset=Sucursal.objects.none(), label='Sucursal asignada', widget=forms.Select(attrs=INPUT_ATTRS))
    pin = forms.CharField(
        label='PIN (4 dígitos)', min_length=4, max_length=4,
        widget=forms.TextInput(attrs={**INPUT_ATTRS, 'inputmode': 'numeric'}),
        help_text='Para identificarse rápido en un dispositivo compartido de la sucursal.')

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields['sucursal'].queryset = Sucursal.objects.filter(empresa=empresa)

    def clean_pin(self):
        pin = self.cleaned_data['pin']
        if not pin.isdigit():
            raise forms.ValidationError('El PIN debe ser solo números.')
        return pin

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)  # usa AUTH_PASSWORD_VALIDATORS
        return password
