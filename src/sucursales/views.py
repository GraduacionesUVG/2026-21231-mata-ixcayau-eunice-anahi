from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from core.decorators import login_activo_required
from core.services import get_perfil

from .forms import SucursalForm
from .models import Almacen, Sucursal


@login_activo_required
def lista_sucursales(request):
    perfil = get_perfil(request)

    # un vendedor solo ve su propia sucursal
    sucursales = Sucursal.objects.filter(empresa=perfil.empresa).select_related('almacen')
    if perfil.rol == 'vendedor' and perfil.sucursal_id:
        sucursales = sucursales.filter(id=perfil.sucursal_id)

    return render(request, 'sucursales/lista.html', {'sucursales': sucursales, 'perfil': perfil})


@login_activo_required
def crear_sucursal(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede crear sucursales.')
        return redirect('sucursales:lista')

    form = SucursalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            sucursal = form.save(commit=False)
            sucursal.empresa = perfil.empresa
            sucursal.save()
            Almacen.objects.create(sucursal=sucursal, nombre=f'Almacén {sucursal.nombre}')
        messages.success(request, f'Sucursal "{sucursal.nombre}" creada con su almacén.')
        return redirect('sucursales:lista')

    return render(request, 'sucursales/crear.html', {'form': form})
