from django import forms
from django.forms import formset_factory

from clientes.models import Cliente
from inventario.models import Stock
from productos.models import Producto

INPUT_ATTRS = {'class': 'fm-input'}


class VentaForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(), required=False, label='Cliente',
        empty_label='Anónimo', widget=forms.Select(attrs=INPUT_ATTRS))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, activo=True)


OTRO = 'otro'


class ProductoOtroSelect(forms.Select):
    """Select de producto (+ opción "Otro") que anota data-stock, los 3
    niveles de precio y las categorías en cada <option>, para que el JS de
    la plantilla muestre el disponible, sugiera/informe los precios y
    permita buscar/filtrar por categoría sin recargar la página."""

    def __init__(self, *args, stock_map=None, precio_map=None, precio_mp_map=None,
                 precio_mg_map=None, categorias_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock_map = stock_map or {}
        self.precio_map = precio_map or {}
        self.precio_mp_map = precio_mp_map or {}
        self.precio_mg_map = precio_mg_map or {}
        self.categorias_map = categorias_map or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value in self.stock_map:
            option['attrs']['data-stock'] = str(self.stock_map[value])
        if value in self.precio_map:
            option['attrs']['data-precio'] = str(self.precio_map[value])
        if value in self.precio_mp_map:
            option['attrs']['data-precio-mp'] = str(self.precio_mp_map[value])
        if value in self.precio_mg_map:
            option['attrs']['data-precio-mg'] = str(self.precio_mg_map[value])
        if value in self.categorias_map:
            option['attrs']['data-categorias'] = ','.join(str(c) for c in self.categorias_map[value])
        return option


class LineaVentaForm(forms.Form):
    OTRO = OTRO

    producto = forms.ChoiceField(label='Producto', required=False, widget=forms.Select(attrs=INPUT_ATTRS))
    descripcion_libre = forms.CharField(
        label='Descripción', required=False, widget=forms.TextInput(attrs=INPUT_ATTRS))
    cantidad = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '1'}))
    precio_unitario = forms.DecimalField(
        label='Precio', required=False, min_value=0,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01'}))

    def __init__(self, *args, empresa=None, sucursal=None, stock_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sucursal = sucursal
        self._productos = {}
        stock_map = stock_map or {}

        choices = [('', '---------')]
        precio_map = {}
        precio_mp_map = {}
        precio_mg_map = {}
        categorias_map = {}
        if empresa is not None:
            for p in Producto.objects.filter(empresa=empresa, activo=True).prefetch_related('categorias'):
                self._productos[str(p.id)] = p
                choices.append((str(p.id), f'{p.codigo} - {p.nombre}'))
                precio_map[str(p.id)] = p.precio_venta
                precio_mp_map[str(p.id)] = p.precio_mayorista_pequeno
                precio_mg_map[str(p.id)] = p.precio_mayorista_grande
                categorias_map[str(p.id)] = [c.id for c in p.categorias.all()]
        choices.append((OTRO, 'Otro (sin registrar)'))

        widget_stock_map = {str(pid): cantidad for pid, cantidad in stock_map.items()}
        widget = ProductoOtroSelect(
            attrs=INPUT_ATTRS, stock_map=widget_stock_map, precio_map=precio_map,
            precio_mp_map=precio_mp_map, precio_mg_map=precio_mg_map, categorias_map=categorias_map)
        widget.choices = choices
        self.fields['producto'].choices = choices
        self.fields['producto'].widget = widget

    def clean(self):
        cleaned = super().clean()
        seleccion = cleaned.get('producto')
        descripcion = cleaned.get('descripcion_libre')
        cantidad = cleaned.get('cantidad')
        precio = cleaned.get('precio_unitario')

        if not any([seleccion, descripcion, cantidad, precio]):
            return cleaned  # fila vacía, se ignora

        if not seleccion:
            raise forms.ValidationError('Elige un producto o "Otro".')
        if not cantidad:
            raise forms.ValidationError('Indica una cantidad.')

        if seleccion == OTRO:
            if not descripcion:
                raise forms.ValidationError('Describe el producto.')
            cleaned['producto_obj'] = None
        else:
            producto = self._productos.get(seleccion)
            if not producto:
                raise forms.ValidationError('Producto inválido.')
            stock = Stock.objects.filter(sucursal=self.sucursal, producto=producto).first()
            disponible = stock.cantidad if stock else 0
            if cantidad > disponible:
                raise forms.ValidationError(
                    f'Solo hay {disponible} unidades de {producto.nombre} en esta sucursal.')
            cleaned['producto_obj'] = producto
            if not precio:
                # sin precio propio, usa el precio registrado del producto
                cleaned['precio_unitario'] = producto.precio_venta

        return cleaned


# 1 fila inicial; el botón "+ Agregar otro producto" de la plantilla añade
# más clonando formset.empty_form por JS.
LineaVentaFormSet = formset_factory(LineaVentaForm, extra=1)
