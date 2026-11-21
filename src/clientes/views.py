from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import login_activo_required
from core.services import get_perfil

from .forms import ClienteForm
from .models import Cliente


@login_activo_required
def lista_clientes(request):
    perfil = get_perfil(request)
    clientes = Cliente.objects.filter(empresa=perfil.empresa)
    return render(request, 'clientes/lista.html', {'clientes': clientes, 'perfil': perfil})


@login_activo_required
def crear_cliente(request):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede registrar clientes.')
        return redirect('clientes:lista')

    form = ClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cliente = form.save(commit=False)
        cliente.empresa = perfil.empresa
        cliente.save()
        messages.success(request, f'Cliente "{cliente.nombre}" creado.')
        return redirect('clientes:lista')
    return render(request, 'clientes/crear.html', {'form': form})


@login_activo_required
def editar_cliente(request, pk):
    perfil = get_perfil(request)
    if perfil.rol != 'dueno':
        messages.error(request, 'Solo el dueño puede editar clientes.')
        return redirect('clientes:lista')

    cliente = get_object_or_404(Cliente, pk=pk, empresa=perfil.empresa)
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Cliente "{cliente.nombre}" actualizado.')
        return redirect('clientes:lista')
    return render(request, 'clientes/crear.html', {'form': form, 'cliente': cliente})
