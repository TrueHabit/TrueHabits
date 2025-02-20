# OK

from telegram import (
    Update
)
from telegram.ext import (
    CallbackContext, MessageHandler, filters
)
import json
import os
import librosa
import soundfile as sf
import speech_recognition as sr
from BOT_create.control_teclado import get_five_button_keyboard
from acciones.recibir_texto_organizar import procesar_mensaje_principal

# Se importa openai para posibles llamadas a la API
import openai

def transcribe_audio(audio_file: str):
    # Se transcribe un archivo de audio ogg a texto
    # Primero se carga el archivo .ogg y se convierte a WAV
    try:
        audio, sr_rate = librosa.load(audio_file, sr=16000)
        wav_file = "temp.wav"
        sf.write(wav_file, audio, sr_rate)

        # Se utiliza speech_recognition para transcribir el archivo WAV
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            transcription = recognizer.recognize_google(audio_data, language="es-ES")

        # Se elimina el archivo WAV temporal
        os.remove(wav_file)
        # Se devuelve la transcripcion
        return transcription
    except Exception as e:
        return f"Error al transcribir el audio: {e}"

async def audio_handler(update: Update, context: CallbackContext):
    # Se gestiona la llegada de un archivo de audio
    # Primero se comprueba si existe el directorio de audios y se crea si no existe
    audio_dir = "./Audios"
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    try:
        # Se descarga el audio recibido de Telegram
        audio_file = await update.message.voice.get_file()
        file_path = f"{audio_dir}/audio_{update.message.message_id}.ogg"
        await audio_file.download_to_drive(file_path)

        # Se transcribe el audio descargado
        transcription = transcribe_audio(file_path)

        # Se comprueba si se ha producido algun error durante la transcripcion
        if "Error" in transcription:
            await update.message.reply_text(transcription)
        else:
            # Se informa al usuario de lo que se ha entendido
            user_id = update.message.from_user.id
            #await update.message.reply_text(f"🔊He entendido lo siguiente:🔊\n {transcription}")
            # Se procesa el texto transcrito para anadirlo a la base de datos
            await procesar_mensaje_principal(transcription, user_id, update, context)

        # Se elimina el archivo de audio original
        os.remove(file_path)

        # Al acabar, se muestran las opciones del teclado
        await update.message.reply_text(
            "🤔 ¿Qué quieres hacer ahora? 🎯",
            reply_markup=get_five_button_keyboard(user_id)
        )

    except Exception as e:
        # Se informa al usuario en caso de error
        await update.message.reply_text(
            f"❌ Error al procesar el audio: {e} ⚠️\n\n"
            f"🎙️ Por favor, intenta nuevamente. Si el problema persiste, contacta con soporte técnico. 🙏"
        )


def manejar_audios(application):
    # Se anade un handler para interceptar los mensajes de audio
    application.add_handler(MessageHandler(filters.VOICE, audio_handler))
