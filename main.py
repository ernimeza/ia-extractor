import os, json
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
# ----- Configuración -----
MODEL = "gpt-4o-mini-2024-07-18" # si aún no tienes acceso, cambia a "gpt-3.5-turbo-0125"
app = FastAPI()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
class Req(BaseModel):
    description: str
    images: list[str]
@app.post("/extract")
async def extract(req: Req):
    # Fix image URLs to ensure they start with https:// and filter out empty/invalid ones
    fixed_images = []
    for u in req.images:
        if u and isinstance(u, str) and u.strip(): # Skip if empty or not a string
            if u.startswith('//'):
                u = 'https:' + u
            elif not u.startswith('http'):
                u = 'https://' + u
            fixed_images.append(u)
    messages = [
        {"role": "system", "content": """
Eres un extractor de datos inmobiliarios experto. Analiza la descripción de texto y las imágenes para extraer/inferir info. Devuelve SOLO un objeto JSON con esta estructura EXACTA (sin campos extras, usa null si no hay data). Corrige ortografía/capitalización para coincidir con listas.
{
  "operacion": Elige de: ['venta', 'alquiler'] (string),
  "tipodepropiedad": Elige exactamente de: ['casas', 'departamentos', 'duplex', 'terrenos', 'oficinas', 'locales', 'edificios', 'paseos', 'depositos', 'quintas', 'estancias'] (string),
  "ciudades": Elige de: ['asuncion', 'luque', 'ciudad-del-este', 'encarnacion', 'san-lorenzo', 'fernando-de-la-mora', 'mariano-roque-alonso', 'san-bernardino', 'lambare', 'capiata', 'nemby'] (string),
  "barrioasu": Elige de: ['villa-morra', 'recoleta', 'carmelitas', 'las-lomas', 'las-mercedes', 'mburucuya', 'jara', 'sajonia', 'villa-aurelia', 'ycua-sati', 'obrero', 'Itá Enramada', 'Nazareth', 'San Roque', 'Vista Alegre', 'Hipódromo', 'La Encarnación', 'Tacumbú', 'Jukyty', 'La Catedral', 'Mbojuapy Tavapy', 'Dr. Gaspar Rodríguez de Francia', 'Ita Pyta Punta', 'Salvador del Mundo'] (string),
  "precio": Número en USD (integer),
  "habitaciones": Elige de: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'monoambiente', '+10'] (string),
  "banos": Elige de: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '+10'] (string),
  "cocheras": Elige de: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '+10'] (string),
  "plantas": Elige de: ['1', '2', '3', '4', '5', '+5'] (string),
  "m2": Número de m² (integer),
  "anno_construccion": Año de construcción (integer),
  "estado": Elige de: ['A estrenar', 'Perfecto', 'Muy bueno', 'Bueno'] (string),
  "amoblado": Elige de: ['Sí', 'No'] (string),
  "descripcion": Resumen completo de la propiedad, bien estructurado y yendo al grano (string),
  "nombredeledificio": Nombre del edificio (string),
  "piso": Piso en el que se encuentra (string),
  "estilo": Elige de: ['Moderna', 'Minimalista', 'Clásica', 'De campo'] (string),
  "divisa": Elige de: ['GS', '$'] (string)
}
"""},
        {"role": "user", "content": [
            {"type": "text", "text": req.description},
            *[{"type": "image_url", "image_url": {"url": u}} for u in fixed_images]
        ]}
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    print("JSON de respuesta desde OpenAI:", resp.choices[0].message.content) # Línea nueva para logs
    return json.loads(resp.choices[0].message.content)
