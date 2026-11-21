from django import forms
from django.forms import formset_factory

from clientes.models import Cliente
from productos.models import Producto
from sucursales.models import Sucursal

INPUT_ATTRS = {'class': 'fm-input'}


class PedidoForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(), required=False, label='Cliente',
        empty_label='Sin cliente', widget=forms.Select(attrs=INPUT_ATTRS))
    sucursal = forms.ModelChoiceField(
        queryset=Sucursal.objects.none(), label='Sucursal',
        help_text='De dónde sale/entra el inventario si este pedido se completa y se pasa a venta.',
        widget=forms.Select(attrs=INPUT_ATTRS))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, activo=True)
            self.fields['sucursal'].queryset = Sucursal.objects.filter(empresa=empresa)


class ProductoSelect(forms.Select):
    """Select de producto que anota las categorías en cada <option>, para
    que el buscador de la plantilla pueda filtrar por categoría sin
    recargar la página (mismo patrón que ventas/forms.py)."""

    def __init__(self, *args, categorias_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.categorias_map = categorias_map or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value in self.categorias_map:
            option['attrs']['data-categorias'] = ','.join(str(c) for c in self.categorias_map[value])
        return option


class PedidoLineaForm(forms.Form):
    producto = forms.ChoiceField(label='Producto', required=False, widget=forms.Select(attrs=INPUT_ATTRS))
    cantidad = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '1'}))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._productos = {}

        choices = [('', '---------')]
        categorias_map = {}
        if empresa is not None:
            for p in Producto.objects.filter(empresa=empresa, activo=True).prefetch_related('categorias'):
                self._productos[str(p.id)] = p
                choices.append((str(p.id), f'{p.codigo} - {p.nombre}'))
                categorias_map[str(p.id)] = [c.id for c in p.categorias.all()]

        widget = ProductoSelect(attrs=INPUT_ATTRS, categorias_map=categorias_map)
        widget.choices = choices
        self.fields['producto'].choices = choices
        self.fields['producto'].widget = widget

    def clean(self):
        cleaned = super().clean()
        seleccion = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')

        if not seleccion and not cantidad:
            return cleaned  # fila vacía, se ignora

        if not seleccion:
            raise forms.ValidationError('Elige un producto.')
        if not cantidad:
            raise forms.ValidationError('Indica una cantidad.')

        producto = self._productos.get(seleccion)
        if not producto:
            raise forms.ValidationError('Producto inválido.')
        cleaned['producto_obj'] = producto
        return cleaned


# 1 fila inicial; el botón "+ Agregar otro producto" de la plantilla añade
# más clonando formset.empty_form por JS (mismo patrón que ventas).
PedidoLineaFormSet = formset_factory(PedidoLineaForm, extra=1)
