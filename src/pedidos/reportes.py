import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLOR_PENDIENTE = colors.HexColor('#fdf2d0')  # fondo tenue para filas sin "recibido completo"


def _estilos():
    styles = getSampleStyleSheet()
    estilo_derecha = styles['Normal'].clone('derecha')
    estilo_derecha.alignment = 2  # TA_RIGHT
    return styles, estilo_derecha


def _descripcion_producto(producto):
    if not producto:
        return '(producto eliminado)'
    return f'{producto.codigo} - {producto.nombre}'


def _nombre_proveedor(producto):
    if producto and producto.proveedor:
        return producto.proveedor.nombre
    return 'Sin proveedor'


def _estilo_tabla(num_filas, encabezados_extra=None):
    reglas = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, num_filas - 1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    if encabezados_extra:
        reglas += encabezados_extra
    return TableStyle(reglas)


def generar_pedido_pdf(pedido, lineas):
    """PDF de un pedido específico: todas sus líneas (pendientes y
    completadas) con su proveedor, para llevar o repasar el pedido completo."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles, estilo_derecha = _estilos()
    elementos = []

    elementos.append(Paragraph(f'Pedido #{pedido.id}', styles['Title']))
    info = (
        f'Cliente: {pedido.cliente.nombre if pedido.cliente else "Sin cliente"} &nbsp;·&nbsp; '
        f'Estado: {pedido.get_estado_display()} &nbsp;·&nbsp; '
        f'Creado: {timezone.localtime(pedido.creado_en).strftime("%d/%m/%Y %H:%M")}'
    )
    if pedido.completado_en:
        info += f' &nbsp;·&nbsp; Completado: {timezone.localtime(pedido.completado_en).strftime("%d/%m/%Y %H:%M")}'
    elementos.append(Paragraph(info, styles['Normal']))
    elementos.append(Spacer(1, 0.6 * cm))

    lineas = list(lineas)
    if not lineas:
        elementos.append(Paragraph('Este pedido no tiene productos.', styles['Normal']))
    else:
        filas = [['Producto', 'Proveedor', 'Cantidad', 'Precio', 'Ya pedido', 'Recibido']]
        resaltar = []  # índices de fila (1-based, el 0 es encabezado) que van con fondo "pendiente"
        for i, linea in enumerate(lineas, start=1):
            filas.append([
                Paragraph(_descripcion_producto(linea.producto), styles['Normal']),
                Paragraph(_nombre_proveedor(linea.producto), styles['Normal']),
                Paragraph(str(linea.cantidad), estilo_derecha),
                Paragraph(str(linea.precio_unitario), estilo_derecha),
                Paragraph('Sí' if linea.ya_pedido else 'No', styles['Normal']),
                Paragraph(linea.get_recibido_display(), styles['Normal']),
            ])
            if linea.recibido != 'completo':
                resaltar.append(i)

        tabla = Table(
            filas, colWidths=[5.5 * cm, 3 * cm, 2 * cm, 2.3 * cm, 2.2 * cm, 3 * cm], repeatRows=1)
        extra = [('BACKGROUND', (0, i), (-1, i), COLOR_PENDIENTE) for i in resaltar]
        tabla.setStyle(_estilo_tabla(len(filas), extra))
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.3 * cm))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pendientes_por_proveedor_pdf(empresa, lineas):
    """PDF global: todas las líneas pendientes (de pedidos en estado
    'pendiente' y que no están "recibido completo") de TODOS los pedidos,
    agrupadas por proveedor - para saber a quién contactar."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles, estilo_derecha = _estilos()
    elementos = []

    elementos.append(Paragraph(f'Pendientes por proveedor — {empresa.nombre}', styles['Title']))
    elementos.append(Paragraph(
        f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal']))
    elementos.append(Spacer(1, 0.6 * cm))

    lineas = list(lineas)
    if not lineas:
        elementos.append(Paragraph('No hay líneas pendientes en ningún pedido activo.', styles['Normal']))

    por_proveedor = {}
    for linea in lineas:
        por_proveedor.setdefault(_nombre_proveedor(linea.producto), []).append(linea)

    for nombre_proveedor in sorted(por_proveedor):
        elementos.append(Paragraph(nombre_proveedor, styles['Heading2']))
        filas = [['Pedido', 'Cliente', 'Producto', 'Cantidad', 'Ya pedido', 'Recibido']]
        for linea in por_proveedor[nombre_proveedor]:
            filas.append([
                Paragraph(f'#{linea.pedido_id}', styles['Normal']),
                Paragraph(linea.pedido.cliente.nombre if linea.pedido.cliente else '—', styles['Normal']),
                Paragraph(_descripcion_producto(linea.producto), styles['Normal']),
                Paragraph(str(linea.cantidad), estilo_derecha),
                Paragraph('Sí' if linea.ya_pedido else 'No', styles['Normal']),
                Paragraph(linea.get_recibido_display(), styles['Normal']),
            ])
        tabla = Table(
            filas, colWidths=[1.8 * cm, 3 * cm, 6 * cm, 2 * cm, 2.2 * cm, 3 * cm], repeatRows=1)
        tabla.setStyle(_estilo_tabla(len(filas)))
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.6 * cm))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
