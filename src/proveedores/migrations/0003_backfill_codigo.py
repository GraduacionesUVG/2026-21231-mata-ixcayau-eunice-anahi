from django.db import migrations


def _codigo_desde_nombre(nombre):
    letras = ''.join(ch for ch in nombre.upper() if ch.isalpha())
    return letras[:4] or 'PROV'


def backfill_codigos(apps, schema_editor):
    """Genera un código provisional (derivado del nombre) para los
    proveedores que ya existían antes de que el código fuera obligatorio.
    Queda editable después desde 'Editar proveedor'."""
    Proveedor = apps.get_model('proveedores', 'Proveedor')
    for empresa_id in Proveedor.objects.values_list('empresa_id', flat=True).distinct():
        usados = set(
            Proveedor.objects.filter(empresa_id=empresa_id, codigo__isnull=False)
            .values_list('codigo', flat=True)
        )
        for proveedor in Proveedor.objects.filter(empresa_id=empresa_id, codigo__isnull=True).order_by('id'):
            base = _codigo_desde_nombre(proveedor.nombre)
            candidato = base
            sufijo = 1
            while candidato in usados:
                recorte = base[:max(1, 4 - len(str(sufijo)))]
                candidato = f'{recorte}{sufijo}'
                sufijo += 1
            usados.add(candidato)
            proveedor.codigo = candidato
            proveedor.save(update_fields=['codigo'])


def revertir(apps, schema_editor):
    pass  # no hay nada que deshacer - el campo vuelve a quedar en null en la migración anterior


class Migration(migrations.Migration):

    dependencies = [
        ('proveedores', '0002_proveedor_codigo_nullable'),
    ]

    operations = [
        migrations.RunPython(backfill_codigos, revertir),
    ]
