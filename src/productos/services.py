from django.db import transaction


def siguiente_codigo_producto(proveedor):
    """Genera el código de un producto nuevo de este proveedor: su código
    (hasta 4 letras) + el siguiente número correlativo para ese proveedor.

    select_for_update() sobre el proveedor evita que dos altas simultáneas
    se lleven el mismo número; el while evita chocar con un código que ya
    exista (ej. un producto creado antes a mano con ese mismo texto) - los
    números no se reciclan, igual que una numeración de factura.
    """
    from .models import Producto  # import tardío, evita ciclo con proveedores

    with transaction.atomic():
        prov = type(proveedor).objects.select_for_update().get(pk=proveedor.pk)
        while True:
            prov.contador_productos += 1
            candidato = f'{prov.codigo}{prov.contador_productos}'
            if not Producto.objects.filter(empresa_id=prov.empresa_id, codigo=candidato).exists():
                break
        prov.save(update_fields=['contador_productos'])
    return candidato
