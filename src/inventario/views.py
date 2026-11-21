from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from core.decorators import login_activo_required
from core.services import get_perfil
from sucursales.models import Sucursal

from .forms import EntradaMercaderiaForm, LineaEntradaFormSet, TransferenciaForm
from .models import MovimientoStock, Stock
from .services import registrar_entrada


@login_activo_required
def dashboard_sucursal(request):
    perfil = get_perfil(request)
    sucursales = Sucursal.objects.filter(empresa=perfil.empresa)

    if perfil.rol == 'vendedor' and perfil.sucursal_id:
        sucursales = sucursales.filter(id=perfil.sucursal_id)
        sucursal_actual = perfil.sucursal
    else:
        sucursal_id = request.GET.get('sucursal')
        sucursal_actual = sucursales.filter(id=sucursal_id).first() if sucursal_id else sucursales.first()

    stock = (
        Stock.objects.filter(sucursal=sucursal_actual).select_related('producto')
        if sucursal_actual else Stock.objects.none()
    )

    return render(request, 'inventario/dashboard.html', {
        'perfil': perfil,
        'sucursales': sucursales,
        'sucursal_actual': sucursal_actual,
        'stock': stock,
    })


@login_activo_required
def reporte_consolidado(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver el inventario consolidado.')
        return redirect('inventario:dashboard')

    stock = (
        Stock.objects.filter(sucursal__empresa=perfil.empresa)
        .select_related('producto', 'sucursal')
        .order_by('producto__nombre', 'sucursal__nombre')
    )
    return render(request, 'inventario/consolidado.html', {'perfil': perfil, 'stock': stock})


@login_activo_required
def entrada_mercaderia(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede registrar entradas de mercadería.')
        return redirect('inventario:dashboard')

    form = EntradaMercaderiaForm(request.POST or None, empresa=perfil.empresa)
    formset = LineaEntradaFormSet(request.POST or None, form_kwargs={'empresa': perfil.empresa})

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        lineas = [
            f.cleaned_data for f in formset
            if f.cleaned_data.get('producto') and f.cleaned_data.get('cantidad')
        ]
        if not lineas:
            messages.error(request, 'Agrega al menos un producto con cantidad.')
        else:
            sucursal_destino = form.cleaned_data['sucursal_destino']
            with transaction.atomic():
                for linea in lineas:
                    registrar_entrada(
                        empresa=perfil.empresa, producto=linea['producto'], sucursal=sucursal_destino,
                        cantidad=linea['cantidad'], usuario=perfil,
                        proveedor=form.cleaned_data['proveedor'], nota=form.cleaned_data.get('nota', ''),
                    )
            messages.success(request, 'Entrada de mercadería registrada.')
            return redirect('inventario:dashboard')

    return render(request, 'inventario/entrada_mercaderia.html', {'form': form, 'formset': formset})


@login_activo_required
def transferencia(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede transferir inventario.')
        return redirect('inventario:dashboard')

    form = TransferenciaForm(request.POST or None, empresa=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        origen = form.cleaned_data['sucursal_origen']
        destino = form.cleaned_data['sucursal_destino']
        producto = form.cleaned_data['producto']
        cantidad = form.cleaned_data['cantidad']

        with transaction.atomic():
            stock_origen = Stock.objects.select_for_update().get(sucursal=origen, producto=producto)
            stock_origen.cantidad -= cantidad
            stock_origen.save(update_fields=['cantidad'])

            stock_destino, _ = Stock.objects.get_or_create(
                sucursal=destino, producto=producto, defaults={'cantidad': Decimal('0')})
            stock_destino.cantidad += cantidad
            stock_destino.save(update_fields=['cantidad'])

            MovimientoStock.objects.create(
                empresa=perfil.empresa, producto=producto, tipo='transferencia',
                sucursal_origen=origen, sucursal_destino=destino, cantidad=cantidad,
                intencion=form.cleaned_data['intencion'], nota=form.cleaned_data.get('nota', ''),
                usuario=perfil,
            )
        messages.success(request, f'Se transfirieron {cantidad} unidades de {producto.nombre} a {destino.nombre}.')
        return redirect('inventario:dashboard')

    return render(request, 'inventario/transferencia.html', {'form': form})


@login_activo_required
def historial_movimientos(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver el historial de movimientos.')
        return redirect('inventario:dashboard')

    movimientos = (
        MovimientoStock.objects.filter(empresa=perfil.empresa, tipo__in=['entrada', 'transferencia'])
        .select_related('producto', 'sucursal_origen', 'sucursal_destino', 'proveedor', 'usuario')
        .order_by('-creado_en')[:200]
    )
    return render(request, 'inventario/historial.html', {'movimientos': movimientos})


@login_activo_required
@require_http_methods(['POST'])
def actualizar_minimo(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede configurar el mínimo de stock.')
        return redirect('inventario:dashboard')

    stock = get_object_or_404(Stock, pk=pk, sucursal__empresa=perfil.empresa)
    try:
        nuevo_minimo = Decimal(request.POST.get('stock_minimo', '0'))
        if nuevo_minimo < 0 or nuevo_minimo % 1 != 0:
            raise InvalidOperation
    except InvalidOperation:
        messages.error(request, 'El mínimo debe ser un número entero, mayor o igual a 0.')
    else:
        stock.stock_minimo = nuevo_minimo
        stock.save(update_fields=['stock_minimo'])
        messages.success(request, f'Mínimo de {stock.producto.nombre} en {stock.sucursal.nombre} actualizado.')

    return redirect(f"{reverse('inventario:dashboard')}?sucursal={stock.sucursal_id}")
