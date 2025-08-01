import os, json
from fastapi import FastAPI
from pydantic import BaseModel
import openai

# ----- Configuración -----
openai.api_key = os.environ["OPENAI_API_KEY"]
MODEL = "gpt-4o-mini-2024-07-18"  # si aún no tienes acceso, cambia a "gpt-3.5-turbo-0125"

app = FastAPI()

class Req(BaseModel):
    description: str
    images: list[str]

@app.post("/extract")
async def extract(req: Req):
    # Fix image URLs to ensure they start with https:// and filter out empty/invalid ones
    fixed_images = []
    for u in req.images:
        if u and isinstance(u, str) and u.strip():  # Skip if empty or not a string
            if u.startswith('//'):
                u = 'https:' + u
            fixed_images.append(u)

    messages = [
        {"role": "system", "content": "Eres un extractor de datos inmobiliarios. Devuelve SOLO el JSON pedido."},
        {"role": "user", "content": [
            {"type": "text", "text": req.description},
            *[{"type": "image_url", "image_url": {"url": u}} for u in fixed_images]
        ]}
    ]
    resp = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
