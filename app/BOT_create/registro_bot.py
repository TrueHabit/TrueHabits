# OK

from telegram import (
    Update
)
from telegram.ext import (
    CallbackContext, MessageHandler, filters
)
import json
from BBDD_create.funciones_add import *
from BBDD_create.database import SessionLocal
from BBDD_create.funciones_consulta import is_user_registered
from BOT_create.control_teclado import single_register_button, get_five_button_keyboard

import openai
from config import OPENAI_API_KEY

import json

GIF_URL = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExNml5a3FkNmF4NHpyc3UzeXV1NGd3dHU4eWc4YWdmcms5NGszbWlhdSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/NGAkGHzGW86pNj4h49/giphy.gif"

openai.api_key = OPENAI_API_KEY

def get_cantidad_y_unidad(texto, frecuencia="diaria"):
    # Esta funcion analiza un texto de objetivo personal y devuelve una unidad y una cantidad asociada para guardarlo en la BBDD.
    # Se basa en la frecuencia (diaria, semanal o mensual) y en si hay unidades explicitas o no.
    # Devuelve una tupla (unidad, cantidad).

    # Se construye el prompt para enviarlo a ChatGPT
    prompt_corregir = f"""
    A partir del siguiente texto en español sobre un objetivo personal, primero corrige posibles errores de tipeo 
    (especialmente en unidades y palabras). No inventes contenido nuevo, solo corrige faltas evidentes.
    
    Texto: "{texto}"
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
    A partir del siguiente texto sobre un objetivo personal, extrae la cantidad total y la unidad asociada.
    Ten en cuenta que el objetivo tiene una frecuencia: "{frecuencia}".
    
    Reglas:
    1. Si el texto incluye unidades explicitas (p. ej. "km", "litros", "paginas", "sentadillas") y tambien un numero de dias
       (o veces), multiplica la cantidad base por ese numero.
    2. Si el texto incluye unidades explicitas pero no menciona dias (o repeticiones), toma la cantidad tal cual.
    3. Si el texto no especifica unidades, se asume la unidad "veces" y se multiplica segun la frecuencia.
    4. Responde unicamente en formato JSON con las claves "cantidad" y "unidad".

    Ejemplos:

    EJEMPLO 1:
    Texto: "Correr 20 km 3 dias", Frecuencia: "semanal"
    Explicacion: 20 km x 3 = 60 km.
    Salida JSON:
    {{
      "cantidad": 60,
      "unidad": "km"
    }}

    EJEMPLO 2:
    Texto: "Beber 2 litros de agua", Frecuencia: "diaria"
    Explicacion: Hay unidad explicita (litros). No menciona dias ni repeticiones extra.
    Salida JSON:
    {{
      "cantidad": 2,
      "unidad": "litros"
    }}

    EJEMPLO 3:
    Texto: "Hacer 50 sentadillas 5 dias", Frecuencia: "mensual"
    Explicacion: 50 sentadillas x 5 dias = 250 sentadillas.
    Salida JSON:
    {{
      "cantidad": 250,
      "unidad": "sentadillas"
    }}

    EJEMPLO 4:
    Texto: "Meditar", Frecuencia: "diaria"
    Explicacion: No hay unidades ni dias. Se asume unidad "veces" y frecuencia diaria = 1.
    Salida JSON:
    {{
      "cantidad": 1,
      "unidad": "veces"
    }}

    EJEMPLO 5:
    Texto: "Leer 10 paginas al dia durante 7 dias", Frecuencia: "semanal"
    Explicacion: 10 paginas x 7 dias = 70 paginas.
    Salida JSON:
    {{
      "cantidad": 70,
      "unidad": "paginas"
    }}

    EJEMPLO 6:
    Texto: "Correr 20 km a la semana", Frecuencia: "semanal"
    Explicacion: Dice 20 km a la semana y ya esta semanal.
    Salida JSON:
    {{
      "cantidad": 20,
      "unidad": "km"
    }}

    AHORA:
    Texto objetivo: "{texto_corregido}"
    Devuelve UNICAMENTE un JSON con "cantidad" y "unidad".
    """

    # Se hace la llamada a ChatGPT
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente util que analiza un texto con un objetivo personal y devuelve un JSON "
                        "con las claves 'cantidad' y 'unidad'."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.0,
        )
        
        # Se obtiene el contenido de la respuesta de ChatGPT
        contenido = response['choices'][0]['message']['content'].strip()
        
        # Se intenta parsear como JSON
        try:
            resultado = json.loads(contenido)
            return resultado.get('unidad'), resultado.get('cantidad')
        except json.JSONDecodeError:
            # Se informa si no se puede parsear
            print(f"Error al analizar JSON: {contenido}")
            return None, None
        
    except Exception as e:
        # Se registra el error y se devuelven valores nulos
        print(f"Error al procesar el objetivo: {e}")
        return None, None

async def web_app_data(update: Update, context: CallbackContext):
    # Esta funcion maneja los datos que llegan desde la WebApp. Se anaden o modifican datos del usuario en la base de datos
    # y luego se muestra la informacion al usuario.

    # Se extraen los datos del mensaje
    data = json.loads(update.message.web_app_data.data)
    print("Recibido desde la WebApp:", data)

    # Se obtiene el user_id
    user_id = update.message.from_user.id
    print("Mensaje de ", user_id)

    # Se extrae la informacion principal del JSON
    nombre = data.get("nombre", "")
    edad = data.get("edad", "")
    sexo = data.get("sexo")
    habitos = data.get("habitos", [])
    objetivos = data.get("objetivos", [])

    # Se combinan habitos y objetivos en base a su categoria y habito
    habitos_con_objetivos = {
        (cat, hab): (obj_text, freq)
        for cat, hab, obj_text, freq in objetivos
    }
    habitos_completos = [
        (
            cat,
            hab,
            icon,
            habitos_con_objetivos.get((cat, hab), (None, None))[0],
            habitos_con_objetivos.get((cat, hab), (None, None))[1]
        )
        for cat, hab, icon in habitos
    ]

    # Se calculan las unidades y cantidades de cada objetivo usando get_cantidad_y_unidad
    habitos_completos_trans = []
    for cat, hab, icon, obj_text, freq in habitos_completos:
        unidad, cantidad = get_cantidad_y_unidad(obj_text, frecuencia=freq)
        habitos_completos_trans.append((cat, hab, icon, obj_text, freq, unidad, cantidad))

    # Se guarda en la base de datos mediante modify_usuario y modify_habitos
    with SessionLocal() as session:
        try:
            # Se actualiza o crea el usuario con sus datos
            modify_usuario(session, user_id=user_id, nombre=nombre, edad=edad, sexo=sexo)
            # Se actualizan los habitos con sus objetivos transformados
            modify_habitos(session, user_id, habitos_completos_trans)
        except Exception as e:
            # Si se produce error, se avisa y se sale
            print(f"Error procesando datos de la WebApp: {e}")
            await update.message.reply_text(
                "😔 Disculpe las molestias, ha habido un problema con la base de datos de la aplicación. 🛠️ Estamos trabajando para solucionarlo."
            )

            raise
        
    # Generar mensaje
    with SessionLocal() as session:
        if is_user_registered(session, user_id):
            # Modificar registro
            mensaje = f"<b>¡Hola, {nombre.capitalize()}! 😎</b>\n"
            mensaje += "\n¡Tu perfil ha sido modificado con éxito! Cada ajuste te acerca más a tus objetivos. 🔥\n"
        else:
            # Nuevo registro
            if sexo == "femenino":
                mensaje = f"<b>🎉 ¡Bienvenida, {nombre.capitalize()}! 🎉</b>\n"
            elif sexo == "masculino":
                mensaje = f"<b>🎉 ¡Bienvenido, {nombre.capitalize()}! 🎉</b>\n"
            else:
                mensaje = f"<b>🎉 ¡Bienvenidx, {nombre.capitalize()}! 🎉</b>\n"
            mensaje += "Nos emociona tenerte en <b>TrueHabits</b>, donde cada hábito te acerca a tu mejor versión 🚀"
        
        # Listado de hábitos registrados
        mensaje += "\n<b>🚀 Tus hábitos registrados:</b>\n"
        for (cat, hab, icon) in habitos:
            if cat.lower() == "dejar":
                mensaje += f"  {icon} Eliminar/Reducir {hab.lower()}\n"
            else:
                mensaje += f"  {icon} {hab}\n"
        mensaje += "\n"
        
        # Listado de objetivos asociados a cada hábito
        mensaje += "<b>🎯 Tus objetivos:</b>\n"
        for (cat, hab, icon, obj_text, freq) in habitos_completos:
            if cat.lower() == "dejar":
                mensaje += f"  {icon} <b>Eliminar/Reducir {hab.lower()}</b> - {obj_text.lower()} <i>({freq.capitalize()})</i>\n"
            else:
                mensaje += f"  {icon} <b>{hab}</b> - {obj_text.lower()} <i>({freq.capitalize()})</i>\n"
        
        # Mensaje de cierre motivador
        mensaje += "\n📊 ¡Acompañaremos cada paso de tu progreso! 🏆\n"         
    
    # Se envia un GIF de confirmacion
    await update.message.reply_animation(
        animation=GIF_URL
    )
    
    # Se comprueba si el usuario ha quedado registrado en la base de datos
    with SessionLocal() as session:
        if is_user_registered(session, user_id):
            keyboard = get_five_button_keyboard(user_id)
        else:
            keyboard = single_register_button()
            mensaje = "👋 ¡Hola! Aún no te has registrado.\nRegístrate usando el botón del teclado para comenzar a disfrutar de todas las funciones. 😊"

    # Se envia el mensaje final con el teclado correspondiente
    await update.message.reply_text(
        text=mensaje,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def datos_registro(application):
    # Esta funcion registra el handler que captura los datos de la WebApp
    # y llama a web_app_data cuando llegan esos datos
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
