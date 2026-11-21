// Escaneo de código de barras con la cámara del dispositivo, usando la
// librería html5-qrcode (decodifica en el propio navegador - nada de la
// imagen se manda al servidor). Requiere HTTPS (o localhost): los
// navegadores no dan acceso a la cámara en conexiones HTTP planas.
//
// Uso desde cualquier plantilla: abrirEscanerCodigoBarras(function (codigo) { ... }).
(function () {
  var modal = document.getElementById('modal-escaner');
  var elError = document.getElementById('escaner-error');
  var lector = null;

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = 'block';
  }

  function detener() {
    var lectorActivo = lector;
    lector = null;
    modal.hidden = true;
    if (lectorActivo) {
      lectorActivo.stop().then(function () {
        return lectorActivo.clear();
      }).catch(function () {
        // si ya se habia detenido (ej. doble clic en cancelar), no pasa nada
      });
    }
  }

  document.getElementById('btn-cancelar-escaner').addEventListener('click', detener);
  modal.addEventListener('click', function (e) {
    if (e.target === modal) detener();
  });

  // onDetectado(codigoTexto) se llama una sola vez, con el texto leído del
  // código de barras - el escáner se cierra solo apenas detecta algo.
  window.abrirEscanerCodigoBarras = function (onDetectado) {
    if (typeof Html5Qrcode === 'undefined') {
      alert('No se pudo cargar el lector de códigos de barras (revisa tu conexión a internet).');
      return;
    }
    if (!window.isSecureContext) {
      alert('El navegador solo da acceso a la cámara en conexiones seguras (HTTPS).');
      return;
    }

    elError.style.display = 'none';
    modal.hidden = false;

    lector = new Html5Qrcode('escaner-lector', {
      formatsToSupport: [Html5QrcodeSupportedFormats.CODE_128],
      verbose: false,
    });

    lector.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 260, height: 140 } },
      function (codigoTexto) {
        detener();
        onDetectado(codigoTexto);
      },
      function () {
        // se llama constantemente mientras no encuentra nada en el cuadro -
        // no es un error real, se ignora a propósito
      }
    ).catch(function (error) {
      mostrarError('No se pudo abrir la cámara: ' + error);
    });
  };
})();
