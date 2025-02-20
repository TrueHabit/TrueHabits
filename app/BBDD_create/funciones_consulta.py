#OK

from sqlalchemy.orm import Session
from sqlalchemy import func
from BBDD_create.database import Usuario, Habito, Accion

def is_user_registered(db: Session, user_id: int) -> bool:
    # Esta funcion comprueba si un usuario esta registrado en la base de datos
    # Devuelve True si existe y False en caso contrario
    return db.query(Usuario).filter_by(user_id=user_id).first() is not None

def get_user_habits(db: Session, user_id: int):
    # Esta funcion obtiene la lista de habitos registrados de un usuario
    habitos_usuario = db.query(Habito.habito).filter_by(user_id=user_id).all()
    # Se forma la lista de habitos a partir de las tuplas obtenidas
    habitos_list = [h[0] for h in habitos_usuario]
    return habitos_list

def get_user_obj(db: Session, user_id: int, habito: str):
    # Esta funcion devuelve una tupla con el objetivo y la unidad de medida
    # o None si no existe en la base de datos
    habito_obj = (
        db.query(Habito.objetivo, Habito.unidad_medida_objetivo)
        .filter(
            Habito.user_id == user_id,
            func.lower(Habito.habito) == func.lower(habito)
        )
        .first()
    )
    return habito_obj

def check_habit_completion(session: Session, user_id: int, habit_name: str):
    """
    Comprueba si un hábito ha cumplido su objetivo para un usuario específico.
    """
    # Obtener el hábito del usuario
    habit = (
        session.query(Habito)
        .filter(Habito.user_id == user_id, Habito.habito == habit_name)
        .first()
    )
    if not habit:
        return False  # Si no existe el hábito, no hay objetivo que cumplir

    # Calcular el progreso actual
    total_acciones = (
        session.query(func.sum(Accion.cantidad))
        .filter(Accion.user_id == user_id, Accion.habito == habit_name)
        .scalar()
    )
    # Verificar si se cumplió el objetivo
     # Verificar si se cumplió el objetivo
    objetivo_cumplido = total_acciones >= habit.cantidad_objetivo if total_acciones else False
    
    # Transformar la frecuencia si es "diaria"
    frecuencia = habit.frecuencia_objetivo
    if frecuencia == "diaria":
        frecuencia = "diario"

    # Retornar el estado de cumplimiento y la frecuencia
    return objetivo_cumplido, frecuencia


