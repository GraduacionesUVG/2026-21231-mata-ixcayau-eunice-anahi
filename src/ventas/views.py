from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import login_activo_required
from core.models import PerfilUsuario
from core.services import get_perfil
from inventario.models import Stock
from inventario.services import registrar_salida
from productos.models import Categoria
from sucursales.models import Sucursal

from .forms import LineaVentaFormSet, VentaForm
from .models import Venta, VentaLinea
from .reportes import generar_resumen_pdf


@login_activo_required
def lista_ventas(request):
    perfil = get_perfil(request)
    ventas = Venta.objects.filter(sucursal__empresa=perfil.empresa).select_related('sucursal', 'operador', 'cliente')
    if perfil.rol == 'vendedor' and perfil.sucursal_id:
        ventas = ventas.filter(sucursal_id=perfil.sucursal_id)
    return render(request, 'ventas/lista.html', {'ventas': ventas, 'perfil': perfil})


@login_activo_required
def cierre_diario(request):
    """Resumen de ventas de HOY - para que el vendedor haga su cierre de
    caja, o el dueño revise el cierre de cualquier vendedor/sucursal."""
    perfil = get_perfil(request)
    hoy = timezone.localdate()

    ventas = Venta.objects.filter(sucursal__empresa=perfil.empresa, fecha__date=hoy)

    vendedor_id = ''
    sucursal_id = ''
    if perfil.rol == 'vendedor':
        # el vendedor solo ve su propio cierre - no puede elegir a nadie más
        ventas = ventas.filter(operador=perfil)
    else:
        vendedor_id = request.GET.get('vendedor', '')
        sucursal_id = request.GET.get('sucursal', '')
        if vendedor_id:
            ventas = ventas.filter(operador_id=vendedor_id)
        if sucursal_id:
            ventas = ventas.filter(sucursal_id=sucursal_id)

    ventas = ventas.select_related('sucursal', 'operador', 'cliente').order_by('-fecha')
    total = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')

    contexto = {
        'perfil': perfil,
        'hoy': hoy,
        'ventas': ventas,
        'total': total,
        'num_ventas': ventas.count(),
    }
    if perfil.rol == 'dueno':
        contexto['vendedores'] = PerfilUsuario.objects.filter(empresa=perfil.empresa, rol='vendedor', activo=True)
        contexto['sucursales'] = Sucursal.objects.filter(empresa=perfil.empresa)
        contexto['vendedor_id'] = vendedor_id
        contexto['sucursal_id'] = sucursal_id

    return render(request, 'ventas/cierre_diario.html', contexto)


@login_activo_required
def registrar_venta(request):
    perfil = get_perfil(request)

    if perfil.rol == 'vendedor':
        sucursal = perfil.sucursal
    else:
        sucursal_id = request.GET.get('sucursal') or request.POST.get('sucursal')
        sucursales_empresa = Sucursal.objects.filter(empresa=perfil.empresa)
        sucursal = sucursales_empresa.filter(id=sucursal_id).first() if sucursal_id else sucursales_empresa.first()

    if not sucursal:
        messages.error(request, 'No hay sucursales registradas todavía.')
        return redirect('core:panel')

    stock_map = {s.producto_id: s.cantidad for s in Stock.objects.filter(sucursal=sucursal)}
    form_kwargs = {'empresa': perfil.empresa, 'sucursal': sucursal, 'stock_map': stock_map}
    venta_form = VentaForm(request.POST or None, empresa=perfil.empresa)
    formset = LineaVentaFormSet(request.POST or None, form_kwargs=form_kwargs)

    if request.method == 'POST' and venta_form.is_valid() and formset.is_valid():
        lineas = [f.cleaned_data for f in formset if f.cleaned_data.get('cantidad')]
        if not lineas:
            messages.error(request, 'Agrega al menos un producto a la venta.')
        else:
            with transaction.atomic():
                venta = Venta.objects.create(
                    sucursal=sucursal, operador=perfil, cliente=venta_form.cleaned_data.get('cliente'))
                total = Decimal('0')
                for linea in lineas:
                    cantidad = linea['cantidad']
                    precio = linea.get('precio_unitario') or Decimal('0')
                    producto = linea.get('producto_obj')
                    if producto:
                        VentaLinea.objects.create(
                            venta=venta, producto=producto, cantidad=cantidad, precio_unitario=precio)
                        registrar_salida(
                            empresa=perfil.empresa, producto=producto, sucursal=sucursal,
                            cantidad=cantidad, usuario=perfil,
                        )
                    else:
                        VentaLinea.objects.create(
                            venta=venta, descripcion_libre=linea['descripcion_libre'],
                            cantidad=cantidad, precio_unitario=precio)
                    total += cantidad * precio
                venta.total = total
                venta.save(update_fields=['total'])
            messages.success(request, f'Venta #{venta.pk} registrada, total {total}.')
            return redirect('ventas:detalle', pk=venta.pk)

    return render(request, 'ventas/registrar.html', {
        'venta_form': venta_form,
        'formset': formset,
        'sucursal': sucursal,
        'sucursales': Sucursal.objects.filter(empresa=perfil.empresa) if perfil.rol == 'dueno' else None,
        'categorias': Categoria.objects.filter(empresa=perfil.empresa).order_by('nombre'),
    })


@login_activo_required
def detalle_venta(request, pk):
    perfil = get_perfil(request)
    ventas = Venta.objects.filter(sucursal__empresa=perfil.empresa)
    if perfil.rol == 'vendedor' and perfil.sucursal_id:
        ventas = ventas.filter(sucursal_id=perfil.sucursal_id)
    venta = get_object_or_404(
        ventas.select_related('sucursal', 'operador', 'cliente'), pk=pk)
    lineas = venta.lineas.select_related('producto')
    return render(request, 'ventas/detalle.html', {'venta': venta, 'lineas': lineas})


@login_activo_required
def detalle_venta_pdf(request, pk):
    perfil = get_perfil(request)
    ventas = Venta.objects.filter(sucursal__empresa=perfil.empresa)
    if perfil.rol == 'vendedor' and perfil.sucursal_id:
        ventas = ventas.filter(sucursal_id=perfil.sucursal_id)
    venta = get_object_or_404(
        ventas.select_related('sucursal', 'operador', 'cliente'), pk=pk)
    lineas = venta.lineas.select_related('producto')

    pdf_bytes = generar_resumen_pdf(venta, lineas)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="venta_{venta.id}.pdf"'
    return response
