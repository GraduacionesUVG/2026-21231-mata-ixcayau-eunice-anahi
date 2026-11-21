from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.decorators import login_activo_required
from core.models import PerfilUsuario
from core.services import get_perfil, get_perfil_real
from sucursales.models import Sucursal

from .forms import VendedorForm


@login_activo_required
def lista_vendedores(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede ver esta página.')
        return redirect('core:panel')

    vendedores = PerfilUsuario.objects.filter(
        empresa=perfil.empresa, rol='vendedor').select_related('sucursal')
    return render(request, 'usuarios/lista.html', {'vendedores': vendedores})


@login_activo_required
def crear_vendedor(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede crear vendedores.')
        return redirect('usuarios:lista')

    form = VendedorForm(request.POST or None, empresa=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.create_user(username=email, email=email, password=form.cleaned_data['password'])
        except IntegrityError:
            messages.error(request, 'Ya existe una cuenta con ese correo.')
            return render(request, 'usuarios/crear.html', {'form': form})

        PerfilUsuario.objects.create(
            user=user,
            email=email,
            nombre=form.cleaned_data['nombre'],
            empresa=perfil.empresa,
            rol='vendedor',
            sucursal=form.cleaned_data['sucursal'],
            pin=make_password(form.cleaned_data['pin']),
        )
        messages.success(request, f'Vendedor "{form.cleaned_data["nombre"]}" creado.')
        return redirect('usuarios:lista')

    return render(request, 'usuarios/crear.html', {'form': form})


@login_activo_required
@require_http_methods(['POST'])
def toggle_vendedor(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede hacer esto.')
        return redirect('usuarios:lista')

    vendedor = get_object_or_404(PerfilUsuario, pk=pk, empresa=perfil.empresa, rol='vendedor')
    vendedor.activo = not vendedor.activo
    vendedor.save(update_fields=['activo'])
    estado = 'activado' if vendedor.activo else 'desactivado'
    messages.success(request, f'{vendedor.nombre or vendedor.email} quedó {estado}.')
    return redirect('usuarios:lista')


@login_activo_required
def seleccionar_operador(request):
    """Identificación rápida por PIN - no reemplaza el login, solo marca quién opera ahora.

    Se basa siempre en el perfil real (la cuenta con la que se inició
    sesión), no en el operador ya seleccionado, para no quedar atrapada con
    los permisos del último operador elegido.
    """
    perfil = get_perfil_real(request)

    sucursales = None
    sucursal = None
    if perfil.rol == 'dueno':
        sucursales = Sucursal.objects.filter(empresa=perfil.empresa)
        sucursal_id = request.GET.get('sucursal') or request.POST.get('sucursal')
        if sucursal_id:
            sucursal = sucursales.filter(id=sucursal_id).first()
    else:
        sucursal = perfil.sucursal

    vendedores = PerfilUsuario.objects.filter(empresa=perfil.empresa, rol='vendedor', activo=True)
    if sucursal:
        vendedores = vendedores.filter(sucursal=sucursal)
    elif perfil.rol == 'dueno':
        vendedores = PerfilUsuario.objects.none()

    if request.method == 'POST' and request.POST.get('vendedor_id'):
        vendedor = get_object_or_404(
            PerfilUsuario, pk=request.POST['vendedor_id'], empresa=perfil.empresa, rol='vendedor', activo=True)
        pin = request.POST.get('pin', '')
        if not vendedor.pin or not check_password(pin, vendedor.pin):
            messages.error(request, 'PIN incorrecto.')
        else:
            nombre_mostrado = vendedor.nombre or vendedor.email
            request.session['operador_id'] = vendedor.id
            request.session['operador_nombre'] = nombre_mostrado
            messages.success(request, f'Operador identificado: {nombre_mostrado}')
            return redirect('core:panel')

    return render(request, 'usuarios/seleccionar_operador.html', {
        'perfil': perfil,
        'sucursales': sucursales,
        'sucursal': sucursal,
        'vendedores': vendedores,
    })


@login_activo_required
@require_http_methods(['POST'])
def cerrar_operador(request):
    """Cierra la sesión por completo, no solo el operador.

    En un dispositivo compartido de sucursal, dejar la sesión del dueño
    activa al "salir" del operador filtraría datos al siguiente que use el
    equipo - por eso esto termina toda la sesión, igual que el logout normal.
    """
    logout(request)
    messages.success(request, 'Sesión cerrada.')
    return redirect('core:login')
