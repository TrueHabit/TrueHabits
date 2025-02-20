# OK

from telegram import (
    Update
)
from telegram.ext import (
    CallbackContext, CommandHandler
)
from BBDD_create.database import SessionLocal
from BBDD_create.funciones_consulta import is_user_registered
from BOT_create.control_teclado import single_register_button, get_five_button_keyboard


# Esta funcion se activa cuando el usuario invoca /start
async def launch_web_ui(update: Update, context: CallbackContext):
    # Se obtiene el id del usuario como cadena
    user_id = str(update.effective_user.id)

    # Se abre la sesion con la base de datos
    with SessionLocal() as session:
        # Se comprueba si el usuario esta registrado en la base de datos
        if is_user_registered(session, user_id):
            # Se crea un teclado con cinco botones
            keyboard = get_five_button_keyboard(user_id)
            # Se define el mensaje a enviar
            message = "✅ ¡Ya estás registrado! \n 🎉 Sigue utilizando la aplicación como siempre. 🚀"
        else:
            # Se crea un teclado con un unico boton
            keyboard = single_register_button()
            # Se define el mensaje de no registro
            message = "👋 ¡Hola! Aún no te has registrado.\nRegístrate usando el botón del teclado para comenzar a disfrutar de todas las funciones. 😊"

    # Se envia un mensaje al usuario con el teclado correspondiente
    await update.message.reply_text(
        text=message,
        reply_markup=keyboard
    )


def iniciar_bot(application):
    # Se anade el handler para /start que llama a la funcion launch_web_ui
    application.add_handler(CommandHandler('start', launch_web_ui))
