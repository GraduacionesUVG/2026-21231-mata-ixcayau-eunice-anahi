{% autoescape off %}^XA
^PW{{ ancho_puntos }}
^LL{{ alto_puntos }}
^LH0,0
^FO{{ margen_puntos }},{{ nombre_y_puntos }}
^A0N,{{ nombre_alto_puntos }},{{ nombre_alto_puntos }}
^FD{{ nombre }}^FS
^FO{{ margen_puntos }},{{ barcode_y_puntos }}
^BY{{ barcode_modulo_puntos }},{{ barcode_ratio }},{{ barcode_alto_puntos }}
^BCN,{{ barcode_alto_puntos }},Y,N,N
^FD{{ codigo }}^FS
^PQ{{ copias }}
^XZ
{% endautoescape %}