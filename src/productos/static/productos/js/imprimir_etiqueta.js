// Pide el ZPL de un producto al servidor y lo manda a imprimir con Zebra
// Browser Print. El servidor nunca habla con la impresora - todo esto
// corre en el navegador de quien tiene la impresora conectada (por USB
// o en la misma red), que es donde sí hay forma de llegarle.
(function () {
  function mostrarEstado(el, mensaje, esError) {
    el.textContent = mensaje;
    el.style.color = esError ? '#b02a2a' : '';
  }

  // Browser Print a veces entrega un dispositivo "fantasma" (ej. una
  // entrada vieja de "network :9100" sin impresora real detrás) - sin
  // nombre. Mandarle datos a eso "funciona" (no tira error) pero no
  // imprime nada, así que se trata como si no se hubiera encontrado nada.
  function esDispositivoValido(device) {
    return !!(device && device.name && device.name.trim());
  }

  function enviarZpl(device, zpl, elEstado) {
    device.send(
      zpl,
      function () {
        mostrarEstado(elEstado, 'Etiqueta enviada a "' + device.name + '".', false);
      },
      function (error) {
        mostrarEstado(elEstado, 'La impresora no aceptó la etiqueta: ' + error, true);
      }
    );
  }

  // sin impresora "por defecto" configurada en Browser Print, se busca
  // cualquier impresora disponible (cubre tanto USB como las que están
  // en la red, Browser Print las trata igual)
  function buscarCualquierImpresora(zpl, elEstado) {
    BrowserPrint.getLocalDevices(
      function (listaDispositivos) {
        var validos = (listaDispositivos || []).filter(esDispositivoValido);
        if (!validos.length) {
          mostrarEstado(
            elEstado,
            'No se encontró ninguna impresora lista para imprimir. Revisa en "Browser Print ' +
              'Settings" que tu impresora aparezca con su nombre real (no "network :9100" sin ' +
              'nombre) - si no, instala el driver de Zebra y que la impresora esté encendida ' +
              'y conectada (USB o en la red).',
            true
          );
          return;
        }
        enviarZpl(validos[0], zpl, elEstado);
      },
      function () {
        mostrarEstado(elEstado, 'No se encontró ninguna impresora conectada.', true);
      },
      'printer'
    );
  }

  function elegirDispositivoYEnviar(zpl, elEstado) {
    BrowserPrint.getDefaultDevice(
      'printer',
      function (device) {
        if (esDispositivoValido(device)) {
          enviarZpl(device, zpl, elEstado);
        } else {
          buscarCualquierImpresora(zpl, elEstado);
        }
      },
      function () {
        buscarCualquierImpresora(zpl, elEstado);
      }
    );
  }

  // productoId: id del producto. copias: cuántas etiquetas iguales.
  // elEstado: elemento donde se va mostrando el progreso/errores.
  window.imprimirEtiquetaProducto = function (productoId, copias, elEstado) {
    if (typeof BrowserPrint === 'undefined') {
      mostrarEstado(
        elEstado,
        'Zebra Browser Print no está instalado o no está corriendo en esta computadora.',
        true
      );
      return;
    }

    mostrarEstado(elEstado, 'Generando etiqueta...', false);

    var url = '/productos/etiquetas/zpl/?producto_id=' + encodeURIComponent(productoId) +
      '&copias=' + encodeURIComponent(copias);

    fetch(url)
      .then(function (resp) {
        if (!resp.ok) {
          return resp.text().then(function (texto) {
            throw new Error(texto || 'No se pudo generar la etiqueta.');
          });
        }
        return resp.text();
      })
      .then(function (zpl) {
        mostrarEstado(elEstado, 'Buscando impresora...', false);
        elegirDispositivoYEnviar(zpl, elEstado);
      })
      .catch(function (error) {
        mostrarEstado(elEstado, error.message || 'No se pudo generar la etiqueta.', true);
      });
  };
})();
