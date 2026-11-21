from django import forms

from proveedores.models import Proveedor
from sucursales.models import Sucursal

from .models import Categoria, Producto

INPUT_ATTRS = {'class': 'fm-input'}


class ProductoForm(forms.ModelForm):
    imagen = forms.ImageField(label='Imagen', required=False)  # se sube a Supabase Storage, no vive en Django
    # se renderiza a mano en la plantilla como buscador con autocompletar
    # (crear.html), no con el widget por defecto - igual queda declarado
    # aquí para que el ModelForm sepa validar/guardar la lista de ids.
    categorias = forms.ModelMultipleChoiceField(
        label='Categorías', queryset=Categoria.objects.none(), required=False,
        widget=forms.SelectMultiple)
    sucursal_inicial = forms.ModelChoiceField(
        label='Agregar a inventario de (opcional)', queryset=Sucursal.objects.none(), required=False,
        widget=forms.Select(attrs=INPUT_ATTRS))
    cantidad_inicial = forms.DecimalField(
        label='Cantidad inicial', required=False, min_value=0, max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '1'}))

    class Meta:
        model = Producto
        fields = [
            'codigo', 'nombre', 'categorias', 'proveedor',
            'precio_venta', 'precio_mayorista_pequeno', 'precio_mayorista_grande',
            'costo', 'unidad', 'activo',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs=INPUT_ATTRS),
            'nombre': forms.TextInput(attrs=INPUT_ATTRS),
            'proveedor': forms.Select(attrs=INPUT_ATTRS),
            'precio_venta': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01'}),
            'precio_mayorista_pequeno': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01'}),
            'precio_mayorista_grande': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01'}),
            'costo': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01'}),
            'unidad': forms.TextInput(attrs=INPUT_ATTRS),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        # obligatorio solo si no se elige proveedor - con proveedor se genera
        # solo (ver clean() y crear_producto/editar_producto)
        self.fields['codigo'].required = False
        if empresa is not None:
            self.fields['categorias'].queryset = Categoria.objects.filter(empresa=empresa)
            self.fields['proveedor'].queryset = Proveedor.objects.filter(empresa=empresa)
            self.fields['sucursal_inicial'].queryset = Sucursal.objects.filter(empresa=empresa)
        if self.instance.pk:
            # al editar un producto ya existente no se vuelve a aplicar inventario inicial
            del self.fields['sucursal_inicial']
            del self.fields['cantidad_inicial']

    def clean(self):
        cleaned = super().clean()

        proveedor = cleaned.get('proveedor')
        codigo = (cleaned.get('codigo') or '').strip()
        cleaned['codigo'] = codigo
        if not proveedor and not codigo:
            self.add_error('codigo', 'Indica un código de producto, o elige un proveedor para generarlo automáticamente.')

        if 'sucursal_inicial' not in self.fields:
            return cleaned
        sucursal = cleaned.get('sucursal_inicial')
        cantidad = cleaned.get('cantidad_inicial')
        if sucursal and not cantidad:
            raise forms.ValidationError('Indica la cantidad inicial para esa sucursal.')
        if cantidad and not sucursal:
            raise forms.ValidationError('Elige la sucursal para ese inventario inicial.')
        return cleaned


class ReporteStockForm(forms.Form):
    categorias = forms.ModelMultipleChoiceField(
        label='Categorías', queryset=Categoria.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple)
    proveedores = forms.ModelMultipleChoiceField(
        label='Proveedores', queryset=Proveedor.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple)
    fecha_desde = forms.DateField(
        label='Desde', widget=forms.DateInput(attrs={**INPUT_ATTRS, 'type': 'date'}))
    fecha_hasta = forms.DateField(
        label='Hasta', widget=forms.DateInput(attrs={**INPUT_ATTRS, 'type': 'date'}))

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields['categorias'].queryset = Categoria.objects.filter(empresa=empresa)
            self.fields['proveedores'].queryset = Proveedor.objects.filter(empresa=empresa)

    def clean(self):
        cleaned = super().clean()
        desde = cleaned.get('fecha_desde')
        hasta = cleaned.get('fecha_hasta')
        if desde and hasta and desde > hasta:
            raise forms.ValidationError('La fecha "desde" no puede ser posterior a la fecha "hasta".')
        return cleaned
