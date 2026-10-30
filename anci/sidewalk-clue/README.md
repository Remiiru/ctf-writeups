# Sidewalk Clue – Writeup

Lo primero que hice fue descomprimir el archivo `sidewalk-clue.zip`. Adentro venían dos cosas: `walk.jpg` y `profile.html`. Este último era un posteo minimalista de una persona llamada "mara" que decía:

> evening loop  
> Camera kept the spot even if I forgot to tag it. Same arch I always cut under when the light goes soft.

Nada más. No había indicios directos del lugar, pero claramente el enfoque estaba en algo llamado "arch", y que ella "corta bajo" — o sea, pasa por debajo. Así que no era un monumento cualquiera, sino uno que se atraviesa. Un arco, literal.

Abrí la imagen con `feh` para ver qué tenía. La foto muestra una vereda de concreto claro, árboles a ambos lados, y al fondo, a la izquierda, una estructura grande de piedra blanca con forma de arco triunfal. No hay letreros, nombres, ni nada escrito. Solo perspectiva urbana. Intenté OCR con `tesseract` por si acaso:

```bash
tesseract walk.jpg stdout
```

No devolvió nada útil. Nada legible. Tampoco había metadatos ocultos en el archivo con `strings` o `binwalk`. Así que seguí con lo obvio: el EXIF.

```bash
exiftool walk.jpg
```

Ahí saltó el GPS:

```
GPS Position: 40° 43' 52.45" N, 73° 59' 49.57" W
```

Convertí eso a decimal:

```bash
echo "40 + 43/60 + 52.45/3600" | bc -l
echo "-(73 + 59/60 + 49.57/3600)" | bc -l
```

Resultado: **40.731236, -73.997103**

Lo metí en OpenStreetMap y caí justo en Washington Square Park, Nueva York. El punto estaba sobre una estructura rectangular en medio de la plaza. Pero, ¿era el arco? El mapa mostraba varios elementos: caminos, bancos, un basurero (sí, `waste_basket`), y un objeto etiquetado como `building=triumphal_arch`.

Hice un reverse geocoding rápido con Nominatim:

```bash
curl "https://nominatim.openstreetmap.org/reverse?format=json&lat=40.731236&lon=-73.997103&zoom=19"
```

La respuesta dio como `display_name` algo como *"Washington Square North, Greenwich Village..."*, pero el objeto principal devuelto fue un `waste_basket` cercano. Clásico falso positivo. No era eso.

Me fijé en los elementos alrededor. El arco está etiquetado como `way` en OSM, no como nodo. Así que abrí OSM en el navegador, zoom 19, y busqué el arco físico. Confirmado: es el **Washington Square Arch**, justo en el centro de la plaza. El punto del GPS caía dentro del polígono del arco, no en la vereda.

Copié el ID del `way` de la URL: `https://www.openstreetmap.org/way/248166269`. Ese era el objeto.

Verifiqué la precisión. Descargué el centroide del `way/248166269` usando Overpass API:

```bash
curl -G "https://overpass-api.de/api/interpreter" --data-urlencode 'data=[out:json];way(248166269);out center;' | jq '.elements[0].center'
```

Resultado:
```json
{
  "lat": 40.7312347,
  "lon": -73.9971025
}
```

Comparé con el EXIF: diferencia de menos de 0.1 metros. No es ruido. Es el mismo punto.

Además, los tags en OSM coinciden con lo que se ve: `historic=monument`, `building=triumphal_arch`, `material=marble`, `height=20.5`. La foto muestra una estructura de piedra clara, alta, con arco central — todo encaja.

El posteo dice "Same arch I always cut under" — y justamente, la gente cruza por debajo del arco para ir de un lado a otro del parque. El ángulo de la foto, desde la vereda, mirando hacia el fondo, con el arco a la izquierda, también calza con la orientación de la entrada sur.

Así que no había duda.

`248166269`