# portafolio

Portafolio de proyectos de análisis de datos de Ángel García, publicado en
[angelgarciadatablog.com/portafolio](https://www.angelgarciadatablog.com/portafolio).

## Cómo funciona

Sitio estático sin build. El nombre del repo forma la URL (mismo patrón que [`links`](https://github.com/angelgarciadatablog/links)).

```
portafolio/
├── index.html                              # grilla de casos
├── assets/
│   ├── portafolio.css                      # estilos de la grilla
│   └── caso.css                            # estilos de la página de caso
├── ecommerce-performance-insights/
│   └── index.html
└── shopify-orders-analysis/
    └── index.html
```

**La identidad visual se hereda del blog**: cada página enlaza
`https://www.angelgarciadatablog.com/assets/styles.css` por URL absoluta, así que las
variables de color y tipografía tienen una sola fuente de verdad. Los CSS de este repo
solo contienen lo propio del portafolio.

## Añadir un caso

1. Crear la carpeta `<slug>/index.html` copiando una existente.
2. Añadir la fila correspondiente en `index.html` con sus `data-cat` y `data-slug`.
3. Si aparece una categoría nueva, añadir su botón de filtro.

**Repo ≠ página publicada.** Los repos de cada análisis contienen el código y los datos;
la narrativa del caso vive aquí. Cada caso tiene una sola URL canónica: `/portafolio/<slug>`.

### Consultas SQL

Van embebidas como `<script type="text/plain" id="…" data-titulo="archivo.sql">` y se abren
en overlay desde cualquier botón con `data-sql="id"`. Añadir otra consulta es pegar el bloque
y su botón, sin tocar el JavaScript.

### Métricas de cada caso

Tres huecos fijos, etiqueta libre: **grano y volumen** · **estructura** (siempre un conteo,
nunca una lista) · **periodo** (siempre tiempo). Si un caso no llena tres huecos honestos,
no lleva fila de métricas.

### Portadas

Son el thumbnail del video de YouTube de cada proyecto, en **16:9**.

## Medición

Contenedor `GTM-KDXJ37SD`, propiedad GA4 `G-S8EKWB6DLM`.

| Página | Evento | Parámetros |
|---|---|---|
| Grilla | `portafolio_filtro` | categoria |
| Grilla | `portafolio_busqueda` | termino |
| Grilla | `portafolio_proyecto_click` | slug, categoria, posicion |
| Caso | `caso_ver_sql` / `caso_copiar_sql` / `caso_descargar_sql` | slug, consulta |
| Caso | `caso_salida` | slug, destino |
