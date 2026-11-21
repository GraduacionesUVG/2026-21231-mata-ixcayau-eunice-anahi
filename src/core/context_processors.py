from django.conf import settings

from .services import get_perfil

NO_HOME_LINK_VIEWS = {'panel', 'onboarding_marca', 'onboarding_negocio', 'onboarding_modulos', None}
SIDEBAR_HIDDEN_VIEWS = {'onboarding_marca', 'onboarding_negocio', 'onboarding_modulos', None}
DESIGN_CSS_PATH = settings.BASE_DIR / 'core' / 'static' / 'core' / 'css' / 'design.css'


def nav(request):
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', None)
    context = {
        'show_home_link': url_name not in NO_HOME_LINK_VIEWS,
        'show_sidebar': url_name not in SIDEBAR_HIDDEN_VIEWS,
        'app_actual': getattr(resolver_match, 'app_name', None),
    }

    if settings.DEBUG:
        # versiona el CSS por su fecha de modificación real (no por request):
        # el navegador lo recarga solo cuando el archivo cambió de verdad,
        # en vez de en cada navegación. runserver no reinicia por cambios en
        # .css, así que esto se recalcula por request - es un stat() local,
        # no pesa nada.
        try:
            context['design_css_version'] = int(DESIGN_CSS_PATH.stat().st_mtime)
        except OSError:
            context['design_css_version'] = None

    if request.user.is_authenticated:
        try:
            perfil = get_perfil(request)
            context['perfil'] = perfil
            context['empresa'] = perfil.empresa
        except Exception:
            context['perfil'] = None

    return context
