from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.decorators import login_activo_required, modulo_requerido
from core.models import PerfilUsuario
from core.services import get_perfil
from inventario.models import Stock
from productos.models import Producto
from sucursales.models import Sucursal
from ventas.models import Venta, VentaLinea

from .reportes_pdf import generar_reportes_pdf

MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
RANGOS_MESES = [12, 24, 36, 48, 60]


def _ultimos_n_meses(n):
    hoy = timezone.localdate()
    y, m = hoy.year, hoy.month
    meses = []
    for _ in range(n):
        meses.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(meses))


def _rango_meses_desde_request(request):
    try:
        rango_meses = int(request.GET.get('meses', 12))
    except ValueError:
        rango_meses = 12
    return rango_meses if rango_meses in RANGOS_MESES else 12


def _rango_fechas_desde_request(request):
    """Rango desde/hasta para los reportes de margen y clientes top - por
    defecto, lo que va del mes actual. Independiente del selector de
    'últimos N meses' de las gráficas mensuales."""
    hoy = timezone.localdate()
    primero_del_mes = hoy.replace(day=1)

    def _parsear(valor, default):
        try:
            return datetime.strptime(valor, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return default

    desde = _parsear(request.GET.get('desde'), primero_del_mes)
    hasta = _parsear(request.GET.get('hasta'), hoy)
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _margen_por_producto(empresa, desde, hasta):
    """Margen real (ingresos - costo) por producto en el rango, usando el
    precio REALMENTE cobrado en cada venta (no el precio de lista) - así
    refleja descuentos o ajustes que haya hecho el vendedor. El costo usa
    el costo actual del producto (no se guarda un histórico de costos)."""
    desde_dt = timezone.make_aware(datetime.combine(desde, datetime.min.time()))
    hasta_dt = timezone.make_aware(datetime.combine(hasta, datetime.max.time()))
    decimal_money = DecimalField(max_digits=14, decimal_places=2)

    filas = (
        VentaLinea.objects.filter(
            venta__sucursal__empresa=empresa, venta__fecha__gte=desde_dt, venta__fecha__lte=hasta_dt,
            producto__isnull=False,
        )
        .values('producto_id', 'producto__codigo', 'producto__nombre')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Sum(F('cantidad') * F('precio_unitario'), output_field=decimal_money),
            costo_total=Sum(F('cantidad') * F('producto__costo'), output_field=decimal_money),
        )
    )

    resultado = []
    for fila in filas:
        ingresos = fila['ingresos'] or Decimal('0')
        costo_total = fila['costo_total'] or Decimal('0')
        margen = ingresos - costo_total
        resultado.append({
            'codigo': fila['producto__codigo'],
            'nombre': fila['producto__nombre'],
            'unidades': fila['unidades'],
            'ingresos': ingresos,
            'costo': costo_total,
            'margen': margen,
            'margen_pct': round(margen / ingresos * 100, 1) if ingresos else None,
        })
    resultado.sort(key=lambda r: r['margen'], reverse=True)
    return resultado


def _clientes_top(empresa, desde, hasta):
    """Ranking de clientes por gasto total en el rango. Las ventas
    anónimas (sin cliente) no participan - no hay a quién atribuirlas."""
    desde_dt = timezone.make_aware(datetime.combine(desde, datetime.min.time()))
    hasta_dt = timezone.make_aware(datetime.combine(hasta, datetime.max.time()))

    filas = (
        Venta.objects.filter(
            sucursal__empresa=empresa, fecha__gte=desde_dt, fecha__lte=hasta_dt, cliente__isnull=False)
        .values('cliente_id', 'cliente__nombre')
        .annotate(num_compras=Count('id'), gasto_total=Sum('total'))
        .order_by('-gasto_total')
    )
    return [
        {
            'nombre': fila['cliente__nombre'],
            'num_compras': fila['num_compras'],
            'gasto_total': fila['gasto_total'] or Decimal('0'),
        }
        for fila in filas
    ]


def _construir_contexto_reportes(empresa, rango_meses):
    hoy = timezone.localdate()
    meses = _ultimos_n_meses(rango_meses)
    desde = timezone.make_aware(datetime(meses[0][0], meses[0][1], 1))

    top_all_time = (
        VentaLinea.objects.filter(venta__sucursal__empresa=empresa, producto__isnull=False)
        .values('producto__nombre').annotate(total=Sum('cantidad')).order_by('-total').first()
    )

    conteo_mensual = (
        Venta.objects.filter(sucursal__empresa=empresa, fecha__gte=desde)
        .annotate(mes=TruncMonth('fecha')).values('mes').annotate(total=Count('id'))
    )
    conteo_por_mes = {c['mes'].strftime('%Y-%m'): c['total'] for c in conteo_mensual}

    # order_by('mes', '-total') deja el producto con más unidades primero dentro
    # de cada mes, así el primer registro de cada clave ya es el top de ese mes.
    lineas_por_mes = (
        VentaLinea.objects.filter(
            venta__sucursal__empresa=empresa, venta__fecha__gte=desde, producto__isnull=False)
        .annotate(mes=TruncMonth('venta__fecha'))
        .values('mes', 'producto__nombre').annotate(total=Sum('cantidad'))
        .order_by('mes', '-total')
    )
    top_por_mes = {}
    for fila in lineas_por_mes:
        clave = fila['mes'].strftime('%Y-%m')
        if clave not in top_por_mes:
            top_por_mes[clave] = {'producto': fila['producto__nombre'], 'cantidad': fila['total']}

    max_ventas_mes = max(conteo_por_mes.values(), default=0)
    max_top_producto = max((v['cantidad'] for v in top_por_mes.values()), default=0)

    ventas_mensuales = []
    ventas_top_producto = []
    for y, m in meses:
        clave = f'{y:04d}-{m:02d}'
        etiqueta = f'{MESES_ES[m - 1]} {str(y)[2:]}'
        es_actual = (y == hoy.year and m == hoy.month)

        total = conteo_por_mes.get(clave, 0)
        ventas_mensuales.append({
            'etiqueta': etiqueta,
            'total': total,
            'pct': round(total / max_ventas_mes * 100) if max_ventas_mes else 0,
            'actual': es_actual,
        })

        top = top_por_mes.get(clave)
        cantidad = top['cantidad'] if top else 0
        ventas_top_producto.append({
            'etiqueta': etiqueta,
            'producto': top['producto'] if top else None,
            'cantidad': cantidad,
            'pct': round(cantidad / max_top_producto * 100) if max_top_producto else 0,
            'actual': es_actual,
        })

    ventas_sucursal_qs = (
        Venta.objects.filter(sucursal__empresa=empresa, fecha__year=hoy.year, fecha__month=hoy.month)
        .values('sucursal__nombre').annotate(total=Count('id')).order_by('-total')[:5]
    )
    max_sucursal = max((v['total'] for v in ventas_sucursal_qs), default=0)
    ventas_por_sucursal = [
        {
            'etiqueta': v['sucursal__nombre'],
            'total': v['total'],
            'pct': round(v['total'] / max_sucursal * 100) if max_sucursal else 0,
        }
        for v in ventas_sucursal_qs
    ]

    stock_bajo_count = Stock.objects.filter(sucursal__empresa=empresa, cantidad__lte=F('stock_minimo')).count()

    # producto más vendido por proveedor este mes - solo los 3 proveedores
    # con más unidades vendidas en total
    lineas_mes_con_proveedor = VentaLinea.objects.filter(
        venta__sucursal__empresa=empresa, venta__fecha__year=hoy.year, venta__fecha__month=hoy.month,
        producto__isnull=False, producto__proveedor__isnull=False,
    )
    top_proveedores = (
        lineas_mes_con_proveedor.values('producto__proveedor_id', 'producto__proveedor__nombre')
        .annotate(total=Sum('cantidad')).order_by('-total')[:3]
    )
    ventas_top_por_proveedor = []
    for fila in top_proveedores:
        mejor_producto = (
            lineas_mes_con_proveedor.filter(producto__proveedor_id=fila['producto__proveedor_id'])
            .values('producto__nombre').annotate(total=Sum('cantidad')).order_by('-total').first()
        )
        ventas_top_por_proveedor.append({
            'proveedor': fila['producto__proveedor__nombre'],
            'producto': mejor_producto['producto__nombre'] if mejor_producto else None,
            'cantidad': mejor_producto['total'] if mejor_producto else 0,
        })
    max_cantidad_top_proveedor = max((v['cantidad'] for v in ventas_top_por_proveedor), default=0)
    for v in ventas_top_por_proveedor:
        v['pct'] = round(v['cantidad'] / max_cantidad_top_proveedor * 100) if max_cantidad_top_proveedor else 0

    return {
        'n_sucursales': Sucursal.objects.filter(empresa=empresa).count(),
        'n_vendedores': PerfilUsuario.objects.filter(empresa=empresa, rol='vendedor', activo=True).count(),
        'n_productos': Producto.objects.filter(empresa=empresa, activo=True).count(),
        'stock_bajo_count': stock_bajo_count,
        'producto_top_nombre': top_all_time['producto__nombre'] if top_all_time else 'Sin datos',
        'producto_top_cantidad': top_all_time['total'] if top_all_time else None,
        'ventas_mensuales': ventas_mensuales,
        'ventas_top_producto': ventas_top_producto,
        'ventas_por_sucursal': ventas_por_sucursal,
        'ventas_top_por_proveedor': ventas_top_por_proveedor,
        'rango_meses': rango_meses,
        'rangos_meses': RANGOS_MESES,
    }


@login_activo_required
@modulo_requerido('modulo_reportes', 'Reportes')
def dashboard_reportes(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver los reportes.')
        return redirect('core:panel')

    rango_meses = _rango_meses_desde_request(request)
    contexto = _construir_contexto_reportes(perfil.empresa, rango_meses)

    fecha_desde, fecha_hasta = _rango_fechas_desde_request(request)
    contexto['fecha_desde'] = fecha_desde
    contexto['fecha_hasta'] = fecha_hasta
    contexto['margen_por_producto'] = _margen_por_producto(perfil.empresa, fecha_desde, fecha_hasta)
    contexto['clientes_top'] = _clientes_top(perfil.empresa, fecha_desde, fecha_hasta)

    return render(request, 'reportes/dashboard.html', contexto)


@login_activo_required
@modulo_requerido('modulo_reportes', 'Reportes')
def dashboard_reportes_pdf(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver los reportes.')
        return redirect('core:panel')

    rango_meses = _rango_meses_desde_request(request)
    contexto = _construir_contexto_reportes(perfil.empresa, rango_meses)
    pdf_bytes = generar_reportes_pdf(perfil.empresa, contexto)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reportes.pdf"'
    return response
