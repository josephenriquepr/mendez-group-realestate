from openai import AsyncOpenAI
from models.property import PropertyData
import config

LISTING_SYSTEM_PROMPT = """Eres un redactor experto en bienes raíces en Puerto Rico.
Escribes descripciones profesionales, atractivas y persuasivas de propiedades
para plataformas como Zillow, Realtor.com y portales locales de PR.
Tu tono es cálido pero profesional. Siempre en español. Máximo 250 palabras."""

INSTAGRAM_SYSTEM_PROMPT = """Eres un especialista en marketing digital para el sector inmobiliario en Puerto Rico.
Creas copies virales, enganchadores y efectivos para Instagram.
Conoces los hashtags más relevantes del mercado de bienes raíces en PR.
Siempre en español. El copy debe generar engagement y consultas directas."""


def _build_listing_prompt(data: PropertyData) -> str:
    amenidades_str = ", ".join(data.amenidades) if data.amenidades else "ninguna especificada"
    hab = data.habitaciones if data.habitaciones is not None else "N/A"
    ban = data.banos if data.banos is not None else "N/A"
    pies = f"{data.pies_cuadrados_construccion:,}" if data.pies_cuadrados_construccion else "N/A"
    terreno = data.metros_o_cuerdas_terreno or "N/A"
    estac = data.estacionamientos if data.estacionamientos is not None else "N/A"

    return f"""Genera una descripción profesional y atractiva para la siguiente propiedad:

Tipo: {data.tipo_propiedad}
Operación: {data.operacion}
Ubicación: {data.direccion}, {data.pueblo}, Puerto Rico
Precio: ${data.precio:,.0f} USD
Habitaciones: {hab}
Baños: {ban}
Área de construcción: {pies} pies cuadrados
Terreno: {terreno}
Estacionamientos: {estac}
Amenidades: {amenidades_str}

Notas del agente: {data.descripcion_agente}

Instrucciones:
- Empieza con una frase gancho que destaque el mayor atractivo de la propiedad.
- Incluye todos los datos relevantes de forma natural y fluida.
- Menciona la ubicación en Puerto Rico de forma que suene atractiva.
- Cierra con una llamada a la acción breve.
- Máximo 250 palabras. Solo la descripción, sin encabezados ni viñetas."""


def _build_instagram_prompt(data: PropertyData, listing_description: str) -> str:
    pueblo_hashtag = data.pueblo.lower().replace(" ", "").replace("í", "i").replace("ó", "o").replace("á", "a").replace("é", "e").replace("ú", "u")
    tipo_hashtag = data.tipo_propiedad.lower().replace(" ", "")

    return f"""Basándote en la siguiente descripción de propiedad, crea un copy optimizado para Instagram:

DESCRIPCIÓN:
{listing_description}

DATOS CLAVE:
Tipo: {data.tipo_propiedad} en {data.operacion}
Precio: ${data.precio:,.0f}
Pueblo: {data.pueblo}, Puerto Rico
Agente: {data.nombre_agente} | {data.licencia_agente} | {data.telefono_agente}

Instrucciones:
- Línea 1: frase de gancho con emoji que genere urgencia o deseo.
- Cuerpo (3-5 líneas): puntos clave con emojis por línea, fácil de leer en móvil.
- Llamada a la acción clara con el número de teléfono del agente.
- Bloque de hashtags al final (mínimo 20 hashtags relevantes).
- Incluye hashtags como: #bienesraicespr #propiedadespr #puertoricorealestate #{pueblo_hashtag} #{tipo_hashtag} y otros populares del sector inmobiliario en PR e hispano.
- Máximo 400 palabras en total (sin contar hashtags).
- Solo el texto del post listo para pegar, sin instrucciones adicionales."""


async def generate_content(data: PropertyData) -> dict:
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    listing_response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": LISTING_SYSTEM_PROMPT},
            {"role": "user", "content": _build_listing_prompt(data)},
        ],
        temperature=0.75,
        max_tokens=500,
    )
    listing_description = listing_response.choices[0].message.content.strip()

    instagram_response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": INSTAGRAM_SYSTEM_PROMPT},
            {"role": "user", "content": _build_instagram_prompt(data, listing_description)},
        ],
        temperature=0.85,
        max_tokens=700,
    )
    instagram_copy = instagram_response.choices[0].message.content.strip()

    return {
        "listing_description": listing_description,
        "instagram_copy": instagram_copy,
    }
