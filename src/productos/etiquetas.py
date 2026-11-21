def datos_etiqueta(producto):
    """Datos de UN producto para armar su etiqueta - no sabe nada de ZPL
    ni de impresoras (eso vive en productos/zpl.py). Si el día de mañana
    cambia qué se imprime en la etiqueta, es este diccionario el que
    crece, no la plantilla ni la vista.
    """
    return {
        'nombre': producto.nombre,
        'codigo': producto.codigo,
    }
