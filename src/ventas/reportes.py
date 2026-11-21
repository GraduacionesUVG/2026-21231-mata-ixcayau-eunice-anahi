import io
from pathlib import Path

from PIL import Image as PILImage
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

IMAGEN_ANCHO_MAX = 3 * cm
IMAGEN_ALTO_MAX = 3 * cm

COL_IMAGEN = 3.2 * cm
COL_PRODUCTO = 6.3 * cm
COL_CANTIDAD = 2.2 * cm
COL_PRECIO = 2.9 * cm
COL_SUBTOTAL = 2.9 * cm


def _ruta_local_imagen(url):
    """Convierte la URL relativa guardada en imagen_url (ej. "/media/productos/1/x.jpg")
    a su ruta real en disco, para incrustarla en el PDF sin pasar por HTTP."""
    if not url or not url.startswith(settings.MEDIA_URL):
        return None
    relativo = url[len(settings.MEDIA_URL):]
    ruta = Path(settings.MEDIA_ROOT) / relativo
    return ruta if ruta.exists() else None


def _imagen_flowable(ruta, styles):
    if not ruta:
        return Paragraph('(sin imagen)', styles['Normal'])
    try:
        with PILImage.open(ruta) as img:
            ancho_real, alto_real = img.size
    except Exception:
        return Paragraph('(imagen no disponible)', styles['Normal'])
    escala = min(IMAGEN_ANCHO_MAX / ancho_real, IMAGEN_ALTO_MAX / alto_real)
    return Image(str(ruta), width=ancho_real * escala, height=alto_real * escala)


def generar_resumen_pdf(venta, lineas):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    estilo_celda = styles['Normal']
    estilo_derecha = styles['Normal'].clone('derecha')
    estilo_derecha.alignment = 2  # TA_RIGHT

    elementos = []

    elementos.append(Paragraph(f'Venta #{venta.id}', styles['Title']))
    operador = venta.operador.nombre or venta.operador.email if venta.operador else '—'
    elementos.append(Paragraph(
        f'Sucursal: {venta.sucursal.nombre} &nbsp;·&nbsp; '
        f'Cliente: {venta.cliente.nombre if venta.cliente else "Anónimo"} &nbsp;·&nbsp; '
        f'Operador: {operador} &nbsp;·&nbsp; '
        f'Fecha: {timezone.localtime(venta.fecha).strftime("%d/%m/%Y %H:%M")}',
        styles['Normal'],
    ))
    elementos.append(Spacer(1, 0.6 * cm))

    filas = [['Imagen', 'Producto', 'Cantidad', 'Precio unitario', 'Subtotal']]
    for linea in lineas:
        ruta_imagen = _ruta_local_imagen(linea.producto.imagen_url) if linea.producto else None
        filas.append([
            _imagen_flowable(ruta_imagen, styles),
            Paragraph(linea.descripcion, estilo_celda),
            Paragraph(str(linea.cantidad), estilo_derecha),
            Paragraph(str(linea.precio_unitario), estilo_derecha),
            Paragraph(str(linea.subtotal), estilo_derecha),
        ])
    filas.append(['', '', '', Paragraph('<b>Total</b>', estilo_derecha), Paragraph(f'<b>{venta.total}</b>', estilo_derecha)])

    tabla = Table(
        filas,
        colWidths=[COL_IMAGEN, COL_PRODUCTO, COL_CANTIDAD, COL_PRECIO, COL_SUBTOTAL],
        repeatRows=1,
    )
    ultima_fila = len(filas) - 1
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (2, 0), (-1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, ultima_fila - 1), 0.5, colors.grey),
        ('LINEABOVE', (0, ultima_fila), (-1, ultima_fila), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
