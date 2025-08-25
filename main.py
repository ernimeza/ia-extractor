import os, json
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

# ------- Compatibilidad SDK -------
NEW_SDK = True
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
except Exception:
    import openai as oai  # SDK legacy 0.x
    oai.api_key = os.environ["OPENAI_API_KEY"]
    NEW_SDK = False

# ------- Modelo por defecto -------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")  # gpt-5 para máxima precisión

# ------- Catálogos -------
OPERACIONES = ["venta", "alquiler"]
TIPOS = ['casas','departamentos','duplex','terrenos','oficinas','locales','edificios','paseos','depositos','quintas','estancias']
HAB_OPC = ['1','2','3','4','5','6','7','8','9','10','monoambiente','+10']
NUM_OPC = ['1','2','3','4','5','6','7','8','9','10','+10']
PLANTAS_OPC = ['1','2','3','4','5','+5']
ESTILO_OPC = ['Moderna','Minimalista','Clásica','De campo']
DIVISA_OPC = ['GS', '$']
ESTADO_OPC = ['A estrenar', 'Perfecto', 'Muy bueno', 'Bueno']
AMENIDADES_OPC = [
    'Acceso controlado','Área de coworking','Área de parrilla','Área de yoga','Área verde','Bar','Bodega',
    'Cancha de pádel','Cancha de tenis','Cancha de fútbol','Cerradura digital','Cine','Club house',
    'Estacionamiento techado','Generador','Gimnasio','Laguna artificial','Laguna natural','Lavandería',
    'Parque infantil','piscina','Quincho','Salón de eventos','Sala de juegos','Sala de masajes',
    'Sala de reuniones','Sauna','Seguridad 24/7','Solarium','Spa','Terraza','Wi-Fi','Café','Business center'
]
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
    'san-bernardino','lambare','capiata','nemby','abai','acahay','alberdi','alborada','alto-vera','altos','antequera',
    'aregua','arroyos-y-esteros','atyra','azotey','bella-vista-amambay','bahia-negra','bella-vista-Itapua','belen',
    'benjamin-aceval','borja','buena-vista','caacupe','caaguazu','caballero','caapucu','caazapa','capiibary',
    'capitan-bado','capitan-meza','caraguatay','capitan-miranda','carapegua','carlos-antonio-lopez','carayao',
    'carmelo-peralta','capiibary','cerrito','chore','colonia-independencia','coronel-bogado','concepcion',
    'coronel-martinez','coronel-oviedo','corpus-christi','curuguaty','desmochados','doctor-cecilio-baez-guaira',
    'doctor-bottrell','doctor-cecilio-baez-caaguazu','doctor-j-victor-barrios','doctor-moises-bertoni',
    'domingo-martinez-de-irala','edelira','emboscada','escobar','esteban-martinez','eugenio-a-garay',
    'eusebio-ayala','filadelfia','felix-perez-cardozo','fuerte-olimpo','fram','francisco-caballero-alvarez',
    'general-artigas','general-delgado','general-diaz','general-elizardo-aquino','general-iginio-morinigo',
    'guayaibi','guarambare','guazu-cua','hernandarias','hohenau','humaitá','horqueta','independencia','isla-pucu',
    'Ita','isla-umbu','itacurubi-de-la-cordillera','itacurubi-del-rosario','itape','itaugua','iturbe','iruna',
    'jesus-de-tavarangue','jose-augusto-saldivar','jose-domingo-ocampos','jose-fasardi','jose-falcon','juan-de-mena',
    'juan-manuel-frutos-pastoreo','juan-eulogio-estigarribia-campo-9','juan-leon-mallorquin','juan-emilio-oleary',
    'la-colmena','karapai','katuete','la-paloma','la-pastora','la-victoria','laureles','leandro-oviedo','lima',
    'limpio','loma-grande','loma-plata','los-cedrales','loreto','mbaracayu','mbocayaty-del-yhaguy','mbocayaty',
    'mbocayaty-del-guaira','maracana','mariscal-estigarribia','mariscal-francisco-solano-lopez','mayor-julio-d-otano',
    'mayor-jose-dejesus-martinez','mbocayaty','minga-guazu','natalicio-talavera','nanawa','naranjal','nueva-alborada',
    'natalio','nueva-asuncion','nueva-colombia','nueva-italia','nueva-germania','nueva-toledo','nacunday','numi',
    'olbligado','paso-barreto','paso-de-patria','paso-yobai','pedro-juan-caballero','pirapo','pirayu','pilar','piribebuy',
    'pozo-colorado','presidente-franco','primero-de-marzo','puerto-adela','puerto-casado','puerto-irala','puerto-pinasco',
    'quyquyho','raul-arsenio-oviedo','repatriacion','R-I-3-corrales','san-alberto','salto-del-guaira','san-antonio',
    'san-carlos-del-apa','san-cosme-y-damian','san-estanislao-santani','san-joaquin','san-jose-obrero',
    'san-juan-bautista-de-las-misiones','san-juan-bautista-de-neembucu','san-juan-del-parana','san-lazaro','san-miguel',
    'san-pedro-del-parana','san-patricio','san-pablo','san-roque-gonzalez-de-santa-cruz','san-pedro-de-ycuamandyyu',
    'san-salvador','san-vicente-pancholo','santa-elena','santa-maria','santa-fe-del-parana','santa-rosa',
    'santa-maria-de-fe','santa-rosa-de-lima','santa-rosa-del-aguaray','santa-rosa-del-mbutuy','santa-rosa-del-monday',
    'santiago','sapucai','sergeant-jose-felix-lopez-puentesino','simon-bolivar','tacuaras','tacuati','tavai','tavapy',
    'tebicuary-mi','tembiaporã','teniente-esteban-martinez','tinfunque','tomas-romero-pereira','tobati','tres-de-mayo',
    'trinidad','union','valenzuela','vaqueria','villa-del-rosario','villa-florida','villa-elisa','villa-franca',
    'villa-hayes','villa-oliva','villa-rica','villeta','yabebyry','yaguaron','yasy-cany','yataity','yataity-del-Norte',
    'ybycui','yby-pyta','yby-yau','ybyrarobana','yguazu','yhu','ypacarai','ypane','yuty','zanja-pyta'
]

# ------- JSON Schema (Structured Outputs) -------
def _nullable_enum(values: List[str]) -> Dict[str, Any]:
    return {"anyOf": [{"enum": values}, {"type": "null"}]}

def _nullable_str() -> Dict[str, Any]:
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}

def _nullable_int() -> Dict[str, Any]:
    return {"anyOf": [{"type": "integer"}, {"type": "null"}]}

EXTRACT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "operacion": _nullable_enum(OPERACIONES),
        "tipodepropiedad": _nullable_enum(TIPOS),
        "ciudades": _nullable_enum(CIUDADES),
        "barrioasu": _nullable_enum(BARRIOS_ASU),
        "precio": _nullable_int(),
        "Barrio": _nullable_str(),
        "habitaciones": _nullable_enum(HAB_OPC),
        "banos": _nullable_enum(NUM_OPC),
        "cocheras": _nullable_enum(NUM_OPC),
        "plantas": _nullable_enum(PLANTAS_OPC),
        "m2": _nullable_int(),
        "anno_construccion": _nullable_int(),
        "datosia": _nullable_str(),
        "hectareas": _nullable_int(),
        "m2t": _nullable_int(),
        "m2c": _nullable_int(),
        "asesor": _nullable_str(),
        "numeroasesor": _nullable_str(),
        "estado": _nullable_enum(ESTADO_OPC),
        "amenidades": {"anyOf": [
            {"type": "array", "items": {"enum": AMENIDADES_OPC}, "uniqueItems": True},
            {"type": "null"}
        ]},
        "amoblado": _nullable_enum(['Sí','No']),
        "descripcion": _nullable_str(),
        "nombredeledificio": _nullable_str(),
        "piso": _nullable_str(),
        "estilo": _nullable_enum(ESTILO_OPC),
        "divisa": _nullable_enum(DIVISA_OPC),
        "ubicacion": _nullable_str()
    },
    "required": [
        "operacion","tipodepropiedad","ciudades","barrioasu","precio","Barrio","habitaciones","banos",
        "cocheras","plantas","m2","anno_construccion","datosia","hectareas","m2t","m2c","asesor",
        "numeroasesor","estado","amenidades","amoblado","descripcion","nombredeledificio","piso",
        "estilo","divisa","ubicacion"
    ],
    "additionalProperties": False
}

SYSTEM_INSTRUCTIONS = (
    "Eres un extractor de datos inmobiliarios experto. Devuelve SOLO un objeto JSON que respete EXACTAMENTE "
    "el esquema indicado (sin campos extra) y usa null cuando no haya dato. "
    "Normaliza sinónimos (ej. pileta → piscina). Corrige ortografía/capitalización para coincidir con listas. "
    "Si detectas un barrio típico de Asunción sin ciudad explícita, asume ciudades='asuncion' y completa 'barrioasu'. "
    "La clave 'datosia' es una descripción interna y técnica (no pública). "
    "La clave 'descripcion' es un copy para público, breve, con emojis y checklist si procede."
)

# ------- FastAPI -------
app = FastAPI()

class Req(BaseModel):
    description: str

_ALLOWED_KEYS = set(EXTRACT_SCHEMA["properties"].keys())

def _clean_result(d: Dict[str, Any]) -> Dict[str, Any]:
    # Filtra claves extra y asegura todas las requeridas
    d = {k: d.get(k, None) for k in _ALLOWED_KEYS}
    # Normaliza amenidades al catálogo
    if isinstance(d.get("amenidades"), list):
        d["amenidades"] = [a for a in d["amenidades"] if a in AMENIDADES_OPC]
        if not d["amenidades"]:
            d["amenidades"] = None
    return d

def _call_chat_with_schema(description: str, model: str) -> Dict[str, Any]:
    """Intenta Structured Outputs (json_schema). Si tu SDK no lo soporta, cae a json_object."""
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": description},
    ]
    # 1) Intento con JSON Schema (Structured Outputs)
    try:
        if NEW_SDK:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=2000,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "inmueble_extract",
                        "strict": True,
                        "schema": EXTRACT_SCHEMA
                    }
                },
            )
            text = resp.choices[0].message.content
        else:
            # SDK 0.x podría no soportar json_schema → forzamos excepción para ir al fallback
            raise RuntimeError("json_schema no soportado en SDK legacy; usar fallback json_object")
        return json.loads(text)
    except Exception:
        # 2) Fallback robusto: JSON mode clásico
        if NEW_SDK:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content
        else:
            resp = oai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            text = resp["choices"][0]["message"]["content"]
        return json.loads(text)

@app.post("/extract")
async def extract(req: Req):
    try:
        data = _call_chat_with_schema(req.description, OPENAI_MODEL)
    except Exception:
        # Fallback de modelo si tu cuenta no tiene el seleccionado
        fallback = "gpt-4o-mini-2024-07-18"
        data = _call_chat_with_schema(req.description, fallback)

    data = _clean_result(data)
    print("JSON de respuesta desde OpenAI:", json.dumps(data, ensure_ascii=False))
    return data
