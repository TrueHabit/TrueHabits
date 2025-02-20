# OK

import os
import openai
from datetime import datetime
from dateutil import parser as date_parser  # Se importa la libreria para parsear texto a objeto datetime
from config import OPENAI_API_KEY

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler

from BBDD_create.database import get_db
from BBDD_create.database import Habito
from BBDD_create.funciones_add import add_accion
from BBDD_create.funciones_consulta import get_user_habits, get_user_obj, check_habit_completion
from BBDD_create.database import SessionLocal, Accion

from acciones.accion_separar_acciones import separar_acciones
import json

# Se establece la clave de API de OpenAI
openai.api_key = OPENAI_API_KEY

def get_habito_desde_lista(user_text: str, user_id: int) -> str:
    """
    Esta funcion llama a ChatGPT para elegir un habito de la lista o devolver desconocido
    """
    # Se crea la sesion de la base de datos
    with SessionLocal() as session:
        # Se obtienen los habitos del usuario
        lista_habitos = get_user_habits(session, user_id)

    # Se devuelve desconocido si no existen habitos
    if not lista_habitos:
        return "desconocido"

    # Se convierte la lista de habitos en una cadena
    habitos_str = ", ".join(lista_habitos)

    # Se construye el prompt para ChatGPT
    prompt = (
        "Tienes esta lista de habitos del usuario:\n\n"
        f"{habitos_str}\n\n"
        "Texto del usuario:\n"
        f"\"{user_text}\"\n\n"
        "Elige SOLO UNO de esos hábitos que mejor coincida con lo que describe el usuario en su mensaje.\n"
        "Si crees que el mensaje no coincide con ninguno, responde exactamente la palabra 'desconocido'.\n"
        "Sin explicaciones adicionales, solo el hábito o 'desconocido'."
    )

    # Se hace la peticion a la API de OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que debe elegir un habito existente en la lista, o 'desconocido'."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    # Se obtiene la respuesta y se limpia
    habito_result = response.choices[0].message.content.strip()

    # Se valida si la respuesta esta en la lista
    if habito_result not in lista_habitos:
        return "desconocido"
    return habito_result

def get_fecha_realizacion(user_text: str) -> datetime:
    """
    Esta funcion llama a ChatGPT para extraer una fecha y hora en formato YYYY-MM-DD HH:MM, o usar la actual
    """
    # Se obtiene la fecha actual
    fecha_actual = datetime.now()

    # Se construye el prompt para ChatGPT con la fecha actual en caso de no encontrar otra
    prompt = (
        f"Extrae una fecha del siguiente texto, en el formato exacto 'YYYY-MM-DD'.\n"
        f"Si se menciona un período relativo (por ejemplo, 'hace tres días'), calcula la fecha correspondiente "
        f"usando ceros si es necesario para completar el formato.\n"
        f"Si no se menciona ninguna fecha, responde exactamente con '{fecha_actual.strftime('%Y-%m-%d')}'.\n\n"
        f"Sabiendo que hoy es {fecha_actual.strftime('%Y-%m-%d')}, analiza el siguiente texto:\n"
        f"\"{user_text}\"\n\n"
        f"Responde única y exclusivamente con la fecha en el formato exacto 'YYYY-MM-DD'."
    )

    # Se hace la peticion a la API de OpenAI
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que extrae una fecha en formato exacto 'YYYY-MM-DD HH:MM' o dice 'HOY'."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    # Se obtiene la cadena de fecha de la respuesta
    fecha_str = respuesta.choices[0].message.content.strip()

    # Se intenta parsear la fecha
    try:
        fecha = date_parser.parse(fecha_str)
        return fecha
    except Exception:
        # Si hay error, se devuelve la fecha actual
        return fecha_actual


def get_cantidad_ef_unidad(texto, objetivo, unidad_objetivo):
    """
    Esta funcion extrae y convierte la cantidad encontrada en el texto a la unidad objetivo, o devuelve -1 si no procede
    """
    
    prompt_check_unidades = f"""        
    Analiza el texto para identificar que la unidad mencionada corresponde con {unidad_objetivo}.
    Si {unidad_objetivo} es 'veces' o 'vez' y el texto indica la acción sin número, asume 1.
    Devuelve '1' si las unidades son iguales o se pueden convertir o '-1' en caso contrario. 
    
    Ejemplos:
    - Texto: "Hoy corrí 4 kilometros" (unidad_objetivo: "km") => 1
    - Texto: "Hoy caminé 4 mil pasos" (unidad_objetivo: "pasos") => 1
    - Texto: "Ayer leí 10 min" (unidad_objetivo: "páginas") => -1
    - Texto: "Hoy leí 10 paginas" (unidad_objetivo: "paginas") => 1
    - Texto: "Hoy nadé 100 metros" (unidad_objetivo: "minutos") => -1

    Recuerda responder solo con 1 o -1. 
        
    Analiza el texto: "{texto}".
    """
    # Se hace la peticion a la API de OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un asistente que comprueba unidades y devuelve unicamente un 1 o -1."},
                {"role": "user", "content": prompt_check_unidades}
            ],
            max_tokens=100,
            temperature=0.0,
        )
        check_unidades = response['choices'][0]['message']['content'].strip()
        if check_unidades == '-1':
            return -1
    except Exception:
        return -1
    
    prompt = f"""        
    Analiza el texto para:
    1. Identificar la cantidad.
    2. Convertir a la unidad objetivo.
    3. Si la unidad objetivo es 'veces' o 'vez' y el texto indica la acción sin número, asume 1.
    4. Devuelve únicamente el número (int o float) o -1 si no procede.
    
    Ejemplos:
    - Objetivo: "Beber 2 litros al dia" (unidad objetivo: "litros")
    Texto: "Bebi 3 litros" => 3
    - Objetivo: "Correr 5 kilometros al dia" (unidad objetivo: "kilometros")
    Texto: "Corri 200 metros" => 0.2
    - Objetivo: "Correr 3 veces a la semana" (unidad objetivo: "veces")
    Texto: "Hoy corri media hora" => 1
    - Objetivo: "Correr 3 veces a la semana" (unidad objetivo: "veces")
    Texto: "Hoy corri 2 veces" => 2
    - Objetivo: "Correr 5 kilometros" (unidad objetivo: "kilometros")
    Texto: "Hoy corri 3 millas" => 4.828
    - Objetivo: "Beber 2 litros" (unidad objetivo: "litros")
    Texto: "Hoy bebi 2 tazas" => -1
    - Objetivo: "Caminar 10000 pasos" (unidad objetivo: "pasos")
    Texto: "Esta semana caminé 15000 pasos todos los días" (unidad objetivo: "pasos")

    Recuerda, solo tienes que devolver el numero o -1, nada mas
    Importante, puede haber casos ambiguos, haz un esfuerzo por transformar lo que te digan

    Analiza el texto: "{texto}".
    Objetivo: "{objetivo}" (unidad objetivo: "{unidad_objetivo}").
    """

    # Se hace la peticion a la API de OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que devuelve solo un numero (int o float) o -1."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.0,
        )
        contenido = response['choices'][0]['message']['content'].strip()
        # Se intenta convertir la respuesta a float
        try:
            return float(contenido)
        except ValueError:
            return -1
    except Exception:
        return -1


async def button_callback(update: Update, context: CallbackContext):
    """
    Esta funcion maneja los botones de accion (aceptar, modificar, eliminar) en un mensaje
    """
    # Se contesta la accion del boton
    query = update.callback_query
    await query.answer()

    # Se separa el tipo de accion y el id
    data = query.data
    action_type, record_id_str = data.split("_", 1)
    record_id = int(record_id_str)

    # Se guarda el texto antiguo del mensaje
    old_text = query.message.text

    # Se elimina el teclado inline
    await query.edit_message_reply_markup(reply_markup=None)

    # Se comprueba la accion
    if action_type == "aceptar":
        # Se edita el mensaje indicando aceptacion
        await query.edit_message_text(
            text=f"🟩 ACEPTADO\n\n{old_text}"
        )    
        # Obtener información del hábito relacionado
        with SessionLocal() as session:
            accion = session.query(Accion).filter(Accion.id == record_id).first()
            if accion:
                habit_name = accion.habito

    elif action_type == "modificar":
        # Se intenta modificar en la base de datos
        with SessionLocal() as session:
            try:
                session.query(Accion).filter(Accion.id == record_id).delete()
                session.commit()
            except Exception as e:
                await query.message.reply_text(text=f"Error al modificar: {e}")
                return

        # Se edita el mensaje original indicando que ha sido modificado
        await query.edit_message_text(
            text=f"🟧 MODIFICADO\n\n{old_text}"
        )
        # Se solicita nuevo envio
        await query.message.reply_text("🔁Vuelva a enviar el mensaje que quiere modificar🔁")

    elif action_type == "eliminar":
        # Se elimina de la base de datos
        with SessionLocal() as session:
            try:
                session.query(Accion).filter(Accion.id == record_id).delete()
                session.commit()
            except Exception as e:
                await query.message.reply_text(text=f"Error al eliminar el registro: {e}")
                return

        # Se edita el mensaje original indicando que ha sido eliminado
        await query.edit_message_text(
            text=f"🟥 ELIMINADO\n\n{old_text}"
        )
    else:
        # Se informa de error si la accion no existe
        await query.message.reply_text(
            text="Ha ocurrido un error: accion desconocida."
        )


def get_habit_details(session: SessionLocal, user_id: int, habit_name: str):
    """
    Devuelve los detalles de un hábito, incluyendo objetivo, unidad de medida y icono.
    """
    habit = (
        session.query(Habito)
        .filter(Habito.user_id == user_id, Habito.habito == habit_name)
        .first()
    )
    if not habit:
        return None, None, None, None  # Si no existe el hábito
    return habit.objetivo, habit.unidad_medida_objetivo, habit.icono, habit.categoria


async def procesar_mensaje_insert(user_text: str, user_id: int, update: Update, context: CallbackContext):
    """
    Esta funcion procesa el texto del usuario y anade la accion en la base de datos
    """
    # Se obtienen las posibles acciones separadas en la frase
    acciones_list = separar_acciones(user_text)

    # Se recorre cada accion identificada
    for accion in acciones_list:
        # Se obtiene el habito
        habito = get_habito_desde_lista(accion, user_id)
        # Se obtiene la fecha de realizacion
        fecha_realizacion = get_fecha_realizacion(accion)

        # Se realiza la insercion en la base de datos
        with SessionLocal() as session:
            try:
                if habito == "desconocido":
                    # Se informa si el habito no pertenece a la lista
                    lista_habitos = get_user_habits(session, user_id)
                    await update.message.reply_text(
                        f"⚠️😕 {accion} 😕⚠️\n"
                        f"El habito que me has dicho no se encuentra entre las posibles opciones.\n\n"
                        f"• Habitos registrados: {', '.join([f'{habito}' for habito in lista_habitos])}\n"
                    )
                else:
                    # Se obtiene el objetivo y unidad de medida
                    #objetivo, unidad_objetivo = get_user_obj(session, user_id, habito)
                    objetivo, unidad_objetivo, icono, categoria = get_habit_details(session, user_id, habito)
                    # Se obtiene la cantidad transformada a la unidad objetivo usando GPT
                    cantidad = get_cantidad_ef_unidad(texto=accion, objetivo=objetivo, unidad_objetivo=unidad_objetivo)

                    if cantidad == -1:
                        await update.message.reply_text(
                            f"❌ {accion} ❌ \n\n"
                            f"El habito de {habito} no se ha indicado en unidades validas\n"
                            f"• Recuerda que tu objetivo es ('{objetivo}'), se mide en {unidad_objetivo}\n\n"
                            f"Registra el habito nuevamente, por favor"
                        )
                    else:
                        # Se anade la accion a la base de datos
                        accion_creada = add_accion(
                            session,
                            user_id,
                            habito,
                            fecha_realizacion,
                            accion,
                            cantidad
                        )
                        
                        # Se obtiene el id de la accion creada
                        record_id = accion_creada.id

                        # Se construye el teclado con opciones
                        keyboard = [
                            [
                                InlineKeyboardButton("Aceptar",  callback_data=f"aceptar_{record_id}"),
                                InlineKeyboardButton("Modificar", callback_data=f"modificar_{record_id}"),
                                InlineKeyboardButton("Eliminar",  callback_data=f"eliminar_{record_id}"),
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                         # Personalizar el mensaje según la categoría
                        if categoria == "dejar":
                            mensaje = (
                                f"{icono}<b>¡Hábito añadido con éxito!</b> 🎯\n\n"
                                f"Recuerda que estás trabajando para reducir este hábito.\n\n"
                                f"• Hábito: {habito}\n"
                                f"• Fecha: {fecha_realizacion.strftime('%d-%m-%Y')}\n"
                                f"• Cantidad: {cantidad} {unidad_objetivo}"
                            )
                        else:
                            mensaje = (
                                f"{icono} <b>¡Hábito añadido con éxito!</b> 🎯\n\n"
                                f"• Hábito: {habito}\n"
                                f"• Fecha: {fecha_realizacion.strftime('%d-%m-%Y')}\n"
                                f"• Cantidad: {cantidad} {unidad_objetivo}"
                            )

                        await update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode="HTML")

                        # Se envia el mensaje de confirmacion con botones
                        """await update.message.reply_text(
                                f"🎯 ¡Hábito añadido con éxito!\n\n"
                                f"➡️ {accion} ⬅️\n"
                                f"• Hábito: {habito}\n"
                                f"• Fecha: {fecha_realizacion.strftime('%Y-%m-%d')}\n"
                                f"• Cantidad: {cantidad} {unidad_objetivo}",
                                reply_markup=reply_markup
                        )"""
                        
                        objetivo_cumplido, frecuencia = check_habit_completion(session, user_id, habito)
                        if objetivo_cumplido:
                            habito = habito.upper()
                            if categoria == "dejar":
                                await update.message.reply_text(
                                    f"🚨 <b>¡Atención!</b> 🚨 \n\nHas alcanzado el límite máximo para el hábito de eliminar o reducir '{habito}' {icono}\n\n"
                                    f"Es importante seguir trabajando para eliminar o reducir este hábito. ¡Ánimo! 💪",
                                    parse_mode="HTML"
                                )
                            else:
                                await update.message.reply_text(
                                    f"🏆 <b>¡Enhorabuena!</b> 🚀 \n\nHas cumplido tu objetivo {frecuencia} del hábito '{habito}' {icono}",
                                    parse_mode="HTML"
                                )
                            
            except Exception as e:
                # Se informa de error en caso de fallo
                await update.message.reply_text(
                    f"❌ {accion} ❌\n\n"
                    f"⚠️ Ha ocurrido un error al guardar tu registro:\n"
                    f"• {e}\n\n"
                    f"📞 Por favor, contacta con atención al cliente si el problema persiste. Gracias por tu paciencia. 🙏"
                )

