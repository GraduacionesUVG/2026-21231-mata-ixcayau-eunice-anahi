from django import forms

from .models import Proveedor

INPUT_ATTRS = {'class': 'fm-input'}


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'codigo', 'telefono']
        widgets = {
            'nombre': forms.TextInput(attrs=INPUT_ATTRS),
            'codigo': forms.TextInput(attrs={**INPUT_ATTRS, 'maxlength': 4, 'style': 'text-transform:uppercase;'}),
            'telefono': forms.TextInput(attrs=INPUT_ATTRS),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

    def clean_codigo(self):
        codigo = (self.cleaned_data.get('codigo') or '').strip().upper()
        if not codigo:
            raise forms.ValidationError('Indica un código de proveedor.')
        if not codigo.isalpha():
            raise forms.ValidationError('El código solo puede tener letras (sin números ni símbolos).')
        if len(codigo) > 4:
            raise forms.ValidationError('El código puede tener como máximo 4 letras.')
        return codigo

    def clean(self):
        cleaned = super().clean()
        codigo = cleaned.get('codigo')
        if codigo and self.empresa is not None:
            existe = Proveedor.objects.filter(empresa=self.empresa, codigo=codigo)
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                self.add_error('codigo', f'Ya existe un proveedor con el código "{codigo}".')
        return cleaned
