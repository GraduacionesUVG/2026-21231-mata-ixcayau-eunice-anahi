import io

import matplotlib
matplotlib.use('Agg')  # sin esto matplotlib busca un display, y no hay uno en el contenedor
import matplotlib.pyplot as plt  # noqa: E402 (tiene que ir después de matplotlib.use)

from django.utils import timezone  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer  # noqa: E402


def _grafica_a_imagen(labels, valores):
    fig, ax = plt.subplots(figsize=(6.3, 2.8))
    indices = range(len(valores))
    ax.plot(indices, valores, marker='o', color='#1F6FEB', linewidth=1.8, markersize=4)
    ax.set_xticks([0, len(labels) - 1] if len(labels) > 1 else [0])
    ax.set_xticklabels([labels[0], labels[-1]] if len(labels) > 1 else [labels[0]], fontsize=8)
    ax.set_ylabel('Existencia', fontsize=8)
    ax.tick_params(axis='y', labelsize=8)
    ax.grid(True, linestyle='--', alpha=0.4)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=130)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def generar_reporte_pdf(empresa, productos, desde, hasta, reconstruir_historial):
    """`reconstruir_historial(producto, desde, hasta)` es la función que
    recalcula la existencia (ya probada por separado en productos/views.py)
    - se recibe por parámetro para no duplicarla aquí.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(f'Reporte de existencia de productos — {empresa.nombre}', styles['Title']))
    elementos.append(Paragraph(
        f'Rango: {desde.strftime("%d/%m/%Y")} a {hasta.strftime("%d/%m/%Y")} '
        f'&nbsp;·&nbsp; Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}',
        styles['Normal'],
    ))
    elementos.append(Spacer(1, 0.6 * cm))

    productos = list(productos)
    if not productos:
        elementos.append(Paragraph('No hay productos que coincidan con los filtros elegidos.', styles['Normal']))

    estilo_info = styles['Normal']
    for producto in productos:
        labels, valores = reconstruir_historial(producto, desde, hasta)

        elementos.append(Paragraph(f'{producto.codigo} — {producto.nombre}', styles['Heading2']))
        categorias = ', '.join(c.nombre for c in producto.categorias.all()) or '—'
        proveedor = producto.proveedor.nombre if producto.proveedor else '—'
        elementos.append(Paragraph(f'Proveedor: {proveedor} &nbsp;·&nbsp; Categorías: {categorias}', estilo_info))
        elementos.append(Paragraph(
            f'Precio unitario: {producto.precio_venta} &nbsp;·&nbsp; '
            f'Mayorista pequeño: {producto.precio_mayorista_pequeno} &nbsp;·&nbsp; '
            f'Mayorista grande: {producto.precio_mayorista_grande}',
            estilo_info,
        ))
        elementos.append(Spacer(1, 0.2 * cm))

        imagen = _grafica_a_imagen(labels, valores)
        elementos.append(Image(imagen, width=16 * cm, height=7 * cm))
        elementos.append(Spacer(1, 0.8 * cm))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
