from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import calendar
from BBDD_create.database import Usuario, Habito, Accion

def add_usuario(db, user_id, nombre, edad, sexo):
    # Esta funcion anade un usuario en la tabla de usuarios
    try:
        # Se crea la instancia del modelo con la informacion
        usuario = Usuario(
            user_id=user_id,
            nombre=nombre,
            edad=edad,
            sexo=sexo
        )
        # Se anade el usuario a la sesion
        db.add(usuario)
        # Se confirman los cambios
        db.commit()
        # Se actualiza la instancia del usuario
        db.refresh(usuario)
        # Se informa que el usuario se anadio correctamente
        print(f"Usuario anadido correctamente: {usuario}")
    except IntegrityError as e:
        # Se deshacen los cambios si ocurre un error de integridad
        db.rollback()
        # Se muestra el error
        print(f"Error al anadir el usuario {user_id}: {e}")
        # Se relanza la excepcion para manejarla fuera
        raise

def modify_usuario(db, user_id, nombre=None, edad=None, sexo=None):
    """
    Modifica los datos de un usuario existente sin eliminar sus relaciones.
    """
    try:
        # Busca el usuario en la base de datos
        usuario = db.query(Usuario).filter_by(user_id=user_id).first()

        if not usuario:
            add_usuario(db, user_id, nombre, edad, sexo)
            usuario = db.query(Usuario).filter_by(user_id=user_id).first()

        # Actualiza los campos según los parámetros proporcionados
        if nombre is not None:
            usuario.nombre = nombre
        if edad is not None:
            usuario.edad = edad
        if sexo is not None:
            usuario.sexo = sexo

        # Confirma los cambios
        db.commit()
        # Refresca la instancia para reflejar los cambios
        db.refresh(usuario)
        print(f"Usuario modificado correctamente: {usuario}")
    except Exception as e:
        # Si hay un error, deshace los cambios
        db.rollback()
        print(f"Error al modificar el usuario {user_id}: {e}")
        raise
    
def add_habito(db, user_id, habito, icono, categoria=None, objetivo=None, frecuencia_objetivo=None, unidad_medida_objetivo=None, cantidad_objetivo=None):
    # Esta funcion anade un habito a la tabla habitos
    try:
        if habito == "Caminar":
            categoria_r = "Caminar"
        else:
            categoria_r = categoria
        # Se crea la instancia del modelo Habito con la informacion
        habito_obj = Habito(
            user_id=user_id,
            habito=habito,
            icono=icono,
            categoria=categoria_r,
            objetivo=objetivo,
            frecuencia_objetivo=frecuencia_objetivo,
            unidad_medida_objetivo=unidad_medida_objetivo,
            cantidad_objetivo=cantidad_objetivo
        )
        # Se anade el habito a la sesion
        db.add(habito_obj)
        # Se confirman los cambios
        db.commit()
        # Se actualiza la instancia del habito
        db.refresh(habito_obj)
        # Se informa que el habito se anadio correctamente
        print(f"Habito anadido correctamente: {habito_obj}")
    except IntegrityError as e:
        # Se deshacen los cambios en caso de error de integridad
        db.rollback()
        # Se muestra el error
        print(f"Error al anadir el habito '{habito}' para el usuario {user_id}: {e}")
        # Se relanza la excepcion
        raise


def modify_habitos(db, user_id, habitos):
    """
    Modifica los hábitos específicos de un usuario sin eliminar otros hábitos ni sus acciones relacionadas.
    """
    try:
        # Obtener todos los hábitos actuales del usuario en la base de datos
        habitos_actuales = db.query(Habito).filter_by(user_id=user_id).all()
        
        # Crear un conjunto de nombres de hábitos proporcionados en la nueva lista
        nuevos_habitos_nombres = {habito[1] for habito in habitos}  # El segundo elemento es el nombre del hábito

        # Iterar por los hábitos existentes y eliminar los que no estén en la nueva lista
        for habito_existente in habitos_actuales:
            if habito_existente.habito not in nuevos_habitos_nombres:
                # Eliminar el hábito y las acciones relacionadas
                db.query(Accion).filter_by(user_id=user_id, habito=habito_existente.habito).delete()
                db.delete(habito_existente)
                
        for (categoria, habito, icono, objetivo, frecuencia, unidad_medida_objetivo, cantidad_objetivo) in habitos:
            # Buscar el hábito en la base de datos
            habito_obj = db.query(Habito).filter_by(user_id=user_id, habito=habito).first()
            
            if habito_obj:
                # Si el hábito es "Deporte", cambiar su categoría a "Caminar"
                if habito == "Caminar": #or (habito_obj.habito == "Deporte" and habito == "Caminar"):
                    habito_obj.categoria = "Caminar"
                    habito_obj.habito = "Caminar"
                else:
                    habito_obj.categoria = categoria

            if habito_obj:
                # Actualizar los campos del hábito existente
                habito_obj.icono = icono
                habito_obj.objetivo = objetivo
                habito_obj.frecuencia_objetivo = frecuencia
                habito_obj.unidad_medida_objetivo = unidad_medida_objetivo
                habito_obj.cantidad_objetivo = cantidad_objetivo
            else:
                # Si el hábito no existe, añadirlo como nuevo
                add_habito(
                    db,
                    user_id,
                    habito,
                    icono,
                    categoria,
                    objetivo,
                    frecuencia,
                    unidad_medida_objetivo=unidad_medida_objetivo,
                    cantidad_objetivo=cantidad_objetivo
                )

        # Confirmar los cambios
        db.commit()
    except Exception as e:
        # Si ocurre un error, deshacer los cambios
        db.rollback()
        print(f"Error al modificar los hábitos del usuario {user_id}: {e}")
        raise

def add_accion(db, user_id, habito, fecha_realizacion, texto, cantidad):
    # Esta funcion anade una accion a la tabla acciones
    try:
        # Se crea la instancia del modelo Accion con la informacion
        accion = Accion(
            user_id=user_id,
            habito=habito,
            fecha_realizacion=fecha_realizacion,
            texto=texto,
            cantidad=cantidad
        )
        # Se anade la accion a la sesion
        db.add(accion)
        # Se confirman los cambios
        db.commit()
        # Se actualiza la instancia de la accion
        db.refresh(accion)
        # Se informa que la accion se anadio correctamente
        print(f"Accion anadida correctamente: {accion}")
        return accion
    except IntegrityError as e:
        # Se deshacen los cambios en caso de error de integridad
        db.rollback()
        # Se muestra el error
        print(f"Error al anadir la accion para el habito '{habito}' del usuario {user_id}: {e}")
        # Se relanza la excepcion
        raise

def modify_acciones(db, user_id, acciones):
    # Esta funcion elimina las acciones existentes de un usuario y anade nuevas
    try:
        # Se eliminan las acciones actuales del usuario
        db.query(Accion).filter_by(user_id=user_id).delete()
        db.commit()
        # Se recorre la lista de acciones para anadirlas
        for (habito, fecha_realizacion, texto, cantidad) in acciones:
            add_accion(db, user_id, habito, fecha_realizacion, texto, cantidad)
    except Exception as e:
        # Si ocurre un error se deshacen los cambios
        db.rollback()
        # Se muestra el error
        print(f"Error al modificar las acciones del usuario {user_id}: {e}")
        # Se relanza la excepcion
        raise
