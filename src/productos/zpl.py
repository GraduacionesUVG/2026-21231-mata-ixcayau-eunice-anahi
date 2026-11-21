import re

from django.conf import settings
from django.template.loader import render_to_string

# Code 128 (subset B, el más común para alfanumérico) solo codifica el
# rango ASCII imprimible 32-126 (espacio a ~). Nada de ñ, acentos ni
# caracteres fuera de ese rango.
_CODE128_VALIDO = re.compile(r'^[\x20-\x7E]+$')

# '^' y '~' son los caracteres de control de ZPL (inician comandos). Si un
# código o nombre de producto los trajera literalmente, romperían el
# resto de la etiqueta - se quitan antes de meterlos en el ZPL.
_CARACTERES_ZPL_RESERVADOS = str.maketrans('', '', '^~')


def validar_codigo_code128(codigo):
    """Lanza ValueError con un mensaje para el usuario si el código del
    producto no se puede codificar en Code 128."""
    if not codigo:
        raise ValueError('Este producto no tiene código, no se puede generar la etiqueta.')
    if not _CODE128_VALIDO.match(codigo):
        raise ValueError(
            f'El código "{codigo}" tiene caracteres que un código de barras Code 128 no '
            'puede representar (solo letras sin acentos/ñ, números y símbolos básicos).'
        )


def _mm_a_puntos(mm, dpi):
    return round(mm * dpi / 25.4)


def generar_zpl_producto(datos_producto, copias=1):
    """Arma el ZPL de una etiqueta (con sus copias) a partir de los datos
    de un producto (ver productos/etiquetas.py). No sabe nada de HTTP ni
    de qué vista la llama - solo texto adentro, texto ZPL afuera.
    """
    cfg = settings.ETIQUETA_ZPL
    dpi = cfg['DPI']

    nombre = datos_producto['nombre'][:cfg['NOMBRE_MAX_CARACTERES']].translate(_CARACTERES_ZPL_RESERVADOS)
    codigo = datos_producto['codigo'].translate(_CARACTERES_ZPL_RESERVADOS)

    contexto = {
        'nombre': nombre,
        'codigo': codigo,
        'copias': max(1, int(copias)),
        'ancho_puntos': _mm_a_puntos(cfg['ANCHO_MM'], dpi),
        'alto_puntos': _mm_a_puntos(cfg['ALTO_MM'], dpi),
        'margen_puntos': _mm_a_puntos(cfg['MARGEN_IZQ_MM'], dpi),
        'nombre_y_puntos': _mm_a_puntos(cfg['NOMBRE_Y_MM'], dpi),
        'nombre_alto_puntos': _mm_a_puntos(cfg['NOMBRE_ALTO_MM'], dpi),
        'barcode_y_puntos': _mm_a_puntos(cfg['BARCODE_Y_MM'], dpi),
        'barcode_alto_puntos': _mm_a_puntos(cfg['BARCODE_ALTO_MM'], dpi),
        'barcode_modulo_puntos': max(1, _mm_a_puntos(cfg['BARCODE_MODULO_MM'], dpi)),
        'barcode_ratio': cfg['BARCODE_RATIO'],
    }
    return render_to_string('productos/etiqueta.zpl', contexto)
