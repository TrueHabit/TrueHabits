# OK

from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters, CallbackQueryHandler

from BOT_create.control_teclado import single_register_button, get_five_button_keyboard
from acciones.recibir_texto_organizar import procesar_mensaje_principal
from BBDD_create.funciones_consulta import is_user_registered
from BBDD_create.funciones_informe import generate_dashboard, get_filtered_data, convert_to_dataframe
from BBDD_create.database import SessionLocal
from acciones.accion_add_datos_BBDD import button_callback
import traceback
import os 

async def text_menu_handler(update: Update, context: CallbackContext):
    """
    Esta funcion gestiona los mensajes de texto del usuario y decide que hacer con ellos.
    """
    # Se obtiene el texto enviado por el usuario y se limpian espacios
    user_text = update.message.text.strip()
    
    # Se abre una sesion con la base de datos
    with SessionLocal() as session:
        # Se extrae el id del usuario
        user_id = update.message.from_user.id
        # Se comprueba si el usuario esta registrado en la base de datos
        if not is_user_registered(session, user_id):
            # Se prepara el teclado para registrarse
            keyboard = single_register_button()
            # Se indica que no esta registrado
            mensaje = "👋 ¡Hola! Aún no te has registrado.\nRegístrate usando el botón del teclado para comenzar a disfrutar de todas las funciones. 😊"
            # Se envia el mensaje y se devuelve
            await update.message.reply_text(
                mensaje,
                reply_markup=keyboard
            )
            return

    # Se evalua el texto para ver si coincide con una de las 3 opciones previstas
    if user_text == "Modificar registro":
        # Se indica la accion de abrir el registro para actualizarlo
        '''
        ABRIR EL REGISTRO PARA QUE EL USUARIO LO ACTUALICE
        '''
        
    elif user_text == "Canjear puntos":
        # Se indica la accion de abrir la pagina web para canjear los puntos
        '''
        ABRIR LA PAGINA WEB PARA CANJEAR LOS PUNTOS
        '''

    elif user_text == "Generar informe":
        # Se indica la accion de generar el informe
        '''
        FUNCION PARA GENERAR EL RESUMEN GENERAL DEL USUARIO
        '''
        with SessionLocal() as session:
            user_id = update.message.from_user.id

            # Llama a la función que genera el dashboard
            png_path = generate_dashboard(session, user_id)
            
            if png_path is None:
                # No hay datos; informa al usuario
                await update.message.reply_text(
                    "📭 No tienes hábitos registrados esta semana. ¡Es un buen momento para comenzar! 🚀"
                )
            else: 
                if os.path.exists(png_path):
                    # Enviar el PNG al usuario
                    await update.message.reply_text("📊 Aquí tienes tu informe semanal de hábitos y objetivos. 🚀")
                    await update.message.reply_photo(photo=open(png_path, 'rb'))                    
                else:
                    await update.message.reply_text("No se pudo generar el informe. Revisa si hay datos suficientes.")
    
        # O, opcionalmente, puedes volver a mostrar opciones al final
        await update.message.reply_text(
            "🤔 ¿Qué quieres hacer ahora? 🎯",
            reply_markup=get_five_button_keyboard(user_id)
        )
        return
                        
    else:
        # Se gestiona el caso en el que el usuario escribe algo no contemplado en el teclado principal
        '''
        PROCESAR LO QUE DIGA EL USUARIO EN EL MODO ESCRITURA
        '''
        # Se envia un mensaje al usuario mostrando lo que ha escrito
        # await update.message.reply_text(f"✍️Has escrito lo siguiente:✍️\n {user_text}")
        # Se llama a la funcion principal que decide que hacer con ese texto
        await procesar_mensaje_principal(user_text, user_id, update, context)

        # Al acabar, se muestran las opciones del teclado
        await update.message.reply_text(
            "🤔 ¿Qué quieres hacer ahora? 🎯",
            reply_markup=get_five_button_keyboard(user_id)
        )
        return

def orquestar_acciones(application):
    """
    Esta funcion registra los handlers que gestionan los mensajes de texto y los callbacks en el bot.
    """
    # Se anade un handler para mensajes de texto que no son comandos
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_menu_handler))
    # Se anade un handler para los callbacks de los botones (aceptar, modificar, eliminar)
    application.add_handler(CallbackQueryHandler(button_callback))
