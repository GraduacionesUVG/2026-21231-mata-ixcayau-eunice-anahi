from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.decorators import login_activo_required, modulo_requerido
from core.services import get_perfil
from inventario.services import registrar_entrada, registrar_salida
from productos.models import Categoria
from ventas.models import Venta, VentaLinea

from .forms import PedidoForm, PedidoLineaFormSet
from .models import Pedido, PedidoLinea
from .reportes import generar_pedido_pdf, generar_pendientes_por_proveedor_pdf


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
def lista_pedidos(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver los pedidos.')
        return redirect('core:panel')

    pedidos = (
        Pedido.objects.filter(empresa=perfil.empresa)
        .select_related('cliente')
        .prefetch_related('lineas')
    )
    return render(request, 'pedidos/lista.html', {'pedidos': pedidos, 'perfil': perfil})


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
def crear_pedido(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede crear pedidos.')
        return redirect('pedidos:lista')

    pedido_form = PedidoForm(request.POST or None, empresa=perfil.empresa)
    formset = PedidoLineaFormSet(request.POST or None, form_kwargs={'empresa': perfil.empresa})

    if request.method == 'POST' and pedido_form.is_valid() and formset.is_valid():
        lineas = [f.cleaned_data for f in formset if f.cleaned_data.get('producto_obj')]
        if not lineas:
            messages.error(request, 'Agrega al menos un producto al pedido.')
        else:
            with transaction.atomic():
                pedido = Pedido.objects.create(
                    empresa=perfil.empresa, cliente=pedido_form.cleaned_data.get('cliente'),
                    sucursal=pedido_form.cleaned_data['sucursal'], creado_por=perfil)
                for linea in lineas:
                    producto = linea['producto_obj']
                    PedidoLinea.objects.create(
                        pedido=pedido, producto=producto, cantidad=linea['cantidad'],
                        precio_unitario=producto.precio_venta,
                    )
            messages.success(request, f'Pedido #{pedido.pk} creado.')
            return redirect('pedidos:detalle', pk=pedido.pk)

    return render(request, 'pedidos/crear.html', {
        'pedido_form': pedido_form,
        'formset': formset,
        'categorias': Categoria.objects.filter(empresa=perfil.empresa).order_by('nombre'),
    })


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
def detalle_pedido(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver los pedidos.')
        return redirect('core:panel')

    pedido = get_object_or_404(Pedido.objects.select_related('cliente'), pk=pk, empresa=perfil.empresa)
    lineas = pedido.lineas.select_related('producto', 'producto__proveedor')
    return render(request, 'pedidos/detalle.html', {'pedido': pedido, 'lineas': lineas})


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
@require_http_methods(['POST'])
def actualizar_linea(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede actualizar un pedido.')
        return redirect('core:panel')

    linea = get_object_or_404(PedidoLinea, pk=pk, pedido__empresa=perfil.empresa)
    if linea.pedido.estado == 'completado':
        messages.error(request, 'Este pedido ya está completado, no se puede modificar.')
        return redirect('pedidos:detalle', pk=linea.pedido_id)

    ahora = timezone.now()
    campos = []

    ya_pedido = request.POST.get('ya_pedido') == 'on'
    if ya_pedido != linea.ya_pedido:
        linea.ya_pedido = ya_pedido
        linea.ya_pedido_en = ahora if ya_pedido else None
        campos += ['ya_pedido', 'ya_pedido_en']

    recibido = request.POST.get('recibido', 'no')
    if recibido in dict(PedidoLinea.RECIBIDO_CHOICES) and recibido != linea.recibido:
        linea.recibido = recibido
        linea.recibido_en = ahora if recibido != 'no' else None
        campos += ['recibido', 'recibido_en']

    if campos:
        linea.save(update_fields=campos)
        messages.success(request, 'Línea actualizada.')
    return redirect('pedidos:detalle', pk=linea.pedido_id)


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
@require_http_methods(['POST'])
def completar_pedido(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede completar un pedido.')
        return redirect('core:panel')

    pedido = get_object_or_404(Pedido, pk=pk, empresa=perfil.empresa)
    if pedido.estado != 'completado':
        pedido.estado = 'completado'
        pedido.completado_en = timezone.now()
        pedido.save(update_fields=['estado', 'completado_en'])
        messages.success(request, f'Pedido #{pedido.pk} marcado como completado.')
    return redirect('pedidos:detalle', pk=pedido.pk)


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
@require_http_methods(['POST'])
def convertir_a_venta(request, pk):
    """Pasa un pedido completado (con cliente y sucursal) a una venta ya
    terminada de ese cliente. Los productos del pedido se registran PRIMERO
    como entrada de inventario (llegaron del proveedor) y LUEGO como salida
    por la venta - así queda el historial completo en Movimientos de stock
    y el inventario de la sucursal nunca queda negativo por esto."""
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede pasar un pedido a venta.')
        return redirect('core:panel')

    pedido = get_object_or_404(
        Pedido.objects.select_related('cliente', 'sucursal'), pk=pk, empresa=perfil.empresa)

    if pedido.estado != 'completado':
        messages.error(request, 'Solo se puede pasar a venta un pedido completado.')
        return redirect('pedidos:detalle', pk=pedido.pk)
    if not pedido.cliente:
        messages.error(request, 'Este pedido no tiene cliente, no se puede pasar a venta.')
        return redirect('pedidos:detalle', pk=pedido.pk)
    if not pedido.sucursal:
        messages.error(request, 'Este pedido no tiene sucursal asignada, no se puede pasar a venta.')
        return redirect('pedidos:detalle', pk=pedido.pk)
    if pedido.venta_generada_id:
        messages.error(request, 'Este pedido ya fue pasado a venta.')
        return redirect('pedidos:detalle', pk=pedido.pk)

    lineas = [l for l in pedido.lineas.select_related('producto', 'producto__proveedor') if l.producto]
    if not lineas:
        messages.error(request, 'Este pedido no tiene productos válidos para pasar a venta.')
        return redirect('pedidos:detalle', pk=pedido.pk)

    with transaction.atomic():
        venta = Venta.objects.create(sucursal=pedido.sucursal, operador=perfil, cliente=pedido.cliente)
        total = Decimal('0')
        for linea in lineas:
            VentaLinea.objects.create(
                venta=venta, producto=linea.producto, cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario)
            registrar_entrada(
                empresa=perfil.empresa, producto=linea.producto, sucursal=pedido.sucursal,
                cantidad=linea.cantidad, usuario=perfil, proveedor=linea.producto.proveedor,
                nota=f'Pedido #{pedido.pk}',
            )
            registrar_salida(
                empresa=perfil.empresa, producto=linea.producto, sucursal=pedido.sucursal,
                cantidad=linea.cantidad, usuario=perfil, nota=f'Pedido #{pedido.pk} pasado a venta',
            )
            total += linea.cantidad * linea.precio_unitario
        venta.total = total
        venta.save(update_fields=['total'])
        pedido.venta_generada = venta
        pedido.save(update_fields=['venta_generada'])

    messages.success(request, f'Pedido #{pedido.pk} pasado a la venta #{venta.pk}.')
    return redirect('ventas:detalle', pk=venta.pk)


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
def pedido_pdf(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver los pedidos.')
        return redirect('core:panel')

    pedido = get_object_or_404(Pedido.objects.select_related('cliente'), pk=pk, empresa=perfil.empresa)
    lineas = pedido.lineas.select_related('producto', 'producto__proveedor')
    pdf_bytes = generar_pedido_pdf(pedido, lineas)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="pedido_{pedido.id}.pdf"'
    return response


@login_activo_required
@modulo_requerido('modulo_pedidos', 'Pedidos')
def pendientes_por_proveedor_pdf(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver los pedidos.')
        return redirect('core:panel')

    lineas = (
        PedidoLinea.objects.filter(pedido__empresa=perfil.empresa, pedido__estado='pendiente')
        .exclude(recibido='completo')
        .select_related('producto', 'producto__proveedor', 'pedido', 'pedido__cliente')
        .order_by('producto__proveedor__nombre', 'pedido_id')
    )
    pdf_bytes = generar_pendientes_por_proveedor_pdf(perfil.empresa, lineas)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="pendientes_por_proveedor.pdf"'
    return response
