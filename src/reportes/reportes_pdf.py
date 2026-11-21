import io

import matplotlib
matplotlib.use('Agg')  # sin esto matplotlib busca un display, y no hay uno en el contenedor
import matplotlib.pyplot as plt  # noqa: E402 (tiene que ir después de matplotlib.use)

from django.utils import timezone  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

COLOR_BARRA = '#333333'
COLOR_ACTUAL = '#1F6FEB'

ANCHO_IMG = 16 * cm
ALTO_IMG_V = 6.2 * cm  # gráficas verticales
ALTO_IMG_H = 5.3 * cm  # gráfica horizontal (proveedores)


def _bar_chart(etiquetas, valores, destacar=None, ylabel=''):
    valores = [float(v) for v in valores]  # Sum('cantidad') devuelve Decimal
    fig, ax = plt.subplots(figsize=(8, 3.1))
    colores = [
        COLOR_ACTUAL if (destacar and destacar[i]) else COLOR_BARRA
        for i in range(len(valores))
    ]
    ax.bar(range(len(valores)), valores, color=colores)
    ax.set_xticks(range(len(etiquetas)))
    ax.set_xticklabels(etiquetas, fontsize=7, rotation=45, ha='right')
    ax.tick_params(axis='y', labelsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.grid(True, axis='y', linestyle='--', alpha=0.4)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=130)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _hbar_chart(etiquetas, valores, subetiquetas=None):
    valores = [float(v) for v in valores]  # Sum('cantidad') devuelve Decimal
    fig, ax = plt.subplots(figsize=(8, 2.6))
    y_pos = range(len(valores))
    ax.barh(list(y_pos), valores, color=COLOR_ACTUAL)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(etiquetas, fontsize=8)
    ax.invert_yaxis()  # el primero (más vendido) queda arriba
    ax.tick_params(axis='x', labelsize=8)
    maximo = max(valores) if valores else 0
    if subetiquetas:
        for i, (v, sub) in enumerate(zip(valores, subetiquetas)):
            ax.text(v + maximo * 0.02, i, f'{sub} ({int(v)})', va='center', fontsize=7)
    ax.set_xlim(0, maximo * 1.4 if maximo else 1)
    ax.grid(True, axis='x', linestyle='--', alpha=0.4)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=130)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def generar_reportes_pdf(empresa, contexto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(f'Reportes — {empresa.nombre}', styles['Title']))
    elementos.append(Paragraph(
        f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal']))
    elementos.append(Spacer(1, 0.5 * cm))

    producto_top = contexto['producto_top_nombre']
    if contexto.get('producto_top_cantidad'):
        producto_top += f' ({contexto["producto_top_cantidad"]} unid.)'
    filas_resumen = [
        ['Sucursales', str(contexto['n_sucursales'])],
        ['Vendedores activos', str(contexto['n_vendedores'])],
        ['Productos activos', str(contexto['n_productos'])],
        ['Productos con stock bajo', str(contexto['stock_bajo_count'])],
        ['Producto más vendido (histórico)', producto_top],
    ]
    tabla_resumen = Table(filas_resumen, colWidths=[7 * cm, 9 * cm])
    tabla_resumen.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ]))
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 0.6 * cm))

    rango = contexto['rango_meses']

    ventas_mensuales = contexto['ventas_mensuales']
    elementos.append(Paragraph(f'Ventas mensuales (últimos {rango} meses)', styles['Heading3']))
    img = _bar_chart(
        [m['etiqueta'] for m in ventas_mensuales], [m['total'] for m in ventas_mensuales],
        destacar=[m['actual'] for m in ventas_mensuales], ylabel='Ventas')
    elementos.append(Image(img, width=ANCHO_IMG, height=ALTO_IMG_V))
    elementos.append(Spacer(1, 0.5 * cm))

    ventas_top_producto = contexto['ventas_top_producto']
    elementos.append(Paragraph(f'Producto más vendido por mes (últimos {rango} meses)', styles['Heading3']))
    img = _bar_chart(
        [m['etiqueta'] for m in ventas_top_producto], [m['cantidad'] for m in ventas_top_producto],
        destacar=[m['actual'] for m in ventas_top_producto], ylabel='Unidades')
    elementos.append(Image(img, width=ANCHO_IMG, height=ALTO_IMG_V))
    elementos.append(Spacer(1, 0.5 * cm))

    ventas_por_sucursal = contexto['ventas_por_sucursal']
    elementos.append(Paragraph('Ventas por sucursal este mes', styles['Heading3']))
    if ventas_por_sucursal:
        img = _bar_chart(
            [s['etiqueta'] for s in ventas_por_sucursal], [s['total'] for s in ventas_por_sucursal], ylabel='Ventas')
        elementos.append(Image(img, width=ANCHO_IMG, height=ALTO_IMG_V))
    else:
        elementos.append(Paragraph('Sin ventas todavía este mes.', styles['Normal']))
    elementos.append(Spacer(1, 0.5 * cm))

    ventas_top_por_proveedor = contexto['ventas_top_por_proveedor']
    elementos.append(Paragraph('Producto más vendido por proveedor (este mes)', styles['Heading3']))
    if ventas_top_por_proveedor:
        img = _hbar_chart(
            [v['proveedor'] for v in ventas_top_por_proveedor],
            [v['cantidad'] for v in ventas_top_por_proveedor],
            subetiquetas=[v['producto'] or 'Sin datos' for v in ventas_top_por_proveedor],
        )
        elementos.append(Image(img, width=ANCHO_IMG, height=ALTO_IMG_H))
    else:
        elementos.append(Paragraph('Sin ventas de productos con proveedor este mes.', styles['Normal']))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
