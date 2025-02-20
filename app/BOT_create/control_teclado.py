# OK

import json
import urllib.parse
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo
)
from BBDD_create.database import SessionLocal
from BBDD_create.database import Usuario
from BBDD_create.funciones_informe import get_points_accumulated_all_time

def single_register_button():
    """
    Esta funcion crea un teclado con un unico boton para el registro via WebApp
    """
    # Se define la estructura del teclado con un unico boton
    kb = [
        [KeyboardButton(
            text="Hacer registro",
            web_app=WebAppInfo(url="https://truehabit.github.io/TrueHabit/")
        )],
        [KeyboardButton(
            text="FAQs",
            web_app=WebAppInfo(url="https://truehabit.github.io/FAQs/")
        )]
    ]
    # Se devuelve el teclado con el boton configurado
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_five_button_keyboard(user_id: int):
    """
    Esta funcion crea un teclado con cinco botones
    """
    # Se define la URL base donde se encuentra la WebApp
    base_url = "https://truehabit.github.io/TrueHabit/"

    # Se establece una sesion con la base de datos
    with SessionLocal() as session:
        # Se obtiene el objeto Usuario asociado al user_id
        user = session.query(Usuario).filter(Usuario.user_id == user_id).one()

        # Se inicializan listas para los habitos y objetivos
        habitos_list = []
        objetivos_list = []
        # Se recorre cada habito del usuario
        for hab in user.habitos:
            cat = "deporte" if hab.categoria == "Caminar" else (hab.categoria or "otro")
            habito = hab.habito
            icon = hab.icono
            # Se anade el habito a la lista de habitos
            habitos_list.append([cat, habito, icon])

            # Se comprueba si existe objetivo para el habito y se anade si procede
            if hab.objetivo:
                obj_text = hab.objetivo
                freq = hab.frecuencia_objetivo or ""
                objetivos_list.append([cat, habito, obj_text, freq])

        # Se crea un diccionario con la informacion del usuario
        data_dict = {
            "nombre": user.nombre,
            "edad": user.edad,
            "sexo": user.sexo,
            "habitos": habitos_list,
            "objetivos": objetivos_list
        }

        # Se convierte el diccionario a JSON y se codifica para incluirlo en la URL
        data_json = json.dumps(data_dict)
        data_json_quoted = urllib.parse.quote(data_json, safe="")

        # Se compone la URL final con la informacion de usuario
        url_con_datos = f"{base_url}?data={data_json_quoted}"
        
                # PUNTOS
        puntos_totales = get_points_accumulated_all_time(user_id)
        puntos_totales = round(puntos_totales, 1)
        url_puntos = "https://truehabit.github.io/Canjear_TH/"
        url_canje_puntos = f"{url_puntos}?usuario={user.nombre}&puntos={puntos_totales}"             

    # Se define la estructura de teclado con botones
    kb_five_buttons = [
        [
            KeyboardButton(
                text="Modificar registro",
                web_app=WebAppInfo(url=url_con_datos)
            )
        ],
        [
            KeyboardButton(
                text="Canjear puntos",
                web_app=WebAppInfo(url=url_canje_puntos)
            )
        ],
        [
            KeyboardButton(text="Generar informe")
        ],
        [
            KeyboardButton(
                text="FAQs",
                web_app=WebAppInfo(url="https://truehabit.github.io/FAQs/")
            )
        ]
    ]
    # Se devuelve el teclado con tres botones
    return ReplyKeyboardMarkup(kb_five_buttons, resize_keyboard=True)
