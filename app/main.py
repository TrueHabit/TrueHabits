from BBDD_create.database import main_crear_BBDD
from BOT_create.bot import main_crear_BOT
from acciones.reminder_scheduler import start_scheduler
import logging
import threading

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,  # Nivel de detalle del log
    format="%(asctime)s [%(levelname)s] %(message)s",  # Formato del log
    handlers=[
        logging.FileHandler("/logs/app.log"),  # Archivo de salida de logs
        logging.StreamHandler()  # Enviar también a la salida estándar
    ]
)

logging.info("Iniciando la aplicación TrueHabits...")  # Ejemplo de log

if __name__ == "__main__":

    '''
    El primer paso consiste en crear la Base de datos
    '''
    
    main_crear_BBDD()

    '''
    Como segundo paso hay que levantar el BOT
    '''
    main_crear_BOT()
    
    ''' Iniciar el scheduler de recordatorios ''' 
    start_scheduler()
