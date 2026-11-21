from django.conf import settings
from django.core.files.storage import default_storage


def guardar_archivo(carpeta: str, nombre_relativo: str, archivo) -> str:
    """Guarda un archivo subido en MEDIA_ROOT/<carpeta>/<nombre_relativo> y
    devuelve la URL para servirlo. Reemplaza los buckets de Supabase
    Storage: cada "bucket" (productos, logos) es ahora una carpeta dentro
    de media/.
    """
    ruta_guardada = default_storage.save(f'{carpeta}/{nombre_relativo}', archivo)
    return settings.MEDIA_URL + ruta_guardada
