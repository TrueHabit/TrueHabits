# OK

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKeyConstraint,
    Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL  

# Se declara la base para los modelos
Base = declarative_base()

class Usuario(Base):
    """
    Esta clase representa la tabla usuarios en la base de datos
    """

    # Se define el nombre de la tabla
    __tablename__ = "usuarios"

    # Se definen las columnas
    user_id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    edad = Column(Integer, nullable=False)
    sexo = Column(String, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    # Se establece la relacion con la clase Habito
    habitos = relationship("Habito", back_populates="usuario", cascade="all, delete")


class Habito(Base):
    """
    Esta clase representa la tabla habitos en la base de datos
    """

    # Se define el nombre de la tabla
    __tablename__ = "habitos"

    # Se definen las columnas y las claves primarias
    user_id = Column(BigInteger, primary_key=True)
    habito = Column(String, primary_key=True)
    icono = Column(String, nullable=True, default=None)
    categoria = Column(String, nullable=True)
    objetivo = Column(String, nullable=True)
    frecuencia_objetivo = Column(String, nullable=True)
    unidad_medida_objetivo = Column(String, nullable=True)
    cantidad_objetivo = Column(Float, nullable=True)

    # Se establecen las claves foraneas
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['usuarios.user_id']),
    )

    # Se establece la relacion con la clase Usuario
    usuario = relationship("Usuario", back_populates="habitos")

    # Se establece la relacion con la clase Accion
    acciones = relationship("Accion", back_populates="habito_relacion", cascade="all, delete")


class Accion(Base):
    """
    Esta clase representa la tabla acciones en la base de datos
    """

    # Se define el nombre de la tabla
    __tablename__ = "acciones"

    # Se definen las columnas
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger)
    habito = Column(String)
    fecha_realizacion = Column(DateTime)
    texto = Column(String, nullable=True)
    cantidad = Column(Float, nullable=True)

    # Se establecen las claves foraneas
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'habito'], ['habitos.user_id', 'habitos.habito']),
    )

    # Se establece la relacion con la clase Habito
    habito_relacion = relationship("Habito", back_populates="acciones")


# Se crea el motor de la base de datos
engine = create_engine(DATABASE_URL, future=True)

# Se configura la sesion de la base de datos
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """
    Proporciona una sesion de base de datos
    """

    # Se crea la sesion local
    db = SessionLocal()
    try:
        # Se produce la sesion
        yield db
    finally:
        # Se cierra la sesion
        db.close()

def main_crear_BBDD():
    """
    Funcion principal que crea la base de datos y las tablas
    """

    # Se informa que se estan creando o verificando las tablas
    print("Creando/verificando tablas en la base de datos...")
    # Se ejecuta la creacion de las tablas definidas en los modelos
    Base.metadata.create_all(bind=engine)
    # Se notifica que ha finalizado el proceso
    print("Proceso completado. Las tablas estan listas.")
