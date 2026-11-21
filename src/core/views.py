from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .decorators import login_activo_required
from .forms import DatosPersonalesForm, EmpresaSettingsForm, LoginForm, MarcaForm, ModulosForm, NegocioForm, SignupForm
from .models import Empresa, PerfilUsuario
from .services import get_perfil, get_perfil_real
from .storage import guardar_archivo


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:panel')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # username == email por convención propia (ver crear_vendedor/signup_view)
        user = authenticate(
            request, username=form.cleaned_data['email'], password=form.cleaned_data['password'])
        if user is None:
            messages.error(request, 'Correo o contraseña incorrectos.')
            return render(request, 'core/login.html', {'form': form})
        login(request, user)
        return redirect('core:panel')

    return render(request, 'core/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('core:panel')

    # Facil Modera es de una sola empresa por instalación - esta pantalla
    # solo sirve para la configuración inicial. En cuanto existe una
    # empresa, queda inhabilitada para siempre, sin importar quién la pida.
    if Empresa.objects.exists():
        messages.error(request, 'Ya existe una empresa configurada. Inicia sesión.')
        return redirect('core:login')

    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.create_user(
                username=email, email=email, password=form.cleaned_data['password'])
        except IntegrityError:
            messages.error(request, 'Ya existe una cuenta con ese correo.')
            return render(request, 'core/signup.html', {'form': form})

        empresa = Empresa.objects.create(nombre=form.cleaned_data['nombre_negocio'])
        PerfilUsuario.objects.create(
            user=user, email=email, nombre=form.cleaned_data['nombre'], empresa=empresa, rol='dueno')
        login(request, user)
        messages.success(request, 'Cuenta creada.')
        return redirect('core:panel')

    return render(request, 'core/signup.html', {'form': form})


@require_http_methods(['POST'])
def logout_view(request):
    # logout() ya limpia/rota la sesión completa (incluye el operador
    # seleccionado por PIN), no hace falta pop-ear claves sueltas.
    logout(request)
    return redirect('core:login')


@login_activo_required
def onboarding_marca(request):
    perfil = get_perfil(request)
    empresa = perfil.empresa
    form = MarcaForm(request.POST or None, request.FILES or None, instance=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        _subir_logo_si_aplica(request, empresa, form.cleaned_data.get('logo'))
        return redirect('core:onboarding_negocio')
    return render(request, 'core/onboarding_marca.html', {'form': form, 'empresa': empresa})


@login_activo_required
def onboarding_negocio(request):
    perfil = get_perfil(request)
    form = NegocioForm(request.POST or None, instance=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('core:onboarding_modulos')
    return render(request, 'core/onboarding_negocio.html', {'form': form})


@login_activo_required
def onboarding_modulos(request):
    perfil = get_perfil(request)
    form = ModulosForm(request.POST or None, instance=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        empresa = form.save(commit=False)
        empresa.onboarding_completo = True
        empresa.save()
        messages.success(request, 'Configuración completada.')
        return redirect('core:panel')
    return render(request, 'core/onboarding_modulos.html', {'form': form})


@login_activo_required
def panel(request):
    perfil = get_perfil(request)
    empresa = perfil.empresa

    if not empresa.onboarding_completo:
        return redirect('core:onboarding_marca')

    # el dueño aterriza en reportes al abrir el programa; el vendedor (sin
    # acceso a reportes) sigue viendo la grilla de módulos. Si Reportes está
    # desactivado, el dueño también cae a la grilla (si no, redirigiría a una
    # vista bloqueada por @modulo_requerido, que a su vez redirige aquí -
    # un ciclo infinito).
    if perfil.rol == 'dueno' and empresa.modulo_reportes:
        return redirect('reportes:dashboard')

    tarjetas = [
        {'nombre': 'Clientes', 'activo': empresa.modulo_clientes, 'disponible': True, 'url_name': 'clientes:lista'},
        {'nombre': 'Productos', 'activo': empresa.modulo_productos, 'disponible': True, 'url_name': 'productos:lista'},
        {'nombre': 'Inventario', 'activo': empresa.modulo_inventario, 'disponible': True, 'url_name': 'inventario:dashboard'},
        {'nombre': 'Ventas', 'activo': empresa.modulo_ventas, 'disponible': True, 'url_name': 'ventas:lista'},
    ]
    # Reportes es solo del dueño (ver el redirect de arriba) - no lo listamos
    # para quien de cualquier forma no puede abrirlo.
    if perfil.rol == 'dueno':
        tarjetas.append(
            {'nombre': 'Reportes', 'activo': empresa.modulo_reportes, 'disponible': True, 'url_name': 'reportes:dashboard'})
    return render(request, 'core/panel.html', {'empresa': empresa, 'tarjetas': tarjetas})


@login_activo_required
def editar_empresa(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede editar la configuración de la empresa.')
        return redirect('core:panel')

    empresa = perfil.empresa
    form = EmpresaSettingsForm(request.POST or None, request.FILES or None, instance=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        _subir_logo_si_aplica(request, empresa, form.cleaned_data.get('logo'))
        messages.success(request, 'Configuración de la empresa actualizada.')
        return redirect('core:editar_empresa')
    return render(request, 'core/editar_empresa.html', {'form': form, 'empresa': empresa})


@login_activo_required
def mi_perfil(request):
    # siempre la identidad real, aunque haya un operador seleccionado por
    # PIN: "mi perfil" es de quien inició sesión, no de a quién se identificó.
    perfil = get_perfil_real(request)
    return render(request, 'core/mi_perfil.html', {'perfil': perfil})


@login_activo_required
def editar_datos_personales(request):
    perfil = get_perfil_real(request)
    form = DatosPersonalesForm(
        request.POST or None, initial={'nombre': perfil.nombre, 'telefono': perfil.telefono})
    if request.method == 'POST' and form.is_valid():
        perfil.nombre = form.cleaned_data['nombre']
        perfil.telefono = form.cleaned_data['telefono']
        perfil.save(update_fields=['nombre', 'telefono'])
        messages.success(request, 'Datos personales actualizados.')
        return redirect('core:mi_perfil')
    return render(request, 'core/editar_datos_personales.html', {'form': form})


def _subir_logo_si_aplica(request, empresa, logo):
    if not logo:
        return
    # el logo es opcional, así que un fallo aquí no debe tumbar el onboarding
    try:
        empresa.logo_url = guardar_archivo('logos', f'{empresa.id}/logo_{logo.name}', logo)
        empresa.save(update_fields=['logo_url'])
    except Exception as exc:
        messages.warning(
            request,
            f'No se pudo subir el logo ({exc}). Puedes seguir sin logo por '
            'ahora y volver a intentarlo después.',
        )
