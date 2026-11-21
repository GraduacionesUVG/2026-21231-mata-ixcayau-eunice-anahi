import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from core.decorators import login_activo_required, modulo_requerido
from core.services import get_perfil
from core.storage import guardar_archivo
from inventario.models import MovimientoStock
from inventario.services import registrar_entrada
from proveedores.models import Proveedor

from .etiquetas import datos_etiqueta
from .forms import ProductoForm, ReporteStockForm
from .models import Categoria, Producto
from .reportes import generar_reporte_pdf
from .services import siguiente_codigo_producto
from .zpl import generar_zpl_producto, validar_codigo_code128

RANGOS_MESES_VALIDOS = {1, 3, 6, 12, 24}


@never_cache
@login_activo_required
def lista_productos(request):
    perfil = get_perfil(request)
    productos = (
        Producto.objects.filter(empresa=perfil.empresa)
        .select_related('proveedor')
        .prefetch_related('categorias')
    )

    categoria_ids = request.GET.getlist('categoria')
    proveedor_ids = request.GET.getlist('proveedor')
    modo_categoria = request.GET.get('modo_categoria') if request.GET.get('modo_categoria') == 'especifico' else 'cualquiera'
    q = request.GET.get('q', '').strip()

    if q:
        productos = productos.filter(codigo__icontains=q)
    if categoria_ids:
        if modo_categoria == 'especifico':
            # el producto tiene que tener TODAS las categorías marcadas (pueden
            # ser más) - encadenar un .filter(categorias=id) por cada una hace
            # un JOIN distinto por categoría, lo que en Django es el patrón
            # correcto para "contiene todos estos" en un M2M (un único
            # categorias__id__in solo pide "contiene alguno de estos")
            for cid in categoria_ids:
                productos = productos.filter(categorias__id=cid)
            productos = productos.distinct()
        else:
            # "cualquiera": un producto con CUALQUIERA de las categorías
            # marcadas ya cuenta - distinct() evita filas repetidas
            productos = productos.filter(categorias__id__in=categoria_ids).distinct()
    if proveedor_ids:
        productos = productos.filter(proveedor_id__in=proveedor_ids)

    return render(request, 'productos/lista.html', {
        'productos': productos,
        'perfil': perfil,
        'categorias': Categoria.objects.filter(empresa=perfil.empresa),
        'proveedores': Proveedor.objects.filter(empresa=perfil.empresa),
        'categoria_ids': categoria_ids,
        'proveedor_ids': proveedor_ids,
        'modo_categoria': modo_categoria,
        'q': q,
    })


@login_activo_required
@require_http_methods(['POST'])
def crear_categoria(request):
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    perfil = get_perfil(request)

    if perfil.rol != 'dueno':
        if es_ajax:
            return JsonResponse({'error': 'Solo el dueño puede crear categorías.'}, status=403)
        messages.error(request, 'Solo el dueño puede crear categorías.')
        return redirect('productos:lista')

    nombre = request.POST.get('nombre', '').strip()
    if not nombre:
        if es_ajax:
            return JsonResponse({'error': 'Indica un nombre para la categoría.'}, status=400)
        messages.error(request, 'Indica un nombre para la categoría.')
        return redirect('productos:lista')

    try:
        categoria = Categoria.objects.create(empresa=perfil.empresa, nombre=nombre)
    except IntegrityError:
        if es_ajax:
            # ya existe - de todas formas es un resultado válido para quien
            # está buscando/creando en el mismo textbox, se la devolvemos
            categoria = Categoria.objects.get(empresa=perfil.empresa, nombre=nombre)
            return JsonResponse({'id': categoria.id, 'nombre': categoria.nombre})
        messages.error(request, f'Ya existe una categoría llamada "{nombre}".')
        return redirect('productos:lista')

    if es_ajax:
        return JsonResponse({'id': categoria.id, 'nombre': categoria.nombre})
    messages.success(request, f'Categoría "{nombre}" creada.')
    return redirect('productos:lista')


def _categorias_json(empresa):
    return json.dumps(list(
        Categoria.objects.filter(empresa=empresa).values('id', 'nombre').order_by('nombre')
    ))


@never_cache
@login_activo_required
def crear_producto(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede crear productos.')
        return redirect('productos:lista')

    form = ProductoForm(request.POST or None, request.FILES or None, empresa=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        producto = None
        try:
            with transaction.atomic():
                producto = form.save(commit=False)
                producto.empresa = perfil.empresa
                proveedor = form.cleaned_data.get('proveedor')
                if proveedor:
                    producto.codigo = siguiente_codigo_producto(proveedor)
                producto.save()
                form.save_m2m()  # categorias: M2M, necesita el producto ya guardado

                sucursal_inicial = form.cleaned_data.get('sucursal_inicial')
                cantidad_inicial = form.cleaned_data.get('cantidad_inicial')
                if sucursal_inicial and cantidad_inicial:
                    registrar_entrada(
                        empresa=perfil.empresa, producto=producto, sucursal=sucursal_inicial,
                        cantidad=cantidad_inicial, usuario=perfil, nota='Inventario inicial al crear el producto',
                    )
        except IntegrityError:
            form.add_error('codigo', f'Ya existe un producto con el código "{producto.codigo}".')
        else:
            _subir_imagen_si_aplica(request, producto, form.cleaned_data.get('imagen'))
            messages.success(request, f'Producto "{producto.nombre}" creado.')
            return redirect('productos:lista')
    return render(request, 'productos/crear.html', {
        'form': form,
        'categorias_disponibles_json': _categorias_json(perfil.empresa),
        'categorias_seleccionadas_json': '[]',
    })


@never_cache
@login_activo_required
def editar_producto(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede editar productos.')
        return redirect('productos:lista')

    producto = get_object_or_404(Producto, pk=pk, empresa=perfil.empresa)
    proveedor_anterior_id = producto.proveedor_id
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto, empresa=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        nuevo_proveedor = form.cleaned_data.get('proveedor')
        if nuevo_proveedor and nuevo_proveedor.id != proveedor_anterior_id:
            # el proveedor cambió (o se eligió uno por primera vez) - se
            # genera un código nuevo; si no cambió, se conserva el que ya tenía
            producto.codigo = siguiente_codigo_producto(nuevo_proveedor)
        try:
            producto.save()
        except IntegrityError:
            form.add_error('codigo', f'Ya existe un producto con el código "{producto.codigo}".')
        else:
            form.save_m2m()  # categorias: M2M, necesita el producto ya guardado
            _subir_imagen_si_aplica(request, producto, form.cleaned_data.get('imagen'))
            messages.success(request, f'Producto "{producto.nombre}" actualizado.')
            return redirect('productos:lista')
    categorias_seleccionadas = list(producto.categorias.values('id', 'nombre').order_by('nombre'))
    return render(request, 'productos/crear.html', {
        'form': form,
        'producto': producto,
        'categorias_disponibles_json': _categorias_json(perfil.empresa),
        'categorias_seleccionadas_json': json.dumps(categorias_seleccionadas),
    })


def _reconstruir_historial_stock(producto, desde, hasta):
    """Reconstruye la existencia total de la empresa (todas las sucursales)
    para ese producto entre `desde` y `hasta` (datetimes con tz), a partir
    del historial de MovimientoStock: entrada suma, venta resta,
    transferencia/ajuste no cambian el total de la empresa (solo mueven
    entre sucursales).

    Cada movimiento dentro del rango es su propio punto (no se agrupan por
    día) para que una entrada de mercadería se vea como su propio cambio,
    aunque haya otro movimiento el mismo día. Devuelve (labels, valores).
    """
    movimientos = MovimientoStock.objects.filter(producto=producto, creado_en__lte=hasta).order_by('creado_en')
    total = Decimal('0')
    nivel_al_inicio_rango = Decimal('0')
    puntos = []  # (timestamp, nivel tras el movimiento) dentro del rango

    for m in movimientos:
        if m.tipo == 'entrada':
            total += m.cantidad
        elif m.tipo == 'venta':
            total -= m.cantidad

        if m.creado_en < desde:
            nivel_al_inicio_rango = total
        else:
            puntos.append((m.creado_en, total))

    labels = [desde.strftime('%d/%m/%Y')]
    valores = [float(nivel_al_inicio_rango)]
    for ts, nivel in puntos:
        labels.append(ts.strftime('%d/%m/%Y %H:%M'))
        valores.append(float(nivel))

    if not puntos or puntos[-1][0].date() != hasta.date():
        labels.append(hasta.strftime('%d/%m/%Y'))
        valores.append(float(total))

    return labels, valores


def _serie_historial_stock(producto, meses):
    ahora = timezone.now()
    desde = ahora - timedelta(days=30 * meses)
    labels, valores = _reconstruir_historial_stock(producto, desde, ahora)
    return {'labels': labels, 'valores': valores}


def _meses_desde_request(request):
    try:
        meses = int(request.GET.get('meses', 12))
    except (TypeError, ValueError):
        meses = 12
    return meses if meses in RANGOS_MESES_VALIDOS else 12


@login_activo_required
def detalle_producto_json(request, pk):
    perfil = get_perfil(request)
    producto = get_object_or_404(
        Producto.objects.select_related('proveedor').prefetch_related('categorias'),
        pk=pk, empresa=perfil.empresa,
    )
    return JsonResponse({
        'codigo': producto.codigo,
        'nombre': producto.nombre,
        'imagen_url': producto.imagen_url,
        'proveedor': producto.proveedor.nombre if producto.proveedor else '',
        'categorias': list(producto.categorias.values_list('nombre', flat=True)),
        'fecha_creacion': producto.creado_en.strftime('%d/%m/%Y'),
        'precio_venta': str(producto.precio_venta),
        'precio_mayorista_pequeno': str(producto.precio_mayorista_pequeno),
        'precio_mayorista_grande': str(producto.precio_mayorista_grande),
        'historial': _serie_historial_stock(producto, _meses_desde_request(request)),
    })


@login_activo_required
def historial_stock_json(request, pk):
    perfil = get_perfil(request)
    producto = get_object_or_404(Producto, pk=pk, empresa=perfil.empresa)
    return JsonResponse(_serie_historial_stock(producto, _meses_desde_request(request)))


@login_activo_required
@modulo_requerido('modulo_codigo_barras', 'Código de barras')
def generar_etiquetas_zpl(request):
    """Devuelve el ZPL (texto plano) de uno o varios productos, listo
    para que el navegador se lo mande a Browser Print. No imprime nada
    acá - el servidor no tiene forma de llegarle a la impresora."""
    perfil = get_perfil(request)

    producto_ids = request.GET.getlist('producto_id')
    if not producto_ids:
        return HttpResponseBadRequest('Indica al menos un producto.')

    try:
        copias = int(request.GET.get('copias', 1))
    except ValueError:
        copias = 1
    copias = max(1, min(copias, 100))  # tope razonable contra pedidos absurdos

    productos = Producto.objects.filter(pk__in=producto_ids, empresa=perfil.empresa)
    if not productos:
        return HttpResponseBadRequest('Producto no encontrado.')

    bloques_zpl = []
    for producto in productos:
        datos = datos_etiqueta(producto)
        try:
            validar_codigo_code128(datos['codigo'])
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        bloques_zpl.append(generar_zpl_producto(datos, copias))

    return HttpResponse(''.join(bloques_zpl), content_type='text/plain; charset=utf-8')


def _productos_filtrados_para_reporte(perfil, categorias, proveedores):
    productos = (
        Producto.objects.filter(empresa=perfil.empresa)
        .select_related('proveedor')
        .prefetch_related('categorias')
    )
    if categorias:
        productos = productos.filter(categorias__in=categorias).distinct()
    if proveedores:
        productos = productos.filter(proveedor__in=proveedores)
    return productos.order_by('nombre')


@login_activo_required
def reporte_productos(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede generar reportes.')
        return redirect('productos:lista')

    form = ReporteStockForm(empresa=perfil.empresa)
    return render(request, 'productos/reporte.html', {'form': form, 'perfil': perfil})


@login_activo_required
def reporte_productos_pdf(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede generar reportes.')
        return redirect('productos:lista')

    form = ReporteStockForm(request.GET or None, empresa=perfil.empresa)
    if not form.is_valid():
        messages.error(request, 'Revisa los filtros del reporte (la fecha "desde" no puede ser posterior a "hasta").')
        return redirect('productos:reporte')

    categorias = form.cleaned_data['categorias']
    proveedores = form.cleaned_data['proveedores']
    fecha_desde = form.cleaned_data['fecha_desde']
    fecha_hasta = form.cleaned_data['fecha_hasta']

    desde = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()))
    hasta = timezone.make_aware(datetime.combine(fecha_hasta, datetime.max.time()))

    productos = _productos_filtrados_para_reporte(perfil, categorias, proveedores)
    pdf_bytes = generar_reporte_pdf(perfil.empresa, productos, desde, hasta, _reconstruir_historial_stock)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_productos.pdf"'
    return response


def _subir_imagen_si_aplica(request, producto, imagen):
    if not imagen:
        return
    # la imagen es opcional, así que un fallo aquí no debe tumbar el guardado del producto
    try:
        producto.imagen_url = guardar_archivo('productos', f'{producto.empresa_id}/{producto.id}_{imagen.name}', imagen)
        producto.save(update_fields=['imagen_url'])
    except Exception as exc:
        messages.warning(
            request,
            f'No se pudo subir la imagen ({exc}). Puedes editar el producto y volver a intentarlo.',
        )
