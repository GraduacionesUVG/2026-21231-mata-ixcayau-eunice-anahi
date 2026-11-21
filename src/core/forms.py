from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Empresa

INPUT_ATTRS = {'class': 'fm-input'}


class SignupForm(forms.Form):
    nombre = forms.CharField(label='Tu nombre', max_length=200, widget=forms.TextInput(attrs=INPUT_ATTRS))
    nombre_negocio = forms.CharField(
        label='Nombre de tu negocio', max_length=200,
        widget=forms.TextInput(attrs=INPUT_ATTRS))
    email = forms.EmailField(label='Correo', widget=forms.EmailInput(attrs=INPUT_ATTRS))
    password = forms.CharField(
        label='Contraseña', widget=forms.PasswordInput(attrs=INPUT_ATTRS))
    password2 = forms.CharField(
        label='Confirmar contraseña', widget=forms.PasswordInput(attrs=INPUT_ATTRS))

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)  # usa AUTH_PASSWORD_VALIDATORS
        return password

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') and cleaned_data.get('password2'):
            if cleaned_data['password'] != cleaned_data['password2']:
                self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data


class DatosPersonalesForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=200, widget=forms.TextInput(attrs=INPUT_ATTRS))
    telefono = forms.CharField(
        label='Teléfono', max_length=30, required=False, widget=forms.TextInput(attrs=INPUT_ATTRS))


class LoginForm(forms.Form):
    email = forms.EmailField(label='Correo', widget=forms.EmailInput(attrs=INPUT_ATTRS))
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs=INPUT_ATTRS))


class MarcaForm(forms.ModelForm):
    logo = forms.ImageField(label='Logo', required=False)  # se sube a Supabase Storage, no vive en Django

    class Meta:
        model = Empresa
        fields = ['color_tema']
        widgets = {'color_tema': forms.RadioSelect}


class NegocioForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre', 'direccion', 'ciudad', 'tipo_negocio']
        widgets = {
            'nombre': forms.TextInput(attrs=INPUT_ATTRS),
            'direccion': forms.TextInput(attrs=INPUT_ATTRS),
            'ciudad': forms.TextInput(attrs=INPUT_ATTRS),
            'tipo_negocio': forms.Select(attrs=INPUT_ATTRS),
        }


class EmpresaSettingsForm(forms.ModelForm):
    logo = forms.ImageField(label='Logo', required=False)  # se sube a Supabase Storage, no vive en Django

    class Meta:
        model = Empresa
        fields = ['nombre', 'color_tema', 'modulo_reportes', 'modulo_codigo_barras', 'modulo_pedidos']
        labels = {
            'modulo_reportes': 'Reportes',
            'modulo_codigo_barras': 'Código de barras (imprimir etiquetas y escanear)',
            'modulo_pedidos': 'Planeación de pedidos',
        }
        widgets = {
            'nombre': forms.TextInput(attrs=INPUT_ATTRS),
            'color_tema': forms.RadioSelect,
        }


class ModulosForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'modulo_clientes', 'modulo_productos', 'modulo_inventario',
            'modulo_ventas', 'modulo_reportes',
        ]
