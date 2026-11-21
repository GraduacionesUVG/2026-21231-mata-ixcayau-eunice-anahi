"""Carga datos ficticios (dummy) para probar Facil Modera.

Uso:
    python manage.py cargar_datos_demo           # solo si aún no hay empresa
    python manage.py cargar_datos_demo --reset   # borra todo y vuelve a cargar

Todos los nombres, teléfonos y correos son inventados.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from clientes.models import Cliente
from core.models import Empresa, PerfilUsuario
from inventario.models import Stock
from inventario.services import registrar_entrada, registrar_salida
from pedidos.models import Pedido, PedidoLinea
from productos.models import Categoria, Producto
from productos.services import siguiente_codigo_producto
from proveedores.models import Proveedor
from sucursales.models import Almacen, Sucursal
from ventas.models import Venta, VentaLinea

PASSWORD = 'Demo2026!'

SUCURSALES = [
    # nombre, código, dirección, ciudad, punto de venta
    ('Tienda Central', 'CEN', '6a Avenida 10-25, Zona 1', 'Guatemala', True),
    ('Tienda Oakland', 'OAK', 'Diagonal 6 13-01, Zona 10', 'Guatemala', True),
    ('Bodega Principal', 'BOD', 'Calzada Roosevelt 22-43, Zona 11', 'Guatemala', False),
]

VENDEDORES = [
    # nombre, correo, código sucursal, PIN
    ('Carlos Pérez', 'vendedor1@demo.com', 'CEN', '1234'),
    ('María López', 'vendedor2@demo.com', 'OAK', '5678'),
]

PROVEEDORES = [
    ('Textiles del Altiplano', 'TEX', '+502 5555 0101'),
    ('Calzado Maya', 'CALZ', '+502 5555 0202'),
    ('Accesorios Quetzal', 'ACC', '+502 5555 0303'),
    ('Moda Express Importaciones', 'MODA', '+502 5555 0404'),
]

CATEGORIAS = ['Blusas', 'Pantalones', 'Vestidos', 'Calzado', 'Accesorios']

PRODUCTOS = [
    # nombre, proveedor, categorías, precio, mayorista pequeño, mayorista grande, costo
    ('Blusa de manta bordada', 'TEX', ['Blusas'], 125, 110, 95, 60),
    ('Blusa casual de algodón', 'TEX', ['Blusas'], 89, 79, 70, 42),
    ('Camisa formal manga larga', 'MODA', ['Blusas'], 149, 135, 120, 75),
    ('Pantalón de lona clásico', 'MODA', ['Pantalones'], 199, 180, 165, 100),
    ('Pantalón de vestir negro', 'MODA', ['Pantalones'], 225, 205, 185, 115),
    ('Short de mezclilla', 'MODA', ['Pantalones'], 115, 100, 90, 55),
    ('Vestido floral de verano', 'TEX', ['Vestidos'], 260, 235, 210, 130),
    ('Vestido de fiesta largo', 'MODA', ['Vestidos'], 450, 410, 370, 230),
    ('Falda típica de corte', 'TEX', ['Vestidos'], 350, 320, 290, 180),
    ('Sandalia de cuero', 'CALZ', ['Calzado'], 175, 160, 145, 85),
    ('Tenis urbanos blancos', 'CALZ', ['Calzado'], 320, 295, 270, 165),
    ('Bota de cuero café', 'CALZ', ['Calzado'], 495, 455, 420, 260),
    ('Bolso tejido artesanal', 'ACC', ['Accesorios'], 180, 165, 150, 90),
    ('Cinturón de cuero', 'ACC', ['Accesorios'], 75, 68, 60, 35),
    ('Aretes de jade', 'ACC', ['Accesorios'], 95, 85, 78, 45),
    ('Bufanda de lana', 'TEX', ['Accesorios', 'Blusas'], 85, 76, 68, 40),
]

CLIENTES = [
    ('Ana Gómez', '+502 4000 1001', 'Prefiere tallas S.'),
    ('Luis Hernández', '+502 4000 1002', ''),
    ('Sofía Ramírez', '+502 4000 1003', 'Compra para su tienda en Antigua.'),
    ('Jorge Castillo', '+502 4000 1004', ''),
    ('Valeria Morales', '+502 4000 1005', 'Avisar cuando lleguen vestidos nuevos.'),
    ('Diego Rodríguez', '+502 4000 1006', ''),
    ('Gabriela Juárez', '+502 4000 1007', 'Cliente mayorista.'),
    ('Fernando Cruz', '+502 4000 1008', ''),
]


class Command(BaseCommand):
    help = 'Carga datos ficticios de una empresa de ropa para probar el sistema.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Borra la empresa existente (y sus usuarios) antes de cargar los datos.')

    def handle(self, *args, **options):
        if Empresa.objects.exists():
            if not options['reset']:
                raise CommandError(
                    'Ya existe una empresa. Usa --reset para borrarla y cargar los datos demo.')
            self._borrar_todo()

        rng = random.Random(2026)
        with transaction.atomic():
            self._cargar(rng)

        self.stdout.write(self.style.SUCCESS('Datos demo cargados.'))
        self.stdout.write(f'  Dueño:      dueno@demo.com / {PASSWORD}')
        for nombre, email, _, pin in VENDEDORES:
            self.stdout.write(f'  Vendedor:   {email} / {PASSWORD} (PIN {pin}) - {nombre}')

    def _borrar_todo(self):
        user_ids = list(PerfilUsuario.objects.values_list('user_id', flat=True))
        # Ventas cuelgan de Sucursal, Pedidos de Empresa: caen en cascada.
        Empresa.objects.all().delete()
        User.objects.filter(id__in=user_ids, is_superuser=False).delete()
        self.stdout.write('Datos anteriores borrados.')

    def _cargar(self, rng):
        ahora = timezone.now()

        empresa = Empresa.objects.create(
            nombre='Modas Lucía', direccion='6a Avenida 10-25, Zona 1', ciudad='Guatemala',
            tipo_negocio='retail', color_tema='purple', onboarding_completo=True)

        # --- Usuarios ---
        dueno_user = User.objects.create_user(
            username='dueno@demo.com', email='dueno@demo.com', password=PASSWORD)
        dueno = PerfilUsuario.objects.create(
            user=dueno_user, email='dueno@demo.com', nombre='Lucía Méndez',
            telefono='+502 5000 0000', empresa=empresa, rol='dueno')

        # --- Sucursales (+ almacén, como hace crear_sucursal) ---
        sucursales = {}
        for nombre, codigo, direccion, ciudad, pv in SUCURSALES:
            s = Sucursal.objects.create(
                empresa=empresa, nombre=nombre, codigo=codigo, direccion=direccion,
                ciudad=ciudad, tiene_punto_venta=pv)
            Almacen.objects.create(sucursal=s, nombre=f'Almacén {s.nombre}')
            sucursales[codigo] = s
        tiendas = [s for s in sucursales.values() if s.tiene_punto_venta]

        vendedores = {}
        for nombre, email, cod_suc, pin in VENDEDORES:
            u = User.objects.create_user(username=email, email=email, password=PASSWORD)
            vendedores[cod_suc] = PerfilUsuario.objects.create(
                user=u, email=email, nombre=nombre, empresa=empresa, rol='vendedor',
                sucursal=sucursales[cod_suc], pin=make_password(pin))

        # --- Catálogos ---
        proveedores = {
            codigo: Proveedor.objects.create(empresa=empresa, nombre=n, codigo=codigo, telefono=t)
            for n, codigo, t in PROVEEDORES
        }
        categorias = {n: Categoria.objects.create(empresa=empresa, nombre=n) for n in CATEGORIAS}
        clientes = [
            Cliente.objects.create(empresa=empresa, nombre=n, telefono=t, notas=notas)
            for n, t, notas in CLIENTES
        ]

        productos = []
        for nombre, cod_prov, cats, precio, may_p, may_g, costo in PRODUCTOS:
            prov = proveedores[cod_prov]
            p = Producto.objects.create(
                empresa=empresa, codigo=siguiente_codigo_producto(prov), nombre=nombre,
                proveedor=prov, precio_venta=Decimal(precio),
                precio_mayorista_pequeno=Decimal(may_p), precio_mayorista_grande=Decimal(may_g),
                costo=Decimal(costo))
            p.categorias.set([categorias[c] for c in cats])
            productos.append(p)

        # --- Inventario inicial (entradas de mercadería) ---
        for p in productos:
            for s in sucursales.values():
                cantidad = rng.randint(40, 70) if s.tiene_punto_venta else rng.randint(80, 150)
                registrar_entrada(
                    empresa=empresa, producto=p, sucursal=s, cantidad=Decimal(cantidad),
                    usuario=dueno, proveedor=p.proveedor, nota='Inventario inicial (demo)')
        Stock.objects.filter(sucursal__empresa=empresa).update(stock_minimo=Decimal(5))

        # --- Ventas de los últimos 12 meses ---
        for _ in range(180):
            sucursal = rng.choice(tiendas)
            operador = rng.choice([dueno, vendedores[sucursal.codigo]])
            cliente = rng.choice(clientes) if rng.random() < 0.6 else None
            venta = Venta.objects.create(sucursal=sucursal, operador=operador, cliente=cliente)
            total = Decimal(0)
            for p in rng.sample(productos, rng.randint(1, 3)):
                cantidad = Decimal(rng.randint(1, 2))
                stock = Stock.objects.get(sucursal=sucursal, producto=p)
                if stock.cantidad - cantidad < 2:
                    continue
                VentaLinea.objects.create(
                    venta=venta, producto=p, cantidad=cantidad, precio_unitario=p.precio_venta)
                registrar_salida(
                    empresa=empresa, producto=p, sucursal=sucursal, cantidad=cantidad,
                    usuario=operador, nota=f'Venta #{venta.pk}')
                total += cantidad * p.precio_venta
            if rng.random() < 0.15:
                VentaLinea.objects.create(
                    venta=venta, descripcion_libre='Arreglo de ruedo', cantidad=Decimal(1),
                    precio_unitario=Decimal(35))
                total += Decimal(35)
            if total == 0:
                venta.delete()
                continue
            # fecha es auto_now_add: se ajusta después para repartir las ventas en el año
            dias = rng.randint(0, 25) if rng.random() < 0.2 else rng.randint(0, 364)
            fecha = ahora - timedelta(days=dias, hours=rng.randint(0, 8), minutes=rng.randint(0, 59))
            Venta.objects.filter(pk=venta.pk).update(total=total, fecha=fecha)

        # un par de productos bajo el mínimo, para la alerta de reportes
        Stock.objects.filter(sucursal=sucursales['CEN'], producto=productos[7]).update(
            cantidad=Decimal(3))
        Stock.objects.filter(sucursal=sucursales['OAK'], producto=productos[11]).update(
            cantidad=Decimal(2))

        # --- Pedidos ---
        for i in range(6):
            completado = i < 3
            creado = ahora - timedelta(days=rng.randint(3, 60))
            pedido = Pedido.objects.create(
                empresa=empresa, cliente=rng.choice(clientes) if i % 3 else None,
                sucursal=rng.choice(tiendas), creado_por=dueno,
                estado='completado' if completado else 'pendiente',
                completado_en=creado + timedelta(days=5) if completado else None)
            Pedido.objects.filter(pk=pedido.pk).update(creado_en=creado)
            for p in rng.sample(productos, rng.randint(1, 4)):
                ya_pedido = completado or rng.random() < 0.5
                PedidoLinea.objects.create(
                    pedido=pedido, producto=p, cantidad=Decimal(rng.randint(2, 10)),
                    precio_unitario=p.precio_venta,
                    ya_pedido=ya_pedido,
                    ya_pedido_en=creado + timedelta(days=1) if ya_pedido else None,
                    recibido='completo' if completado else rng.choice(['no', 'parcial']),
                    recibido_en=creado + timedelta(days=4) if completado else None)
