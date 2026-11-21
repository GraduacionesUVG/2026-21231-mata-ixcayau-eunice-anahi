from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import login_activo_required
from core.services import get_perfil

from .forms import ProveedorForm
from .models import Proveedor


@login_activo_required
def lista_proveedores(request):
    perfil = get_perfil(request)
    proveedores = Proveedor.objects.filter(empresa=perfil.empresa)
    return render(request, 'proveedores/lista.html', {'proveedores': proveedores, 'perfil': perfil})


@login_activo_required
def crear_proveedor(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede crear proveedores.')
        return redirect('proveedores:lista')

    form = ProveedorForm(request.POST or None, empresa=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        proveedor = form.save(commit=False)
        proveedor.empresa = perfil.empresa
        proveedor.save()
        messages.success(request, f'Proveedor "{proveedor.nombre}" creado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/crear.html', {'form': form})


@login_activo_required
def editar_proveedor(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede editar proveedores.')
        return redirect('proveedores:lista')

    proveedor = get_object_or_404(Proveedor, pk=pk, empresa=perfil.empresa)
    form = ProveedorForm(request.POST or None, instance=proveedor, empresa=perfil.empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/crear.html', {'form': form, 'proveedor': proveedor})
