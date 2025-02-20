# OK

from config import TELEGRAM_TOKEN
from BOT_create.start_bot import iniciar_bot
from BOT_create.registro_bot import datos_registro
from BOT_create.orquestador_acciones import orquestar_acciones
from acciones.accion_audio import manejar_audios
from telegram.ext import (
    ApplicationBuilder
)

# Se define el nombre de usuario del bot y la URL del GIF
BOT_USERNAME = 'truehabits_bot'

def main_crear_BOT():
    # Se construye la aplicacion del bot con el token de Telegram
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Se inicia el bot con el handler para /start
    iniciar_bot(application)

    # Se registra el handler para recibir los datos de registro desde la WebApp
    datos_registro(application)

    # Se anade la gestion de audios
    manejar_audios(application)

    # Se anade la orquestacion de acciones (textos y callbacks)
    orquestar_acciones(application)

    # Se muestra por consola que el bot se ha iniciado
    print(f"Bot iniciado. Visita http://t.me/{BOT_USERNAME} para probarlo.")
    # Se inicia la escucha de eventos
    application.run_polling(timeout=10)
