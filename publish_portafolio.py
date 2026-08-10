"""
Convierte los casos de vault/portafolio/ a HTML estático en este repo.

Mismo patrón que publish.py del repo web: frontmatter + markdown + plantilla
con {{placeholders}}. Lo que cambia es el destino, la plantilla y tres bloques
propios del portafolio.

Uso:
  python publish_portafolio.py                  # publica los status listo o publicado
  python publish_portafolio.py --borrador       # incluye los que estan en-redaccion
  python publish_portafolio.py --slug <slug>    # publica solo uno
"""

import argparse
import html as htmlmod
import re
import sys
from pathlib import Path

import frontmatter
import markdown

# ─── RUTAS ────────────────────────────────────────────────────────────────────
VAULT_PORTAFOLIO = Path.home() / "infinity-memory" / "vault" / "portafolio"
REPO_ROOT        = Path(__file__).parent
TEMPLATE_PATH    = REPO_ROOT / "assets" / "portafolio_template.html"
GRILLA_PATH      = REPO_ROOT / "assets" / "grilla_template.html"
# Los repos de analisis viven fuera de este repo: el frontmatter declara cual y
# el script resuelve la ruta. Asi el vault nunca guarda rutas de usuario.
REPOS_BASE       = Path.home() / "repositorios" / "proyectos"

STATUS_PUBLICABLES = {"listo", "publicado"}
CSS_VERSION        = 7          # subir al tocar caso.css

# Los 15 temas del vault, en el mismo orden y con los mismos nombres que la lista
# madre de vault/datablog/00-index.md. Si cambia alli, cambia aqui.
TEMAS = {
    "google-cloud":     "Google Cloud",
    "aws":              "AWS",
    "azure":            "Azure",
    "git":              "Git",
    "claude-code":      "Claude Code",
    "bash-shell":       "Bash & Shell",
    "python":           "Python",
    "apis":             "APIs",
    "sql":              "SQL",
    "bases-de-datos":   "Bases de datos",
    "portafolio-web":   "Portafolio web",
    "power-bi":         "Power BI",
    "google-analytics": "Google Analytics",
    "hojas-de-calculo": "Hojas de cálculo",
    "formacion":        "Formación",
}

# Botones de la cabecera. Lista CERRADA y en este orden: cada clave es un valor
# de `destino` que GA4 registra al hacer clic, asi que abrirla haria inanalizable
# el dato. Un enlace que no encaje en estos cinco va en el cuerpo como enlace
# normal, no como boton.
#
# La diferencia entre dashboard y demo es CON QUE ESTA HECHO, no si es
# interactivo — un informe de Looker tambien lo es:
#   dashboard  hecho con una herramienta de BI   (Looker Studio, Power BI)
#   demo       hecho con codigo, servido en web  (una app, un sitio)
#   repo       el codigo                          OBLIGATORIO
#   dataset    la fuente, documentada
#   post       el articulo del blog que lo explica
#
# Cada campo admite dos formas:
#   url-dashboard: https://…                     -> boton "Ver dashboard"
#   url-dashboard:
#     - Looker Studio | https://…                -> boton "Ver en Looker Studio"
#     - Power BI | https://…                     -> boton "Ver en Power BI"
ACCIONES = {
    "dashboard": "Ver dashboard",
    "demo":      "Ver demo",
    "repo":      "Ver repositorio",
    "dataset":   "Documentación del dataset",
    "post":      "Leer el artículo",
}

parser = argparse.ArgumentParser()
parser.add_argument("--borrador", action="store_true", help="incluye status en-redaccion")
parser.add_argument("--slug", type=str, help="publica solo el caso con este slug")
args = parser.parse_args()


# ─── BLOQUES PROPIOS ──────────────────────────────────────────────────────────
def resolver_repo(nombre):
    """ecommerce-performance-insights -> ~/repositorios/proyectos/proyecto-<n>/<n>"""
    return REPOS_BASE / f"proyecto-{nombre}" / nombre


def extraer_consultas(cuerpo, repo_consultas, slug):
    """
    ```codigo
    archivo: queries/crear-tablas.sql
    texto: Ver el script          (opcional)
    ```
    Para lo que NO cabe en la pagina: scripts largos, .py, .sh, notebooks. El
    contenido no se copia al vault, se lee del repo del caso al publicar, asi
    que pagina y repo no pueden divergir. Si el archivo no existe, aborta.

    Lo corto va en un bloque ```sql normal, dentro del markdown. La regla es la
    longitud: hasta unas quince lineas se lee mejor en el sitio.

    `consulta` se mantiene como alias de `codigo` por los casos ya escritos.
    """
    # El texto por defecto del boton depende de lo que sea el archivo
    TEXTO_POR_EXTENSION = {
        ".sql": "Ver consulta", ".py": "Ver el script", ".sh": "Ver el script",
        ".ipynb": "Ver el notebook",
    }
    bloques = []

    def sustituir(m):
        campos = dict(
            (k.strip(), v.strip())
            for k, v in (l.split(":", 1) for l in m.group(1).strip().split("\n") if ":" in l)
        )
        ruta_rel = campos["archivo"]
        texto    = campos.get("texto") or TEXTO_POR_EXTENSION.get(
                       Path(ruta_rel).suffix.lower(), "Ver el código")

        ruta = resolver_repo(repo_consultas) / ruta_rel
        if not ruta.exists():
            sys.exit(f"✗ {slug}: no existe {repo_consultas}/{ruta_rel}")

        sql_id = f"sql-{len(bloques) + 1:02d}"
        sql    = ruta.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
        bloques.append(
            f'<script type="text/plain" id="{sql_id}" data-titulo="{ruta.name}">\n{sql}</script>'
        )
        return f'<button class="cs-boton" data-sql="{sql_id}">{texto}</button>'

    cuerpo = re.sub(r"```(?:codigo|consulta)\n(.*?)```", sustituir, cuerpo, flags=re.S)
    return cuerpo, "\n\n".join(bloques)


def convertir_flujo(cuerpo):
    """
    ```flujo
    GA4 | Export crudo | 4.3M eventos
    ```
    """
    def sustituir(m):
        pasos = []
        for linea in m.group(1).strip().split("\n"):
            partes = [p.strip() for p in linea.split("|")]
            herramienta = partes[0]
            dato = "<br />".join(partes[1:])
            pasos.append(
                '<div class="cs-flujo-paso">'
                f'<span class="cs-flujo-tool">{herramienta}</span>'
                f'<span class="cs-flujo-dato">{dato}</span>'
                "</div>"
            )
        return '<div class="cs-flujo">\n' + "\n".join(pasos) + "\n</div>"

    return re.sub(r"```flujo\n(.*?)```", sustituir, cuerpo, flags=re.S)


# Callouts nativos de Obsidian -> bloques del caso. Para añadir uno nuevo basta
# una entrada aquí y su regla en caso.css.
CALLOUTS = {
    "aviso":    "cs-aviso",
    "pregunta": "cs-pregunta-bloque",
    "hallazgo": "cs-hallazgo",
}


def convertir_callouts(cuerpo):
    """`> [!aviso]` y `> [!pregunta]`, que en Obsidian se ven como callouts."""
    def sustituir(m):
        tipo = m.group(1)
        clase = CALLOUTS[tipo]
        lineas = [re.sub(r"^>\s?", "", l) for l in m.group(0).split("\n")][1:]
        parrafos = "\n".join(f"<p>{p}</p>" for p in "\n".join(lineas).split("\n\n") if p.strip())
        return f'<div class="{clase}">\n{parrafos}\n</div>'

    tipos = "|".join(CALLOUTS)
    return re.sub(rf"^> \[!({tipos})\]\n(?:^>.*\n?)*", sustituir, cuerpo, flags=re.M)


# ─── CABECERA ─────────────────────────────────────────────────────────────────
def leer_metricas(meta):
    """
    metricas:
      - 4.3M | eventos
    Lista de textos planos para que Obsidian pueda editarla desde el panel de
    propiedades. Tres huecos con significado fijo: grano y volumen, estructura,
    periodo. Si un caso no llena los tres de forma honesta, se deja vacio.
    """
    pares = []
    for linea in meta.get("metricas") or []:
        if "|" not in str(linea):
            sys.exit(f"✗ métrica sin separador '|': {linea}")
        valor, etiqueta = (p.strip() for p in str(linea).split("|", 1))
        pares.append((valor, etiqueta))
    return pares


def render_metricas(pares, clase="cs"):
    if not pares:
        return ""
    huecos = "".join(
        f'<div class="{clase}-metrica"><b>{v}</b><span>{etq}</span></div>' for v, etq in pares
    )
    return f'<div class="{clase}-metricas">{huecos}</div>'


def leer_stack(meta, slug):
    """
    stack:
      - Google Cloud     <- coincide con un tema: filtra
      - SQL              <- coincide con un tema: filtra
      - JavaScript       <- no es tema: solo se muestra

    Un solo campo. Lo que coincide con un tema hace funcionar el filtro; lo que
    no, se muestra igual. El detalle fino (BigQuery dentro de Google Cloud) lo
    resuelve el buscador por texto, no la barra de temas.
    """
    por_nombre = {nombre.lower(): slug_tema for slug_tema, nombre in TEMAS.items()}
    herramientas, temas = [], []

    for linea in meta.get("stack") or []:
        herramienta = str(linea).strip()
        herramientas.append(herramienta)
        tema = por_nombre.get(herramienta.lower())
        if tema:
            temas.append(tema)

    if not temas:
        sys.exit(f"✗ {slug}: el stack no incluye ningún tema, el caso no sería filtrable. "
                 f"Temas válidos: {', '.join(TEMAS.values())}")
    return herramientas, temas


def render_stack(meta, slug):
    return " · ".join(leer_stack(meta, slug)[0])


def render_acciones(meta, slug):
    """Un campo plano por destino: url-dashboard, url-demo, url-repo, url-dataset, url-post."""
    if not meta.get("url-repo"):
        sys.exit(f"✗ {slug}: falta url-repo. Todo caso del portafolio tiene su repo.")

    desconocidos = [k for k in meta if k.startswith("url-") and k[4:] not in ACCIONES]
    if desconocidos:
        sys.exit(f"✗ {slug}: enlace no estándar {desconocidos}. "
                 f"Válidos: {', '.join('url-' + a for a in ACCIONES)}")

    enlaces = ""
    for destino, texto_por_defecto in ACCIONES.items():
        valor = meta.get(f"url-{destino}")
        if not valor:
            continue

        # Una sola URL, o varias con su etiqueta: "Looker Studio | https://…"
        entradas = valor if isinstance(valor, list) else [valor]
        for entrada in entradas:
            entrada = str(entrada).strip()
            if "|" in entrada:
                etiqueta, url = (x.strip() for x in entrada.split("|", 1))
                texto = f"Ver en {etiqueta}"
            else:
                url, texto = entrada, texto_por_defecto
            if not url.startswith("http"):
                sys.exit(f"✗ {slug}: url-{destino} no parece una URL: {url}")
            enlaces += (
                f'<a class="cs-accion" href="{url}" target="_blank" '
                f'data-destino="{destino}">{texto} <span>&#8599;</span></a>'
            )

    return f'<div class="cs-acciones">{enlaces}</div>' if enlaces else ""


def render_video(url):
    if not url:
        return '<div class="cs-video"><div class="cs-video-vacio">video del proyecto</div></div>'
    vid = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not vid:
        return ""
    return (
        '<div class="cs-video"><iframe src="https://www.youtube.com/embed/'
        f'{vid.group(1)}" title="Video del proyecto" frameborder="0" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
    )


# ─── SALIDA ───────────────────────────────────────────────────────────────────
def tabla_etiqueta_valor(html):
    """
    Una tabla markdown con la fila de cabecera vacia (`| | |`) es una tabla de
    etiqueta y valor, no de columnas. Se le quita el thead vacio y la primera
    celda de cada fila pasa a <th>, que es como se ven las fichas de datos.
    """
    def sustituir(m):
        tabla = m.group(0)
        cabecera = re.search(r"<thead>.*?</thead>", tabla, flags=re.S)
        if not cabecera or re.sub(r"</?(thead|tr|th)>|\s", "", cabecera.group(0)):
            return tabla                      # la cabecera tiene texto: se respeta
        tabla = tabla.replace(cabecera.group(0), "")
        tabla = re.sub(r"<tr>\s*<td>(.*?)</td>", r"<tr>\n<th>\1</th>", tabla, flags=re.S)
        return tabla

    return re.sub(r'<table class="cs-tabla">.*?</table>', sustituir, html, flags=re.S)


def postprocesar(html):
    """Retoques sobre el HTML que genera markdown."""
    html = html.replace("<table>", '<table class="cs-tabla">')
    html = tabla_etiqueta_valor(html)
    # Un parrafo que solo contiene una imagen pasa a figura con pie
    html = re.sub(
        r'<p><img alt="([^"]*)" src="([^"]+)"\s*/?></p>',
        r'<figure><img src="\2" alt="\1" loading="lazy" /><figcaption>\1</figcaption></figure>',
        html,
    )
    return html


def publicar(ruta_md, plantilla):
    post = frontmatter.load(ruta_md)
    meta, cuerpo = post.metadata, post.content

    slug = meta.get("slug") or ruta_md.stem
    if args.slug and args.slug != slug:
        return None
    status = meta.get("status", "")
    if status not in STATUS_PUBLICABLES and not args.borrador:
        return None

    cuerpo = convertir_callouts(cuerpo)
    cuerpo = convertir_flujo(cuerpo)
    cuerpo, bloques_sql = extraer_consultas(cuerpo, meta.get("repo-consultas", ""), slug)

    md = markdown.Markdown(extensions=["fenced_code", "tables"])
    contenido = postprocesar(md.convert(cuerpo))

    html = plantilla
    for clave, valor in {
        "{{titulo}}":           meta.get("titulo", slug),
        "{{descripcion}}":      meta.get("descripcion", ""),
        "{{categoria_nombre}}": render_stack(meta, slug),
        "{{pregunta}}":         meta.get("pregunta", ""),
        "{{acciones}}":         render_acciones(meta, slug),
        "{{metricas}}":         render_metricas(leer_metricas(meta)),
        "{{video}}":            render_video(meta.get("video-youtube")),
        "{{contenido}}":        contenido,
        "{{bloques_sql}}":      bloques_sql,
        "{{slug}}":             slug,
    }.items():
        html = html.replace(clave, valor)

    html = re.sub(r"caso\.css\?v=\d+", f"caso.css?v={CSS_VERSION}", html)

    destino = REPO_ROOT / slug
    destino.mkdir(exist_ok=True)
    (destino / "index.html").write_text(html, encoding="utf-8")
    return slug, len(bloques_sql.split("</script>")) - 1, meta


# ─── GRILLA ───────────────────────────────────────────────────────────────────
def render_card(meta, slug):
    portada = meta.get("portada")
    thumb = (
        f'<img src="{portada}" alt="{meta.get("titulo", "")}" loading="lazy" />'
        if portada
        else '<div class="pf-thumb-vacia">portada del caso</div>'
    )
    bloque_metricas = render_metricas(leer_metricas(meta), clase="pf")

    return f"""    <a class="pf-card" data-slug="{slug}" data-temas="{' '.join(leer_stack(meta, slug)[1])}"
       href="{slug}/">
      <div class="pf-thumb">{thumb}</div>
      <div class="pf-body">
        <div class="pf-cat">{render_stack(meta, slug)}</div>
        <h2>{meta.get('titulo', slug)}</h2>
        <p class="pf-pregunta">{meta.get('pregunta', '')}</p>
        <p class="pf-desc">{meta.get('resumen', meta.get('descripcion', ''))}</p>
        {bloque_metricas}
        <div class="pf-pie">
          <span class="pf-cta">Ver caso &rarr;</span>
        </div>
      </div>
    </a>"""


def render_temas(casos):
    """
    Los 15 temas siempre visibles con su numero de proyectos. Los que estan a
    cero se ven apagados y no filtran: un tema sin proyecto es informacion — es
    el hueco — y ocultarlo convertiria el mapa en decoracion.
    """
    conteo = {slug_tema: 0 for slug_tema in TEMAS}
    for meta, slug in casos:
        for tema in leer_stack(meta, slug)[1]:
            conteo[tema] += 1

    filas = [
        '      <span class="pf-temas-titulo">Temas</span>',
        f'      <button class="pf-tema activo" data-tema="todos">'
        f'Todos<span class="pf-tema-n">{len(casos)}</span></button>',
    ]
    for slug_tema, nombre in TEMAS.items():
        nombre = htmlmod.escape(nombre)
        n = conteo[slug_tema]
        if n:
            filas.append(f'      <button class="pf-tema" data-tema="{slug_tema}">'
                         f'{nombre}<span class="pf-tema-n">{n}</span></button>')
        else:
            filas.append(f'      <span class="pf-tema vacio">'
                         f'{nombre}<span class="pf-tema-n">0</span></span>')
    return "\n".join(filas)


def generar_grilla(casos):
    """casos: lista de (meta, slug), ya filtrada y ordenada."""
    cards = "\n\n".join(render_card(meta, slug) for meta, slug in casos)

    n = len(casos)
    html = GRILLA_PATH.read_text(encoding="utf-8")
    html = html.replace("{{cards}}", cards)
    html = html.replace("{{temas}}", render_temas(casos))
    html = html.replace("{{contador}}", f"{n} caso{'s' if n != 1 else ''}")
    (REPO_ROOT / "index.html").write_text(html, encoding="utf-8")
    return n


# ─── MAIN ─────────────────────────────────────────────────────────────────────
plantilla = TEMPLATE_PATH.read_text(encoding="utf-8")
casos = []

for ruta in sorted(VAULT_PORTAFOLIO.glob("*.md")):
    if ruta.name.startswith("00-"):
        continue
    resultado = publicar(ruta, plantilla)
    if resultado:
        slug, n_consultas, meta = resultado
        print(f"✓ {slug}/index.html  ({n_consultas} consultas)")
        casos.append((meta, slug))

if not casos:
    print("Nada que publicar. Usa --borrador para incluir los que estan en-redaccion.")
    raise SystemExit

# Mas reciente arriba, misma convencion que el indice del blog
casos.sort(key=lambda c: str(c[0].get("updated", "")), reverse=True)
print(f"✓ index.html  (grilla con {generar_grilla(casos)} casos)")
