from django import forms
from django.forms import formset_factory

from productos.models import Producto
from proveedores.models import Proveedor
from sucursales.models import Sucursal

from .models import MovimientoStock, Stock

INPUT_ATTRS = {'class': 'fm-input'}


class EntradaMercaderiaForm(forms.Form):
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.none(), widget=forms.Select(attrs=INPUT_ATTRS))
    sucursal_destino = forms.ModelChoiceField(
        queryset=Sucursal.objects.none(), label='Recibido en', widget=forms.Select(attrs=INPUT_ATTRS))
    nota = forms.CharField(label='Referencia / nota', required=False, widget=forms.TextInput(attrs=INPUT_ATTRS))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(empresa=empresa)
            self.fields['sucursal_destino'].queryset = Sucursal.objects.filter(empresa=empresa)


class LineaEntradaForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.none(), required=False, widget=forms.Select(attrs=INPUT_ATTRS))
    cantidad = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '1'}))
    costo = forms.DecimalField(
        required=False, min_value=0, widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01'}))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields['producto'].queryset = Producto.objects.filter(empresa=empresa, activo=True)


# 1 fila inicial; el botón "+ Agregar otro producto" de la plantilla añade
# más clonando formset.empty_form por JS. Las vacías se ignoran al guardar.
LineaEntradaFormSet = formset_factory(LineaEntradaForm, extra=1)


class TransferenciaForm(forms.Form):
    sucursal_origen = forms.ModelChoiceField(queryset=Sucursal.objects.none(), widget=forms.Select(attrs=INPUT_ATTRS))
    sucursal_destino = forms.ModelChoiceField(queryset=Sucursal.objects.none(), widget=forms.Select(attrs=INPUT_ATTRS))
    producto = forms.ModelChoiceField(queryset=Producto.objects.none(), widget=forms.Select(attrs=INPUT_ATTRS))
    cantidad = forms.DecimalField(
        min_value=0, max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '1'}))
    intencion = forms.ChoiceField(choices=MovimientoStock.INTENCION, widget=forms.Select(attrs=INPUT_ATTRS))
    nota = forms.CharField(required=False, widget=forms.TextInput(attrs=INPUT_ATTRS))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa is not None:
            sucursales = Sucursal.objects.filter(empresa=empresa)
            self.fields['sucursal_origen'].queryset = sucursales
            self.fields['sucursal_destino'].queryset = sucursales
            self.fields['producto'].queryset = Producto.objects.filter(empresa=empresa, activo=True)

    def clean(self):
        cleaned = super().clean()
        origen = cleaned.get('sucursal_origen')
        destino = cleaned.get('sucursal_destino')
        producto = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')

        if origen and destino and origen == destino:
            raise forms.ValidationError('Origen y destino deben ser sucursales distintas.')

        if origen and producto and cantidad:
            stock = Stock.objects.filter(sucursal=origen, producto=producto).first()
            disponible = stock.cantidad if stock else 0
            if cantidad > disponible:
                raise forms.ValidationError(
                    f'Solo hay {disponible} unidades de {producto.nombre} en {origen.nombre}.')

        return cleaned
