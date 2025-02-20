# OK

import openai
import io
import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from telegram import Update
from telegram.ext import CallbackContext
from collections import defaultdict

from config import OPENAI_API_KEY
from BBDD_create.database import SessionLocal
from BBDD_create.funciones_consulta import get_user_habits
from BBDD_create.database import Accion, Habito
from sqlalchemy import func

from acciones.accion_cumplir_objetivos import get_objetivo_mensaje

def parse_resumen_info(user_text: str, lista_habitos: list) -> tuple:
    # Funcion que llama a ChatGPT para analizar el texto del usuario y extraer la informacion principal (HABITO, START DATE, END DATE)
    # Se crea un string que contiene la instruccion y el contexto que ChatGPT necesita
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    habitos_str = ", ".join(lista_habitos) if lista_habitos else "N/A"
    prompt = f"""
        Eres un asistente que procesa informacion de habitos del usuario y genera una respuesta en formato JSON basandote en el texto del usuario.

        Contexto:
        - Tienes una lista de habitos del usuario.
        - El usuario hace una consulta en texto libre.
        - Debes:
        1. Identificar un habito que coincida con el texto del usuario o responder "desconocido" si no hay coincidencia.
        2. Extraer un rango de fechas en formato ISO 8601 'YYYY-MM-DDTHH:mm:ss' para las claves `start_date` y `end_date`:
            - Si no se menciona explicitamente un rango de fechas, por defecto usa 30 dias atras para `start_date` (a las 00:00:01) y el dia de hoy, `{hoy_str}` (a las 23:59:59), para `end_date`.
            - Si el texto incluye frases como "los ultimos tres dias", interpreta el rango de fechas con base en el dia actual, pero siempre usando `T00:00:01` para la fecha inicial y `T23:59:59` para la fecha final de cada dia calculado.
            - Si el texto incluye frases como "esta semana", interpreta el rango de fechas con base en el dia actual y tomando en cuenta que la semana es de lunes a domingo, pero siempre usando `T00:00:01` para la fecha inicial y `T23:59:59` para la fecha final de cada dia calculado.
        3. Responde siempre con un JSON EXACTO que incluya las claves: "habito", "start_date", "end_date".

        Datos del usuario que tienes que responder en base a las instrucciones y los ejemplos anteriores:
        - Lista de habitos del usuario: [{habitos_str}]
        - Texto del usuario: "{user_text}"
        - Fecha actual: {hoy_str}
    """

    # Se hace la llamada a la API de OpenAI para obtener la respuesta en formato JSON
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente que devuelve un JSON con las claves "
                        "'habito', 'start_date', 'end_date' y 'tipo_resumen'."
                    )
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0
        )
        respuesta_chatgpt = response.choices[0].message.content.strip()
    except Exception as e:
        # Si hay un error en la llamada, se informa y se devuelven valores por defecto
        print(f"[ERROR ChatGPT parse_resumen_info] {e}")
        return ("desconocido", None, None, "desconocido")

    # Se intenta parsear la respuesta como JSON
    import json
    try:
        parsed = json.loads(respuesta_chatgpt)
        habito_obtenido = parsed.get("habito", "desconocido")
        start_str = parsed.get("start_date", hoy_str)
        end_str = parsed.get("end_date", hoy_str)
        start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
        end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")

        # Se comprueba si el habito esta en la lista. Si no, se marca como desconocido
        habito_en_lista = any(habito_obtenido.lower() == h.lower() for h in lista_habitos)
        if not habito_en_lista:
            habito_obtenido = "desconocido"

        return (habito_obtenido, start_date, end_date)

    except Exception as e:
        # Si hay un error parseando el JSON, se informa y se devuelven valores por defecto
        print(f"[ERROR parse JSON ChatGPT] {e}")
        return ("desconocido", None, None)

async def procesar_resumen(user_text: str, user_id: int, update: Update, context: CallbackContext):
    # Esta funcion se encarga del flujo principal para procesar la peticion de resumen del usuario (preguntar sobre cosas registras en la app)
    # Se obtiene la sesion de la base de datos y la lista de habitos
    with SessionLocal() as session:
        lista_habitos = get_user_habits(session, user_id)

    # Se comprueba si el usuario tiene habitos registrados
    if not lista_habitos:
        await update.message.reply_text("🚀No tienes habitos registrados.\n ¡Primero registra algun habito!")
        return

    # Se llama a parse_resumen_info para extraer habito y rango de fechas
    habito, start_date, end_date = parse_resumen_info(user_text, lista_habitos)

    # Se valida si se ha obtenido habito y fechas
    if habito == "desconocido" or start_date is None or end_date is None:
        await update.message.reply_text(
            "Lo siento, no he podido entender el habito o las fechas. "
            "Verifica que tengas un habito valido y menciones un rango de fechas."
        )
        return

    start_date = start_date.date()
    end_date = end_date.date() 
    # Se hace otra consulta a la base de datos para obtener la suma de la cantidad
    with SessionLocal() as session:
        valor_logrado = (
            session.query(func.sum(Accion.cantidad))
            .filter(Accion.user_id == user_id)
            .filter(func.lower(Accion.habito) == func.lower(habito))
            .filter(Accion.fecha_realizacion >= start_date)
            .filter(Accion.fecha_realizacion <= end_date)
            .scalar()
        )

        # Se busca la informacion del habito
        habito_obj = (
            session.query(Habito)
            .filter(Habito.user_id == user_id, func.lower(Habito.habito) == func.lower(habito))
            .first()
        )

    # Se comprueba si hay acciones que mostrar en el rango de fechas indicado
    if not valor_logrado:
        await update.message.reply_text(
            f"💢😕 \n No se encontraron acciones para el habito '{habito}' "
            f"entre {start_date.date()} y {end_date.date()}."
        )
        return

    # Se comprueba el objetivo del habito y se genera un mensaje motivacional en caso de existir
    with SessionLocal() as session:
        msg_objetivo = get_objetivo_mensaje(session, user_id, user_text, habito, valor_logrado, habito_obj)

    # Si existe el mensaje de objetivo, se envia al usuario
    if msg_objetivo.strip():
        await update.message.reply_text(msg_objetivo)
