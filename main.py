import os, json
from typing import Any, Dict
from fastapi import FastAPI
from pydantic import BaseModel

# Compatibilidad con SDK nuevo o legacy
NEW_SDK = True
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
except Exception:
    import openai as oai  # SDK 0.x
    oai.api_key = os.environ["OPENAI_API_KEY"]
    NEW_SDK = False

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")  # "gpt-5" para precisión máxima

app = FastAPI()

class Req(BaseModel):
    description: str

SYSTEM_PROMPT = r"""
Eres un EXTRACTOR de datos inmobiliarios experto. Debes LEER una descripción y devolver **SOLO** un objeto JSON (sin texto extra, sin markdown) que respete EXACTAMENTE el siguiente esquema. 
Reglas globales IMPORTANTES:
- NO agregues campos adicionales; SOLO los listados.
- Evita strings vacíos: si no hay dato, usa null. PERO intenta INFERIR con señales del texto antes de usar null.
- Normaliza sinónimos (pileta→piscina; depto→departamentos; dúplex→duplex; cochera/garaje/estacionamiento→cochera).
- Si aparece un **barrio clásico de Asunción** (p. ej. villa morra, recoleta, carmelitas, etc.) sin ciudad explícita, asume `ciudades='asuncion'` y completa `barrioasu`.
- Para números: extrae y normaliza. Acepta formatos 'm²', 'm2', 'mts2', 'metros cuadrados'.
- Para precio: 
  - Coloca el número que diga en Precio:.
-Para `habitaciones/banos/cocheras/plantas`, coloca la cantidad exacta que diga en la descripción siempre.
- `m2` = superficie principal (si hay “m2 construidos/área cubierta”, úsalo como `m2c`; si solo hay un m2 sin especificar, colócalo en `m2`).
- Diferencia superficies:
  - `m2t` = terreno/lote/superficie total/terreno.
  - `m2c` = construcción/cubiertos/edificados.
  - `m2` = si hay ambas medidas (m2c y m2t) usa el más grande (nomralmente m2t)
- `estado`: mapea a ['A estrenar','Perfecto','Muy bueno','Bueno'] según lenguaje (“a estrenar/nuevo”→A estrenar; “excelente”→Perfecto; “muy bueno”→Muy bueno; “bueno”→Bueno).
- `amoblado`: 'Sí' si explicitamente dice que viene amoblado, no pongas ´´Sí´´ si es que dice solo ´´cocina amoblada´´ o una pequeña parte de la casa amoblada, se tiene que referir a los muebles de toda la casa; 'No' si es que no dice explicitamente que sí está amoblado.
- `tipodepropiedad`: elegir exactamente de: ['casas','departamentos','duplex','terrenos','oficinas','locales','edificios','paseos','depositos','quintas','estancias'].
- `operacion`: elegir de ['venta','alquiler'] (renta/arrendamiento→alquiler).
- `ciudades`: elegir EXACTAMENTE del catálogo proporcionado en el esquema (slugs en minúscula).
- `barrioasu`: elegir EXACTAMENTE del catálogo proporcionado (slug). Acepta variaciones con acentos/mayúsculas y normaliza.
- `datosia`: crea SIEMPRE un párrafo técnico amplio (solo para análisis interno, no público) describiendo la propiedad con lo que se sepa (tipo, m2, habitaciones, amenidades, zona).
- `descripcion`: Copia la descripción completa que dice luego de ´´Descripción´´.

Devuelve SOLO un JSON con esta estructura EXACTA (usa null si no hay data):

{
  "operacion": "venta|alquiler" (string, inferir por contexto “alquiler/renta/arrendamiento”→alquiler; “venta/oportunidad de compra”→venta),
  "tipodepropiedad": "casas|departamentos|duplex|terrenos|oficinas|locales|edificios|paseos|depositos|quintas|estancias" (string),
  "ciudades": "slug exacto de ciudad del catálogo" (string),
  "barrioasu": "slug exacto si aplica Asunción; si no, null" (string|null),
  "precio": "Número ENTERO",
  "Barrio": "nombre de barrio libre (si no es Asunción o no está en catálogo); si es Asunción usa también 'barrioasu'" (string|null),
  "habitaciones": "uno de ['1','2','3','4','5','6','7','8','9','10','monoambiente','+10']" (string|null),
  "banos": "uno de ['1','2','3','4','5','6','7','8','9','10','+10']" (string|null),
  "cocheras": "uno de ['1','2','3','4','5','6','7','8','9','10','+10'] (si dice 'sin cochera', usa null)" (string|null),
  "plantas": "uno de ['1','2','3','4','5','+5']" (string|null),
  "m2": "m² principal de la unidad" (integer|null),
  "id": "id de la propiedad" (integer|null),
  "anno_construccion": "año (yyyy) si está" (integer|null),
  "datosia": "descripción técnica amplia SIEMPRE" (string),
  "hectareas": "entero en hectáreas si aplica (campos/estancias/quintas)" (integer|null),
  "m2t": "m² del terreno" (integer|null),
  "m2c": "m² de construcción/cubiertos" (integer|null),
  "asesor": "nombre del asesor si aparece" (string|null),
  "numeroasesor": "tel del asesor en formato tal cual aparece" (string|null),
  "estado": "una de ['A estrenar','Perfecto','Muy bueno','Bueno','Desarrollo','Remodelada','Regular','Le falta trabajo','En construción','Pre venta'] según adjetivos; si no se infiere, null" (string|null),
  "amenidades": "subset de ['Acceso controlado','Área de coworking','Área de parrilla','Área de yoga','Área verde','Bar','Bodega','Cancha de pádel','Cancha de tenis','Cancha de fútbol','Cerradura digital','Cine','Club house','Estacionamiento techado','Generador','Gimnasio','Laguna artificial','Laguna natural','Lavandería','Parque infantil','piscina','Quincho','Salón de eventos','Sala de juegos','Sala de masajes','Sala de reuniones','Sauna','Seguridad 24/7','Solarium','Spa','Terraza','Wi-Fi','Café','Business center'] (normaliza sinónimos y deduplica)" (array|null),
  "amoblado": "Sí|No" (string|null),
  "descripcion": "copy comercial breve con emojis y checklist" (string),
  "nombredeledificio": "si dice 'Edificio X'/'Torre X'" (string|null),
  "piso": "número de piso o 'PB' si explícito; si es casa/terreno: null" (string|null),
  "estilo": "una de ['Moderna','Minimalista','Clásica','De campo','Rústica','De playa','De verano','De lujo','Para inversión','Sustentable','Prefabricada','Inteligente'] según adjetivos; si no se infiere, null" (string|null),
  "divisa": "GS|$ (según aparezca el precio)." (string|null),
  "ubicacion": "dirección formateada estilo Google Maps, basandote en lo que dice en ´´Dirección:´´ Si o si en Paraguay, y en la ciudad de la descripción (string|null)
}

Catálogos de ciudades y barrios (slugs) SON los definidos por tu sistema; respétalos exactamente al completar.
"""

# Para no llenar este archivo con los catálogos enormes, se los pasamos al modelo como "contexto auxiliar"
# Si prefieres, puedes pegar tus listas completas aquí:
CIUDADES_CTX = ", ".join([
    "asuncion","luque","ciudad-del-este","encarnacion","san-lorenzo","fernando-de-la-mora","mariano-roque-alonso",
    "san-bernardino","lambare","capiata","nemby","... (resto del catálogo que usas)"
])
BARRIOS_CTX = ", ".join([
    "villa-morra","recoleta","carmelitas","las-lomas","las-mercedes","mburucuya","jara","sajonia","villa-aurelia",
    "ycua-sati","... (resto del catálogo que usas)"
])

def _chat_completion_json(description: str, model: str) -> Dict[str, Any]:
    user_content = (
        "Descripción de entrada:\n"
        f"{description}\n\n"
        "Catálogo ciudades (slugs válidos):\n" + CIUDADES_CTX + "\n\n"
        "Catálogo barrios Asunción (slugs válidos):\n" + BARRIOS_CTX + "\n\n"
        "Responde SOLO con el JSON solicitado."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # Intento con SDK nuevo
    if NEW_SDK:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0, max_tokens=2000,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content
    else:
        # SDK legacy 0.x
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
        # Fallback de modelo si el principal no está habilitado
        data = _chat_completion_json(req.description, "gpt-4o-mini-2024-07-18")

    # Log para depurar
    print("JSON de respuesta desde OpenAI:", json.dumps(data, ensure_ascii=False))
    return data
