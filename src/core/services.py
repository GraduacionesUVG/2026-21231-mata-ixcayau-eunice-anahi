from .models import PerfilUsuario


def get_perfil_real(request) -> PerfilUsuario:
    """Perfil de la cuenta con la que se inició sesión, sin importar el operador seleccionado por PIN.

    Cacheado en el objeto request: el decorador, el context processor de la
    nav y la vista lo piden cada uno por su lado, y sin esto cada uno pagaba
    su propia consulta a la base por el mismo registro.
    """
    if not hasattr(request, '_perfil_real_cache'):
        request._perfil_real_cache = PerfilUsuario.objects.select_related('empresa').get(user=request.user)
    return request._perfil_real_cache


def get_perfil(request) -> PerfilUsuario:
    """Perfil efectivo: si hay un operador-vendedor identificado por PIN, sus permisos son los que rigen. Cacheado por request."""
    if not hasattr(request, '_perfil_cache'):
        operador = None
        operador_id = request.session.get('operador_id')
        if operador_id:
            operador = PerfilUsuario.objects.select_related('empresa').filter(
                pk=operador_id, rol='vendedor', activo=True).first()
        request._perfil_cache = operador or get_perfil_real(request)
    return request._perfil_cache
