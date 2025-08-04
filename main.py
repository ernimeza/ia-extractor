import os, json, logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import openai

# Configura logging básico (salida a stdout con nivel INFO)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----- Configuración -----
openai.api_key = os.environ["OPENAI_API_KEY"]
MODEL = "gpt-4o-mini"  # Versión general para compatibilidad

app = FastAPI()

class Req(BaseModel):
    description: str
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image4: Optional[str] = None
    image5: Optional[str] = None
    image6: Optional[str] = None
    image7: Optional[str] = None
    image8: Optional[str] = None
    image9: Optional[str] = None
    image10: Optional[str] = None

@app.post("/extract")
async def extract(req: Req):
    # Collect and fix image URLs
    images = [
        req.image1, req.image2, req.image3, req.image4, req.image5,
        req.image6, req.image7, req.image8, req.image9, req.image10
    ]
    fixed_images = []
    for u in images:
        if u and isinstance(u, str) and u.strip():  # Skip if None, empty or not a string
            if u.startswith('//'):
                u = 'https:' + u
            fixed_images.append(u)
    
    # Log las URLs entrantes para depuración
    logger.info("URLs de imágenes recibidas: %s", fixed_images)
    
    messages = [
        {"role": "system", "content": """
Eres un extractor de datos inmobiliarios experto. Analiza la descripción de texto y las imágenes para extraer/inferir info. Devuelve SOLO un objeto JSON con esta estructura EXACTA (sin campos extras, usa null si no hay data). Corrige ortografía/capitalización para coincidir con listas. 
SIEMPRE incluye las URLs exactas de las imágenes proporcionadas en los campos image1 a image10, incluso si no puedes analizar las imágenes o si parecen irrelevantes (cópialas directamente; usa null SOLO si no se proporcionó ninguna URL en esa posición).
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
  "divisa": Elige de: ['GS', '$'] (string),
  "image1": URL de la imagen 1 o null (string),
  "image2": URL de la imagen 2 o null (string),
  "image3": URL de la imagen 3 o null (string),
  "image4": URL de la imagen 4 o null (string),
  "image5": URL de la imagen 5 o null (string),
  "image6": URL de la imagen 6 o null (string),
  "image7": URL de la imagen 7 o null (string),
  "image8": URL de la imagen 8 o null (string),
  "image9": URL de la imagen 9 o null (string),
  "image10": URL de la imagen 10 o null (string)
}
"""},
        {"role": "user", "content": [
            {"type": "text", "text": req.description},
            *[{"type": "image_url", "image_url": {"url": u}} for u in fixed_images]
        ]}
    ]
    
    try:
        resp = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        json_response = resp.choices[0].message.content
        logger.info("JSON de respuesta desde OpenAI: %s", json_response)  # Log completo del JSON
        return json.loads(json_response)
    except Exception as e:
        logger.error("Error en llamada a OpenAI: %s", str(e))  # Log de errores
        return {"error": str(e)}
