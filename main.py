import os, json
from fastapi import FastAPI
from pydantic import BaseModel
import openai
# ----- Configuración -----
openai.api_key = os.environ["OPENAI_API_KEY"]
MODEL = "gpt-4o-mini-2024-07-18" # si aún no tienes acceso, cambia a "gpt-3.5-turbo-0125"
app = FastAPI()
class Req(BaseModel):
    description: str
@app.post("/extract")
async def extract(req: Req):
    messages = [
        {"role": "system", "content": """
Eres un extractor de datos inmobiliarios experto. Analiza la descripción de texto para extraer/inferir info. Devuelve SOLO un objeto JSON con esta estructura EXACTA (sin campos extras, usa null si no hay data). Corrige ortografía/capitalización para coincidir con listas.
{
  "operacion": Elige de: ['venta', 'alquiler'] (string),
  "tipodepropiedad": Elige exactamente de: ['casas', 'departamentos', 'duplex', 'terrenos', 'oficinas', 'locales', 'edificios', 'paseos-comerciales', 'depositos', 'quintas', 'estancias'] (string),
  "ciudades": Elige de: ['asuncion', 'luque', 'ciudad-del-este', 'encarnacion', 'san-lorenzo', 'fernando-de-la-mora', 'mariano-roque-alonso', 'san-bernardino', 'lambare', 'capiata', 'nemby'] (string),
  "barrioasu": Elige de: ['villa-morra', 'recoleta', 'carmelitas', 'las-lomas', 'las-mercedes', 'mburucuya', 'jara', 'sajonia', 'villa-aurelia', 'ycua-sati', 'obrero', 'Itá Enramada', 'Nazareth', 'San Roque', 'Vista Alegre', 'Hipódromo', 'La Encarnación', 'Tacumbú', 'Jukyty', 'La Catedral', 'Mbojuapy Tavapy', 'Dr. Gaspar Rodríguez de Francia', 'Ita Pyta Punta', 'Salvador del Mundo'] (string),
  "precio": Número en USD (integer),
  "habitaciones": Elige de: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'monoambiente', '+10'] (string),
  "banos": Elige de: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '+10'] (string),
  "cocheras": Elige de: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '+10'] (string),
  "plantas": Elige de: ['1', '2', '3', '4', '5', '+5'] (string),
  "m2": Número de m² (integer),
  "anno_construccion": Año de construcción (integer),
  "hectareas": Hectáreas (integer)
  "m2t": Número de m² del terreno (integer)
  "m2t": Número de m² de construcción, (integer)
  "estado": Elige exclusivamente de las siguientes opciones, si no hay información seleeciona la que mas se asemeje: ['A estrenar', 'Perfecto', 'Muy bueno', 'Bueno'] (string),
  "amenidades": Elige las opciones entre: ['Acceso controlado', 'Área de coworking', 'Área de parrilla', 'Área de yoga', 'Área verde', 'Bar', 'Bodega', 'Cancha de pádel', 'Cancha de tenis', 'Cancha de fútbol', 'Cerradura digital', 'Cine', 'Club house', 'Estacionamiento techado', 'Generador', 'Gimnasio', 'Laguna artificial', 'Laguna natural', 'Lavandería', 'Parque infantil', 'piscina', 'Quincho', 'Salón de eventos', 'Sala de juegos', 'Sala de masajes', 'Sala de reuniones', 'Sauna', 'Seguridad 24/7', 'Solarium', 'Spa', 'Terraza', 'Wi-Fi', 'Café', 'Business center'] (list),
  "amoblado": Elige de: ['Sí', 'No'] (string)
  "descripcion": Linda descripción de la propiedad, bien estructurada, dejando una linea al concluiir el parrafo yendo al grano, con emojies y checklist con beneficios si hay contenido (string),
  "nombredeledificio": Nombre del edificio (string),
  "piso": Piso en el que se encuentra (string),
  "estilo": Elige de: ['Moderna', 'Minimalista', 'Clásica', 'De campo'] (string),
  "divisa": Elige de: ['GS', '$'] (string),
  "ubicacion": Dirección completa formateada como en Google Maps (string)
}
"""},
        {"role": "user", "content": [
            {"type": "text", "text": req.description}
        ]}
    ]
    resp = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    print("JSON de respuesta desde OpenAI:", resp.choices[0].message.content) # Línea nueva para logs
    return json.loads(resp.choices[0].message.content)
