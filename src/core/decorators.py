from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from .services import get_perfil, get_perfil_real


def login_activo_required(view_func):
    """Como @login_required, pero además corta el acceso si el perfil está desactivado.

    Se valida el perfil real (la cuenta con la que se inició sesión), no el
    operador seleccionado por PIN: desactivar a un operador no debe cerrar la
    sesión real de quien lo tenía identificado.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')

        try:
            perfil = get_perfil_real(request)
        except Exception:
            return redirect('core:login')

        if not perfil.activo:
            logout(request)
            messages.error(request, 'Tu acceso fue desactivado. Contacta al dueño del negocio.')
            return redirect('core:login')

        return view_func(request, *args, **kwargs)
    return _wrapped


def modulo_requerido(campo_modulo, nombre_legible):
    """Corta el acceso si la empresa desactivó este módulo en su configuración."""
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            perfil = get_perfil(request)
            if not getattr(perfil.empresa, campo_modulo):
                messages.error(request, f'El módulo de {nombre_legible} está desactivado para tu empresa.')
                return redirect('core:panel')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorador
