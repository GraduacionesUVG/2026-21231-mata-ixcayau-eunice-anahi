# Facil Modera

## Descripción

Sistema web ERP/CRM para pequeños negocios con una o varias sucursales. Permite administrar sucursales, vendedores, productos, proveedores, clientes, inventario, ventas y pedidos, y genera reportes con gráficos y exportación a PDF.

Funcionalidades principales:

- Configuración inicial de la empresa (logo, color de marca, datos del negocio y módulos activos).
- Roles de dueño y vendedor; cada vendedor queda limitado a su sucursal. Cambio rápido de operador por PIN de 4 dígitos.
- Catálogo de productos con códigos generados por proveedor, precios minoristas y mayoristas, e impresión de etiquetas de código de barras (ZPL, impresoras Zebra).
- Escaneo de código de barras con la cámara del dispositivo.
- Inventario por sucursal: entradas de mercadería, transferencias, historial de movimientos y alertas de stock mínimo.
- Registro de ventas con descuento automático de inventario y cierre diario.
- Pedidos con seguimiento de estado por línea (pedido / recibido).
- Contacto directo con clientes y proveedores por WhatsApp.
- Reportes de ventas mensuales, producto más vendido y ventas por sucursal, exportables a PDF.

## Tecnologías Utilizadas

- **Backend:** Python 3.12, Django 5.0
- **Base de datos:** PostgreSQL 17 (psycopg 3)
- **Frontend:** plantillas de Django, HTML, CSS y JavaScript
- **Reportes:** ReportLab (PDF) y Matplotlib (gráficos)
- **Imágenes:** Pillow
- **Código de barras:** html5-qrcode (escaneo) y Zebra Browser Print (impresión ZPL)
- **Despliegue:** Docker y Docker Compose; Gunicorn en producción

## Requisitos Previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose)
- Git

## Instalación

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/eunicean/2026-21231-mata-ixcayau-eunice-anahi.git
   cd 2026-21231-mata-ixcayau-eunice-anahi/src
   ```

2. Crear el archivo de variables de entorno a partir del ejemplo y cambiar las contraseñas:

   ```bash
   cp .env.example .env
   ```

   La contraseña de `POSTGRES_PASSWORD` debe coincidir con la que aparece en `DATABASE_URL`.

3. Construir la imagen y aplicar las migraciones:

   ```bash
   docker compose build
   docker compose run --rm web python manage.py migrate
   ```

4. (Opcional) Cargar datos de prueba:

   ```bash
   docker compose run --rm web python manage.py cargar_datos_demo
   ```

   Crea la empresa ficticia "Modas Lucía" con 3 sucursales, 16 productos, proveedores, clientes, inventario, unas 180 ventas de los últimos 12 meses y pedidos. Para borrar los datos existentes y volver a cargarlos, use `--reset`.

   | Rol | Correo | Contraseña | PIN |
   |---|---|---|---|
   | Dueño | dueno@demo.com | Demo2026! | — |
   | Vendedor (Tienda Central) | vendedor1@demo.com | Demo2026! | 1234 |
   | Vendedor (Tienda Oakland) | vendedor2@demo.com | Demo2026! | 5678 |

## Ejecución

```bash
docker compose up
```

Abrir [http://localhost:8000](http://localhost:8000). Si no se cargaron datos de prueba, la primera pantalla permite crear la cuenta del dueño y configurar la empresa (el sistema admite una empresa por instalación).

Para producción se usa Gunicorn:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Capturas

Las capturas de pantalla del sistema están en [`/capturas`](capturas/) (`captura-01.png` a `captura-29.png`).

## Demo

Video demostrativo: [`/demo/demo.mp4`](demo/demo.mp4)

## Documentación

- Informe final: [`/docs/informe_final.pdf`](docs/informe_final.pdf)
- Consentimiento firmado: [`/docs/consentimiento_firmado.pdf`](docs/consentimiento_firmado.pdf)

## Autores

- Eunice Anahí Mata Ixcayau — Carné 21231
