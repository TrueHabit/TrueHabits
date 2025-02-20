# OK

import openai
from telegram import Update
from telegram.ext import CallbackContext

from config import OPENAI_API_KEY
from sqlalchemy.orm import Session
from acciones.accion_add_datos_BBDD import procesar_mensaje_insert
from acciones.accion_preguntas import procesar_resumen
from BBDD_create.funciones_informe import get_points_accumulated_all_time, get_points_accumulated_weekly

openai.api_key = OPENAI_API_KEY

def clasificar_accion(user_text: str) -> str:
    # Esta funcion llama a ChatGPT para clasificar la intencion del usuario
    # Se construye el prompt explicando las categorias posibles: habito, resumen o ninguna
    
    prompt_corregir = f"""
    A partir del siguiente texto en español sobre un objetivo personal, primero corrige posibles errores de tipeo 
    (especialmente en unidades y palabras). No inventes contenido nuevo, solo corrige faltas evidentes.
    
    Texto: "{user_text}"
    """
    
    # Se hace la peticion a la API de OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que corrige el texto en español. Devuelve solo el texto corregido."},
                {"role": "user", "content": prompt_corregir}
            ],
            max_tokens=100,
            temperature=0.0,
        )
        texto_corregido = response['choices'][0]['message']['content'].strip()
    except Exception:
        return -1
    
    prompt = f"""
    El usuario puede enviar un mensaje con distintos propósitos:
    1) Añadir un nuevo hábito a su registro. (Respuesta: habito)
    2) Solicitar un resumen descriptivo de los hábitos que ha registrado, para conocer detalles o estadísticas de sus actividades. (Respuesta: resumen)
    3) Preguntar cuántos puntos ha acumulado en la semana. (Respuesta: puntos_semana)
    4) Preguntar cuántos puntos ha acumulado en total desde que empezó a usar la aplicación. (Respuesta: puntos_totales)
    5) Si el mensaje no encaja en ninguno de estos casos. (Respuesta: ninguna)

    **Reglas importantes:**
    - Si el usuario menciona un número (por ejemplo: "caminé 100 pasos", "corrí 5 km", "nadé 30 minutos"), el número debe **mantenerse EXACTAMENTE como lo escribió el usuario**.
    - NO debes cambiar ni interpretar los números. Si el usuario dice "100 pasos", debe registrarse como "100 pasos", no "1000 pasos".
    - Si el mensaje describe una acción realizada **sin incluir un número explícito** (por ejemplo, "hoy comí comida basura"), se debe clasificar como **habito** y registrar la acción como 1 vez.

    **Instrucciones:**  
    Responde **EXACTAMENTE** con una de estas 5 palabras (en minúsculas):
    - habito
    - resumen
    - puntos_semana
    - puntos_totales
    - ninguna

    **Casos importantes:**
    - Si el mensaje **pregunta por una actividad (cuánto caminé, corrí, nadé, leí, etc.)** sin mencionar “puntos” → clasificación: **resumen**.
    - Si el mensaje **menciona la palabra “puntos”** y se limita a la semana → clasificación: **puntos_semana**.
    - Si el mensaje **menciona la palabra “puntos”** y pregunta de forma general o “en total” → clasificación: **puntos_totales**.
    - Si el mensaje **describe una acción realizada con una cantidad (ejemplo: "camine 10000 pasos", "corrí 5 km", "nadé 30 minutos")** → clasificación: **habito**.
    - Si el mensaje **describe una acción realizada sin una cantidad explícita** (ejemplo: "hoy comí comida basura") → clasificación: **habito**.

    **Ejemplos:**
    1. "¿Cuántas veces he corrido este mes?"  
    → No menciona “puntos”, pregunta sobre la actividad → **resumen**.

    2. "¿Cuánto corrí esta semana?"  
    → Pregunta sobre la actividad (correr) en la semana, sin mencionar “puntos” → **resumen**.

    3. "¿Cuánto caminé esta semana?"  
    → Pregunta sobre la actividad de caminar en la semana, sin mencionar “puntos” → **resumen**.

    4. "Ayer corrí 5 km"  
    → Es un registro nuevo de un hábito → **habito**.

    5. "¿Cuántos puntos llevo esta semana?"  
    → La palabra clave es “puntos”, se refiere a la semana → **puntos_semana**.

    6. "¿Cuántos puntos tengo en total?"  
    → La palabra clave es “puntos”, de forma general → **puntos_totales**.

    7. "Hoy he jugado al fútbol 30 minutos"  
    → Registra un hábito nuevo → **habito**.

    8. "¿Cuántos puntos acumulados llevo?"  
    → La palabra clave es “puntos” y “acumulados” → **puntos_totales**.

    9. "¿Cuánto puntaje tengo esta semana?"  
    → La palabra clave es “puntaje” (similar a “puntos”) en la semana → **puntos_semana**.

    10. "¿Cuánto he nadado este mes?"  
    → Pregunta sobre la actividad de nadar → **resumen**.
    
    11. "Caminé 10000 pasos"  
    → Es un registro de un hábito realizado → **habito**. 
    
    12. "Hoy he caminado 40 minutos" 
    → Es un registro de un hábito realizado → **habito**. 
    
    13. "Hoy comí comida basura"  
    → Es un registro nuevo de un hábito (sin número, se registra como 1 vez) → **habito**.   
    

    **Si el usuario dice**: 
    - "¿Cuánto caminé esta semana?" y NO menciona la palabra “puntos”: → **resumen**.
    - "¿Cuántos puntos llevo por caminar esta semana?": → menciona “puntos”, se refiere a la semana → **puntos_semana**.

    El usuario ha escrito lo siguiente:
    \"{texto_corregido}\"
    """
    
    # Se realiza la llamada a la API de OpenAI con el prompt
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un clasificador que solo responde con una palabra: 'habito', 'resumen', "
                    "'puntos_semana', 'puntos_totales' o 'ninguna'. "
                    "Si el usuario NO menciona la palabra 'puntos', pero pregunta qué tanto o cuánto "
                    "ha realizado de una actividad (caminar, correr, etc.), responde 'resumen'. "
                    "Sin explicaciones, solo la palabra exacta."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    # Se obtiene la clasificacion y se limpia
    classification = response.choices[0].message.content.strip().lower()
    # Se valida que sea una de las tres palabras esperadas, en caso contrario se marca como "ninguna"
    if classification not in ["habito", "resumen", "puntos_semana", "puntos_totales", "ninguna"]:
        classification = "ninguna"
    return classification


async def procesar_mensaje_principal(
    user_text: str,
    user_id: int,
    update: Update,
    context: CallbackContext
):
    # Esta funcion se encarga de decidir que hacer con el texto del usuario
    # Se llama a la funcion que clasifica la accion
    accion = clasificar_accion(user_text)
    # Si ChatGPT clasifica como habito, se llama a la funcion para anadir la accion en la BBDD
    if accion == "habito":
        await procesar_mensaje_insert(user_text, user_id, update, context)
    # Si clasifica como resumen, se llama a la funcion que genera un resumen
    elif accion == "resumen":
        await procesar_resumen(user_text, user_id, update, context)
    elif accion == "puntos_semana":
        # 1. Calcular puntos de esta semana
        puntos_semana = get_points_accumulated_weekly(user_id)
        # 2. Responder al usuario
        await update.message.reply_text(
            text=f"Esta semana has acumulado {puntos_semana:.1f} puntos. 🏅"
        )

    elif accion == "puntos_totales":
        # 1. Calcular puntos históricos
        puntos_totales = get_points_accumulated_all_time(user_id)
        # 2. Responder
        await update.message.reply_text(
            text=f"Tienes {puntos_totales:.1f} puntos acumulados. 🏆"
        )
    # Si no coincide, se informa al usuario
    else:
        await update.message.reply_text(
        "❌ Lo siento, solo se puede:\n\n"
        "1️⃣ Añadir un hábito ➕\n"
        "2️⃣ Preguntar por tu progreso 📈\n"
        "3️⃣ Preguntar por tus puntos acumulados 🏆\n\n"
        "🙏 Por favor, vuelve a intentarlo."
    )
