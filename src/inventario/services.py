from decimal import Decimal

from .models import MovimientoStock, Stock


def registrar_entrada(*, empresa, producto, sucursal, cantidad, usuario, proveedor=None, nota=''):
    """Suma cantidad al Stock de esa sucursal/producto y deja el MovimientoStock correspondiente.

    Compartido entre la entrada de mercadería y el inventario inicial opcional
    al crear un producto - mismo efecto, dos puntos de entrada.
    """
    stock, _ = Stock.objects.get_or_create(
        sucursal=sucursal, producto=producto, defaults={'cantidad': Decimal('0')})
    stock.cantidad = stock.cantidad + cantidad
    stock.save(update_fields=['cantidad'])
    MovimientoStock.objects.create(
        empresa=empresa, producto=producto, tipo='entrada',
        sucursal_destino=sucursal, proveedor=proveedor, cantidad=cantidad,
        nota=nota, usuario=usuario,
    )
    return stock


def registrar_salida(*, empresa, producto, sucursal, cantidad, usuario, nota=''):
    """Resta cantidad del Stock de esa sucursal/producto y deja el
    MovimientoStock correspondiente (tipo='venta').

    select_for_update() evita que dos salidas simultáneas del mismo
    producto/sucursal se pisen y dejen el stock mal - debe llamarse
    dentro de un transaction.atomic().
    """
    stock = Stock.objects.select_for_update().get(sucursal=sucursal, producto=producto)
    stock.cantidad = stock.cantidad - cantidad
    stock.save(update_fields=['cantidad'])
    MovimientoStock.objects.create(
        empresa=empresa, producto=producto, tipo='venta',
        sucursal_origen=sucursal, cantidad=cantidad, nota=nota, usuario=usuario,
    )
    return stock
