import os, json, re, unicodedata
from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

# --- SDK nuevo o legacy ---
NEW_SDK = True
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
except Exception:
    import openai as oai
    oai.api_key = os.environ["OPENAI_API_KEY"]
    NEW_SDK = False

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")  # usa "gpt-5" si necesitás más recall

# --- Catálogos (recortados aquí; usa los tuyos completos) ---
BARRIOS_ASU = [
    'villa-morra','recoleta','carmelitas','las-lomas','las-mercedes','mburucuya','jara','sajonia','villa-aurelia',
    'ycua-sati','banco-san-miguel','bañado-cara-cara','bernardino-caballero','obrero','bella-vista','Botanico',
    'cañada-del-ybyray','carlos-a-lopez','catedral','ciudad-nueva','dr-francia','la-encarnación','general-diaz',
    'herrera','hipodromo','ita-enramada','ita-pyta-punta','jukyty','los-laureles','loma-pyta','madame-lynch',
    'manora','mcal-estigarribia','mcal-lopez','mbocayaty','mburicao','nazareth','ñu-guazu','panambi-reta',
    'panambi-vera','pettirossi','pinoza','pirizal','republicano','chacarita','roberto-l-pettit','salvador-del-mundo',
    'san-antonio','san-blas','san-cayetano','san-cristobal','san-jorge','san-juan','san-pablo','san-roque','san-vicente',
    'santa-ana','santa-librada','santa-maria','santa-rosa','santisima-trinidad','santo-domingo','silvio-pettirossi',
    'tablada-nueva','tacumbu','tembetary','terminal','virgen-de-fatima','virgen-de-la-asuncion','virgen-del-huerto',
    'vista-alegre','ytay','zeballos-cue'
]
CIUDADES = [
    'asuncion','luque','ciudad-del-este','encarnacion','san-lorenzo','fernando-de-la-mora','mariano-roque-alonso',
    'san-bernardino','lambare','capiata','nemby', # ... (completa con tu catálogo)
]

AMENIDADES_OPC = [
    'Acceso controlado','Área de coworking','Área de parrilla','Área de yoga','Área verde','Bar','Bodega',
    'Cancha de pádel','Cancha de tenis','Cancha de fútbol','Cerradura digital','Cine','Club house',
    'Estacionamiento techado','Generador','Gimnasio','Laguna artificial','Laguna natural','Lavandería',
    'Parque infantil','piscina','Quincho','Salón de eventos','Sala de juegos','Sala de masajes',
    'Sala de reuniones','Sauna','Seguridad 24/7','Solarium','Spa','Terraza','Wi-Fi','Café','Business center'
]

# --- Utils ubicación: slugify y extracción de pistas ---
def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s\-./]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s

def _extract_location_hints(text: str) -> Dict[str, Optional[str]]:
    """
    Busca líneas típicas y arma una 'ubicacion_sugerida' + slugs.
    Soporta: Dirección/Direccion/Address, Municipio, Departamento, País/Pais.
    """
    lines = text.splitlines()
    vals = {"direccion": None, "municipio": None, "departamento": None, "pais": None}

    patterns = {
        "direccion": r"^(?:Direcci[oó]n|Address)\s*:\s*(.+)$",
        "municipio": r"^(?:Municipio)\s*:\s*(.+)$",
        "departamento": r"^(?:Departamento)\s*:\s*(.+)$",
        "pais": r"^(?:Pa[ií]s)\s*:\s*(.+)$",
    }

    for ln in lines:
        ln = ln.strip()
        for key, pat in patterns.items():
            m = re.match(pat, ln, flags=re.IGNORECASE)
            if m:
                vals[key] = m.group(1).strip(" -")
    # Construye ubicación sugerida
    parts = []
    if vals["direccion"]:
        parts.append(vals["direccion"])
    if vals["municipio"]:
        parts.append(vals["municipio"])
    if vals["departamento"]:
        parts.append(vals["departamento"])
    if vals["pais"]:
        parts.append(vals["pais"])
    ubicacion_sugerida = ", ".join([p for p in parts if p])

    # Inferencias de slugs:
    ciudad_slug = None
    barrio_slug = None

    # Si el departamento dice "Asunción", trátalo como ciudad 'asuncion'
    if vals["departamento"] and _slugify(vals["departamento"]) in ("asuncion",):
        ciudad_slug = "asuncion"

    # Si hay municipio y estamos en Asunción, intenta mapear a barrio
    if vals["municipio"]:
        cand = _slugify(vals["municipio"])
        if cand in BARRIOS_ASU:
            barrio_slug = cand
            if not ciudad_slug:
                ciudad_slug = "asuncion"

    return {
        "ubicacion_sugerida": ubicacion_sugerida or None,
        "ciudad_sugerida": ciudad_slug,
        "barrio_sugerido": barrio_slug,
    }

# --- Prompt reforzado (reglas de UBICACION) ---
SYSTEM_PROMPT = r"""
Eres un EXTRACTOR de datos inmobiliarios experto. Devuelve SOLO un objeto JSON (sin markdown) con el esquema exacto.
Reglas clave:
- NO agregues campos extra. Usa null si no hay dato, pero intenta INFERIR antes.
- Normaliza sinónimos (pileta→piscina; depto→departamentos; cochera/garaje→cochera).
- Si aparece un barrio clásico de Asunción (villa morra, recoleta, carmelitas, las lomas, etc.) sin ciudad, set `ciudades='asuncion'` y `barrioasu` con el slug.
- Números: extrae y normaliza (m², m2, mts2).
- Precio: si está en USD, `divisa='$'`. Si está en Gs, convierte a USD con 1 USD = 7300 Gs (redondea) y pon `divisa='$'`.

REGLAS **UBICACION** (muy importante):
1) Si el texto contiene un bloque de **Dirección/Direccion/Address**, JAMÁS dejes `ubicacion` en null.
2) Construye la dirección concatenando en este orden cuando existan: 
   [Dirección], [Municipio o barrio/zona], [Ciudad], [País]. 
   Ejemplo: "Av. X esq. Y - Edificio Z, Las Lomas, Asunción, Paraguay".
3) Considera que en estos portales “Municipio” suele equivaler a **barrio** dentro de Asunción. 
   Si `Municipio=Las Lomas` → `barrioasu='las-lomas'` y `ciudades='asuncion'`.
4) Mantén el texto literal de “Dirección” (no reescribas la calle ni el edificio), solo normaliza abreviaturas comunes como "esq."→"esq." (déjala igual si ya viene).
5) Si hay varias piezas dispersas (Dirección/Municipio/Departamento/País), **únelas** en la `ubicacion`.

Campos y formato JSON EXACTO:
{
  "operacion": "venta|alquiler",
  "tipodepropiedad": "casas|departamentos|duplex|terrenos|oficinas|locales|edificios|paseos|depositos|quintas|estancias",
  "ciudades": "slug de ciudad",
  "barrioasu": "slug si es Asunción; de lo contrario null",
  "precio": integer|null,
  "Barrio": string|null,
  "habitaciones": "['1','2','3','4','5','6','7','8','9','10','monoambiente','+10']"|null,
  "banos": "['1','2','3','4','5','6','7','8','9','10','+10']"|null,
  "cocheras": "['1','2','3','4','5','6','7','8','9','10','+10']"|null,
  "plantas": "['1','2','3','4','5','+5']"|null,
  "m2": integer|null,
  "anno_construccion": integer|null,
  "datosia": string,
  "hectareas": integer|null,
  "m2t": integer|null,
  "m2c": integer|null,
  "asesor": string|null,
  "numeroasesor": string|null,
  "estado": "A estrenar|Perfecto|Muy bueno|Bueno"|null,
  "amenidades": array|null,
  "amoblado": "Sí|No"|null,
  "descripcion": string,
  "nombredeledificio": string|null,
  "piso": string|null,
  "estilo": "Moderna|Minimalista|Clásica|De campo"|null,
  "divisa": "GS|$"|null,
  "ubicacion": "dirección estilo portal (concatenada según reglas)"
}
"""

# Para pasar el catálogo sin pegarlo completo
CIUDADES_CTX = ", ".join(CIUDADES + ["..."])
BARRIOS_CTX  = ", ".join(BARRIOS_ASU[:10] + ["..."])  # muestra parcial

app = FastAPI()

class Req(BaseModel):
    description: str

def _chat_completion_json(description: str, model: str) -> Dict[str, Any]:
    hints = _extract_location_hints(description)
    # Hints explícitos que el modelo debe priorizar
    hints_text = (
        "PISTAS DETECTADAS (USARLAS SIEMPRE SI EXISTEN):\n"
        f"- ubicacion_sugerida: {hints.get('ubicacion_sugerida')}\n"
        f"- ciudad_sugerida_slug: {hints.get('ciudad_sugerida')}\n"
        f"- barrioasu_sugerido_slug: {hints.get('barrio_sugerido')}\n"
    )

    user_content = (
        "Descripción de entrada:\n" + description + "\n\n" +
        hints_text + "\n" +
        "Catálogo ciudades (slugs válidos):\n" + CIUDADES_CTX + "\n\n" +
        "Catálogo barrios Asunción (slugs válidos):\n" + BARRIOS_CTX + "\n\n" +
        "Responde SOLO con el JSON solicitado."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    if NEW_SDK:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0, max_tokens=2000,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content
    else:
        resp = oai.ChatCompletion.create(
            model=model, messages=messages, temperature=0, max_tokens=2000,
            response_format={"type": "json_object"},
        )
        text = resp["choices"][0]["message"]["content"]

    return json.loads(text)

@app.post("/extract")
async def extract(req: Req):
    try:
        data = _chat_completion_json(req.description, OPENAI_MODEL)
    except Exception:
        data = _chat_completion_json(req.description, "gpt-4o-mini-2024-07-18")

    print("JSON de respuesta desde OpenAI:", json.dumps(data, ensure_ascii=False))
    return data
