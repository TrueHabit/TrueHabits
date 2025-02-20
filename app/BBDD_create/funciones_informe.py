import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from BBDD_create.database import Usuario, Habito, Accion
from BBDD_create.database import SessionLocal

# ------------------------------------------------------------------------
# 1. Funciones de acceso a la BBDD
# ------------------------------------------------------------------------

def get_user_name(db: Session, user_id: int) -> str:
    """
    Retorna el nombre del usuario (columna 'nombre' en la tabla Usuario).
    Si no existe o es None, retorna cadena vacía.
    """
    nombre = db.query(Usuario.nombre).filter(Usuario.user_id == user_id).scalar()
    return nombre if nombre else ""


def get_user_habits(db: Session, user_id: int):
    """
    Retorna todos los hábitos (tabla 'Habito') asociados al user_id,
    sin filtrar por fecha ni por acciones.
    """
    return (
        db.query(Habito)
        .filter(Habito.user_id == user_id)
        .all()
    )


def get_all_data(db: Session, user_id: int):
    """
    Retorna todas las acciones (sin filtrar por semana) de un usuario.
    Query:
        - JOIN entre Habito y Accion 
        - Agrupa por fecha (func.date()), sum de cantidades,
          etc. (no hay filtros de fecha).
    """
    data = (
        db.query(
            Habito.user_id.label("user_id"), 
            Habito.habito,
            Habito.categoria,
            Habito.frecuencia_objetivo,
            func.date(Accion.fecha_realizacion).label("fecha_realizacion"),
            func.sum(Accion.cantidad).label("total_acciones"),
            Habito.cantidad_objetivo.label("cantidad_objetivo"),
            func.avg(Accion.cantidad).label("media"),
            case(
                [(Habito.categoria == "dejar", func.min(Accion.cantidad))],
                else_=None
            ).label("reducir"),
        )
        .join(
            Accion, 
            (Habito.user_id == Accion.user_id) & 
            (Habito.habito == Accion.habito)
        )
        .filter(Habito.user_id == user_id)
        .group_by(
            Habito.user_id,
            Habito.habito,
            Habito.categoria,
            Habito.frecuencia_objetivo,
            func.date(Accion.fecha_realizacion),
            Habito.cantidad_objetivo
        )
        .all()
    )
    return data


def get_filtered_data(db: Session, user_id: int):
    """
    Retorna datos de un usuario pero filtrando SOLO la semana actual (lunes->domingo).
    Emplea outerjoin para no perder hábitos sin acciones en esa semana.
    """
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)
    
    data = (
        db.query(
            Habito.user_id.label("user_id"), 
            Habito.habito,
            Habito.categoria,
            Habito.frecuencia_objetivo,
            func.date(Accion.fecha_realizacion).label("fecha_realizacion"),
            func.sum(Accion.cantidad).label("total_acciones"),
            Habito.cantidad_objetivo.label("cantidad_objetivo"),
            func.avg(Accion.cantidad).label("media"),
            case(
                [(Habito.categoria == "dejar", func.min(Accion.cantidad))],
                else_=None
            ).label("reducir"),
        )
        .outerjoin(
            Accion, 
            (Habito.user_id == Accion.user_id) & 
            (Habito.habito == Accion.habito) &
            (Accion.fecha_realizacion >= start_of_week) &
            (Accion.fecha_realizacion <= end_of_week)
        )
        .filter(Habito.user_id == user_id)
        .group_by(
            Habito.user_id,
            Habito.habito,
            Habito.categoria,
            Habito.frecuencia_objetivo,
            func.date(Accion.fecha_realizacion),
            Habito.cantidad_objetivo
        )
        .all()
    )
    return data


def get_all_users_truefriends_data(db: Session):
    """
    Retorna datos filtrados por categorías 'deporte' o 'estilo-vida' (para comparar con otros usuarios).
    Filtro de la semana actual (lunes->domingo).
    """
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)
    
    data = (
        db.query(
            Habito.user_id.label("user_id"), 
            Habito.habito,
            Habito.categoria,
            Habito.frecuencia_objetivo,
            func.date(Accion.fecha_realizacion).label("fecha_realizacion"),
            func.sum(Accion.cantidad).label("total_acciones"),
            Habito.cantidad_objetivo.label("cantidad_objetivo"),
            func.avg(Accion.cantidad).label("media"),
            case(
                [(Habito.categoria == "dejar", func.min(Accion.cantidad))],
                else_=None
            ).label("reducir"),
        )
        .outerjoin(
            Accion, 
            (Habito.user_id == Accion.user_id) & 
            (Habito.habito == Accion.habito) &
            (Accion.fecha_realizacion >= start_of_week) &
            (Accion.fecha_realizacion <= end_of_week)
        )
        .filter((Habito.categoria == "deporte") | (Habito.categoria == "estilo-vida"))
        .group_by(
            Habito.user_id,
            Habito.habito,
            Habito.categoria,
            Habito.frecuencia_objetivo,
            func.date(Accion.fecha_realizacion),
            Habito.cantidad_objetivo
        )
        .all()
    )
    return data


# ------------------------------------------------------------------------
# 2. Funciones de cálculo de puntos y conversión a DataFrame
# ------------------------------------------------------------------------

def calculate_points(row) -> float:
    """
    Calcula cuántos puntos obtiene el usuario según:
      - categoría (si es 'dejar', debe no superar cierto límite),
      - frecuencia (diaria/semanal -> distinto 'points_max'),
      - total_acciones vs cantidad_objetivo.
    """
    cat = row['categoria']
    freq = row['frecuencia_objetivo']
    total = row['total_acciones']
    cantidad_objetivo = row['cantidad_objetivo']

    # Determinar el puntaje máximo según la frecuencia
    points_max = 50 if freq == "semanal" else 10
    
    if cat == "dejar":
        # Debe no superar la cantidad_objetivo
        return points_max if total <= cantidad_objetivo else 0.0
    else:
        # Hábito normal (ej: correr, caminar...)
        if total >= cantidad_objetivo:
            return float(points_max)
        else:
            ratio = float(total / cantidad_objetivo) if cantidad_objetivo != 0 else 0
            return min(ratio * points_max, points_max)


def calculate_points_max(row) -> float:
    """
    Calcula la puntuación máxima en función de la frecuencia:
      - semanal: 50
      - diaria: 10
    """
    return 50.0 if row['frecuencia_objetivo'] == "semanal" else 10.0

 
def accumulate_weekly_points(df_weekly: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada hábito semanal (frecuencia_objetivo == "semanal") en df_weekly,
    se genera un registro diario (de lunes a domingo) y se calcula la cantidad de puntos
    ganados ese día usando:
        puntos = min((total_acciones / cantidad_objetivo) * 50, 50)
    Retorna un DataFrame con columnas: id, habito, fecha_realizacion, total_acciones, puntos_diarios.
    """
    df_weekly["fecha_dt"] = pd.to_datetime(df_weekly["fecha_realizacion"], errors="coerce")
    results = []
    for (uid, hab), group in df_weekly.groupby(["id", "habito"]):
        group = group.sort_values("fecha_dt")
        # Determinar el lunes de la semana usando el primer registro
        first_date = group["fecha_dt"].min()
        monday = first_date - pd.Timedelta(days=first_date.weekday())
        sunday = monday + pd.Timedelta(days=6)
        # Crear el rango completo de fechas de lunes a domingo
        full_dates = pd.date_range(start=monday, end=sunday, freq="D")
        # Reindexar para incluir todos los días de la semana, rellenando con 0 los días sin registro
        group = group.set_index("fecha_dt").reindex(full_dates, fill_value=0)
        group = group.rename_axis("fecha_dt").reset_index()
        group["id"] = uid
        group["habito"] = hab
        # Se asume que 'cantidad_objetivo' es constante para este hábito
        cantidad_objetivo = df_weekly.loc[
            (df_weekly["id"] == uid) & (df_weekly["habito"] == hab), "cantidad_objetivo"
        ].iloc[0]
        group["total_acciones"] = group["total_acciones"].astype(float)
        # Calcular los puntos diarios (sin acumulación) para cada día
        group["puntos_diarios"] = group.apply(
            lambda row: min((row["total_acciones"] / cantidad_objetivo) * 50, 50)
            if cantidad_objetivo > 0 else 0,
            axis=1
        )
        group["fecha_realizacion"] = group["fecha_dt"].dt.strftime("%Y-%m-%d")
        results.append(group[["id", "habito", "fecha_realizacion", "total_acciones", "puntos_diarios"]])
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()


def convert_to_dataframe(data) -> pd.DataFrame:
    """
    Convierte los datos obtenidos de la base de datos (lista de tuplas)
    a un DataFrame de pandas. Aplica el cálculo de puntos y puntos máximos.
    Para hábitos SEMANALES, en lugar de generar una sola fila semanal,
    se calcula el acumulado diario (de lunes a domingo) para poder graficar el progreso.
    """
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)
    
    try:
        # -----------------------
        # 1) Construir un DF base
        # -----------------------
        rows = []
        for row in data:
            # row = (user_id, habito, categoria, frecuencia_objetivo, fecha_realizacion, total_acciones,
            #        cantidad_objetivo, media, reducir)
            user_id        = row[0]
            habito         = row[1] if row[1] else ""
            categoria      = row[2] if row[2] else ""
            freq_obj       = row[3] if row[3] else ""
            fecha_real     = row[4]  # puede ser None
            total_acciones = row[5] if row[5] is not None else 0.0
            cant_objetivo  = row[6] if row[6] is not None else 0.0
            media          = row[7] if row[7] is not None else 0.0
            reducir        = row[8] if row[8] is not None else 0.0

            # Si no hay fecha, usar el inicio de semana
            if fecha_real is None:
                fecha_str = start_of_week.strftime('%Y-%m-%d')
            else:
                fecha_str = fecha_real.strftime('%Y-%m-%d')

            rows.append({
                "id": str(user_id) if user_id else None,
                "habito": habito.lower(),
                "categoria": categoria.lower(),
                "frecuencia_objetivo": freq_obj.lower(),
                "fecha_realizacion": fecha_str,
                "total_acciones": float(total_acciones),
                "cantidad_objetivo": float(cant_objetivo),
                "media": float(media),
                "reducir": float(reducir)
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # --------------------------------------------------------------------
        # 2) Para hábitos 'dejar' diarios: rellenar días faltantes (se mantiene la lógica original)
        # --------------------------------------------------------------------
        daily_dejar = df[(df["categoria"] == "dejar") & (df["frecuencia_objetivo"] == "diaria")].copy()
        if not daily_dejar.empty:
            unique_daily_dejar = daily_dejar[["id", "habito", "categoria", "frecuencia_objetivo", "cantidad_objetivo", "reducir"]].drop_duplicates()
            start_of_week_plus_one = start_of_week + timedelta(days=1)
            date_range = pd.date_range(start=start_of_week_plus_one, end=end_of_week)
            all_new_rows = []
            for _, habit_row in unique_daily_dejar.iterrows():
                uid     = habit_row["id"]
                hab     = habit_row["habito"]
                cat     = habit_row["categoria"]
                freq    = habit_row["frecuencia_objetivo"]
                cantobj = habit_row["cantidad_objetivo"]
                red     = habit_row["reducir"]
                for single_date in date_range:
                    date_str = single_date.strftime("%Y-%m-%d")
                    mask = ((df["id"] == uid) & (df["habito"] == hab) & (df["fecha_realizacion"] == date_str))
                    if not mask.any():
                        all_new_rows.append({
                            "id": uid,
                            "habito": hab,
                            "categoria": cat,
                            "frecuencia_objetivo": freq,
                            "fecha_realizacion": date_str,
                            "total_acciones": 0.0,
                            "cantidad_objetivo": cantobj,
                            "media": 0.0,
                            "reducir": red
                        })
            if all_new_rows:
                df = pd.concat([df, pd.DataFrame(all_new_rows)], ignore_index=True)

        # --------------------------------------------------------------------
        # 3) Agrupar por día (para evitar duplicados de la misma fecha-hábito)
        # --------------------------------------------------------------------
        df = df.groupby(
            ["id", "habito", "categoria", "frecuencia_objetivo", "fecha_realizacion", "cantidad_objetivo"],
            dropna=False,
            as_index=False
        ).agg({
            "total_acciones": "sum",
            "media": "mean",
            "reducir": "min"
        })

        # --------------------------------------------------------------------
        # 4) Separar hábitos diarios y semanales
        # --------------------------------------------------------------------
        df_daily = df[df["frecuencia_objetivo"] == "diaria"].copy()
        df_weekly = df[df["frecuencia_objetivo"] == "semanal"].copy()

        # Para los diarios, calcular puntos con la fórmula ya definida
        if not df_daily.empty:
            df_daily["puntos"] = df_daily.apply(calculate_points, axis=1).round(1)
            df_daily["puntos_obj"] = df_daily.apply(calculate_points_max, axis=1)
        else:
            df_daily = pd.DataFrame()

        # Para los semanales, usar la función accumulate_weekly_points para obtener acumulados diarios
        if not df_weekly.empty:
            df_weekly_accum = accumulate_weekly_points(df_weekly)
            # Renombrar la columna 'puntos_acumulados' a 'puntos'
            df_weekly_accum["puntos"] = df_weekly_accum["puntos_diarios"]
            # Asignar el puntaje máximo teórico de 50 para hábitos semanales
            df_weekly_accum["puntos_obj"] = 50.0
            # Agregar la columna 'frecuencia_objetivo' como "semanal"
            df_weekly_accum["frecuencia_objetivo"] = "semanal"
            # Para completar la información, agregar la columna 'categoria' desde el df original
            weekly_info = df_weekly.drop_duplicates(subset=["id", "habito"])[["id", "habito", "categoria", "cantidad_objetivo"]]
            df_weekly_accum = df_weekly_accum.merge(weekly_info, on=["id", "habito"], how="left")
        else:
            df_weekly_accum = pd.DataFrame()

        # --------------------------------------------------------------------
        # 5) Combinar los DataFrames diarios y semanales
        # --------------------------------------------------------------------
        df_final = pd.concat([df_daily, df_weekly_accum], ignore_index=True)
        df_final.sort_values(by=["id", "habito", "fecha_realizacion"], inplace=True, ignore_index=True)
        return df_final

    except Exception as e:
        print(f"Error en convert_to_dataframe: {e}")
        return pd.DataFrame()



# ------------------------------------------------------------------------
# 3. Funciones para obtener puntos acumulados (histórico / semanal)
# ------------------------------------------------------------------------

def get_points_accumulated_all_time(user_id: int) -> float:
    """
    Calcula la suma de PUNTOS TOTALES de TODO el historial (sin filtrar por semana).
    Redondea a 1 decimal.
    """
    with SessionLocal() as db:
        data = get_all_data(db, user_id)
        df = convert_to_dataframe(data)
        if df.empty:
            return 0.0
        # Convertir a datetime la fecha de realización
        df["fecha_dt"] = pd.to_datetime(df["fecha_realizacion"], errors="coerce")
        # Calcular el inicio de la semana (lunes) para cada registro
        df["week_start"] = df["fecha_dt"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
        
        # Agrupar por semana y sumar los puntos de cada una
        weekly_history = (
            df.groupby("week_start", as_index=False)["puntos"]
              .sum()
              .rename(columns={"puntos": "puntos_totales"})
              .sort_values("week_start")
              .reset_index(drop=True)
        )
        return round(weekly_history["puntos_totales"].sum(), 1)


def get_points_accumulated_weekly(user_id: int) -> float:
    """
    Calcula los puntos acumulados (suma) para la SEMANA ACTUAL, sin redondear (o redondear si se desea).
    """
    with SessionLocal() as db:
        data = get_filtered_data(db, user_id)  
        df = convert_to_dataframe(data)
        if df.empty:
            return 0.0
        # Separar los registros diarios y semanales
        df_daily = df[df["frecuencia_objetivo"] == "diaria"]
        df_weekly = df[df["frecuencia_objetivo"] == "semanal"]

        # Para los diarios se suman todos los puntos
        daily_sum = df_daily["puntos"].sum()

        # Para los semanales se agrupa por hábito (por ejemplo, por 'id' y 'habito') y se toma el valor máximo de puntos (el acumulado final)
        if not df_weekly.empty:
            weekly_max_df = df_weekly.groupby(["id", "habito"], as_index=False)["puntos"].max()
            weekly_sum = weekly_max_df["puntos"].sum()
        else:
            weekly_sum = 0

        # Total global: suma de los diarios y la contribución única de cada hábito semanal
        puntos_totales = daily_sum + weekly_sum
        return puntos_totales



# ------------------------------------------------------------------------
# 4. Función principal de generación de dashboard
# ------------------------------------------------------------------------
             
def generate_dashboard_2(db: Session, user_id: int, output_path: str = "informe.png"):
    """
    Genera un informe semanal (PNG) con gráficas y estadísticas para el usuario user_id.
    - Si no hay datos relevantes, retorna None.
    - Usa Plotly para crear subplots con:
        1) Gauge de puntos,
        2) Barras de puntos por categoría,
        3) Tabla de puntos de hoy,
        4) Barras/días cumplidos, etc.
    - Añade gráficas para 'caminar', 'deporte', 'estilo-vida', y un pie chart de 'dejar' si corresponde.
    Retorna la ruta de la imagen generada o None si falla la exportación.
    """
    data = get_filtered_data(db, user_id)
    df = convert_to_dataframe(data)
    if df.empty or not (df['total_acciones'] > 0).any():
        return None
    
    # ====================== Cálculo de métricas ====================== #
    user_habits = get_user_habits(db, user_id)
    habitos_diarios = [h for h in user_habits if (h.frecuencia_objetivo or "").lower() == "diaria"]
    habitos_semanales = [h for h in user_habits if (h.frecuencia_objetivo or "").lower() == "semanal"]
    
    puntos_objetivo_totales = len(habitos_diarios)*7*10 + len(habitos_semanales)*50
    puntos_totales = df['puntos'].sum()

    # Días cumplidos (solo para diarios)
    df_cumplidos = df[df['puntos'] >= df['puntos_obj']]
    df_cumplidos_dias = df_cumplidos[df_cumplidos['frecuencia_objetivo'] == 'diaria']

    dias_caminar = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'caminar']['fecha_realizacion'].nunique()
    dias_deporte = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'deporte']['fecha_realizacion'].nunique()
    dias_estilo = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'estilo-vida']['fecha_realizacion'].nunique()
    dias_alimentacion = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'alimentacion']['fecha_realizacion'].nunique()
    dias_tiempo = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'tiempo']['fecha_realizacion'].nunique()
    
    # “Días sin mal hábito” (cat 'dejar') - con freq diaria
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)
    rango_fechas = pd.date_range(start=start_of_week, end=end_of_week, freq='D')

    df_mal_habito = df[
        (df['categoria'] == 'dejar') & 
        (df['frecuencia_objetivo'] == 'diaria') &
        (df['total_acciones'] > 0)
    ].copy()
    fechas_mal_habito_set = set(df_mal_habito['fecha_realizacion'].unique())
    dias_reducir = sum(1 for dia in rango_fechas if dia.strftime('%Y-%m-%d') not in fechas_mal_habito_set)
    
    
def generate_dashboard(db: Session, user_id: int, output_path: str = "informe.png"):   
    data = get_filtered_data(db, user_id)        
    df = convert_to_dataframe(data)
    if df.empty or not(df['total_acciones'] > 0).any():
        return None    
    
    # ====================== Cálculo de métricas adicionales ====================== #
    user_habits = get_user_habits(db, user_id)
    habitos_diarios = [h for h in user_habits if (h.frecuencia_objetivo or "").lower()=="diaria"]
    habitos_semanales = [h for h in user_habits if (h.frecuencia_objetivo or "").lower()=="semanal"]
    puntos_objetivo_totales = len(habitos_diarios)*7*10 + len(habitos_semanales)*50
    
    # Separar los registros diarios y semanales
    df_daily = df[df["frecuencia_objetivo"] == "diaria"]
    df_weekly = df[df["frecuencia_objetivo"] == "semanal"]

    # Para los diarios se suman todos los puntos
    daily_sum = df_daily["puntos"].sum()

    # Para los semanales se agrupa por hábito (por ejemplo, por 'id' y 'habito') y se toma el valor máximo de puntos (el acumulado final)
    if not df_weekly.empty:
        weekly_max_df = df_weekly.groupby(["id", "habito"], as_index=False)["puntos"].max()
        weekly_sum = weekly_max_df["puntos"].sum()
    else:
        weekly_sum = 0

    # Total global: suma de los diarios y la contribución única de cada hábito semanal
    puntos_totales = daily_sum + weekly_sum

    
    # Días cumplidos (sólo diarios)
    df_cumplidos = df[df['puntos'] >= df['puntos_obj']]
    df_cumplidos_dias = df_cumplidos[df_cumplidos['frecuencia_objetivo'] == 'diaria']

    dias_caminar = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'caminar']['fecha_realizacion'].nunique()
    dias_deporte = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'deporte']['fecha_realizacion'].nunique()
    dias_estilo = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'estilo-vida']['fecha_realizacion'].nunique()
    dias_alimentacion = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'alimentacion']['fecha_realizacion'].nunique()
    dias_tiempo = df_cumplidos_dias[df_cumplidos_dias['categoria'] == 'tiempo']['fecha_realizacion'].nunique()
    
    # “Días sin mal hábito” en la categoría 'dejar'
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)
    rango_fechas = pd.date_range(start=start_of_week, end=end_of_week, freq='D')

    df_mal_habito = df[
        (df['categoria'] == 'dejar') & 
        (df['frecuencia_objetivo'] == 'diaria') &
        (df['total_acciones'] > 0)
    ].copy()
    fechas_mal_habito = df_mal_habito['fecha_realizacion'].unique()
    fechas_mal_habito_set = set(fechas_mal_habito) 
    dias_reducir = 0
    for dia in rango_fechas:
        if dia.strftime('%Y-%m-%d') not in fechas_mal_habito_set:
            dias_reducir += 1
    
    
    # ================================== Creación del dashboard ================================== #
    mostrar_caminar = df[(df['habito'] == 'caminar') & (df['puntos'] > 0)].shape[0] > 0
    mostrar_deporte = df[(df['categoria'] == 'deporte') & (df['puntos'] > 0)].shape[0] > 0

    mostrar_estilo_vida = df[(df['categoria'] == 'estilo-vida') & (df['puntos'] > 0)].shape[0] > 0
    #mostrar_reducir = df[(df['categoria'] == 'dejar')].shape[0] > 0
    mostrar_reducir = any(habit.categoria.lower() == "dejar" for habit in habitos_diarios)
    
    # Definir specs y subplot_titles fijos para las 2 primeras filas
    specs = [
        [{"type": "domain"}, {"type": "xy"}],   # Fila 1: gauge + barras (puntos totales, puntos categoría)
        [{"type": "table"}, {"type": "xy"}],    # Fila 2: tabla hoy + racha días
    ]
    subplot_titles = [
        "<b>Puntos TrueHabits</b>",
        "<b>Puntos por tipo de hábito</b>",
        "<b>Puntos acumulados hoy</b>",
        "<b>Racha de días cumplidos</b>",
    ]

    # Variables toggle para la posición en caso de tener un solo elemento en una fila
    toggle_row3_single = False
    toggle_row4_single = False
    
    # Grupo para Caminar y Deporte (fila 3 por defecto)
    row3_items = []
    if mostrar_caminar:
        row3_items.append(("<b>Puntos acumulados - Caminar</b>", {"type": "xy"}))
    if mostrar_deporte:
        row3_items.append(("<b>Puntos acumulados - Deporte</b>", {"type": "xy"}))

    # Grupo para Estilo de Vida y Reducir (fila 4 por defecto)
    row4_items = []
    if mostrar_estilo_vida:
        row4_items.append(("<b>Puntos acumulados - Estilo de Vida</b>", {"type": "xy"}))
    if mostrar_reducir:
        row4_items.append(("<b>Hábitos a Eliminar</b>", {"type": "domain"}))

        
    # --- Regla especial ---
    # Si no hay 'caminar' pero sí 'deporte' y además se quiere mostrar 'estilo de vida',
    # se "sube" el elemento de estilo de vida a la fila 3.
    if (not mostrar_caminar) and mostrar_deporte and mostrar_estilo_vida:
        # Agregar 'Estilo de Vida' a row3_items (si aún no está)
        if not any(item[0] == "<b>Puntos acumulados - Estilo de Vida</b>" for item in row3_items):
            row3_items.append(("<b>Puntos acumulados - Estilo de Vida</b>", {"type": "xy"}))
        # Y eliminarlo de row4_items para evitar duplicados.
        row4_items = [item for item in row4_items if item[0] != "<b>Puntos acumulados - Estilo de Vida</b>"]


    # === Si no hay elementos en la fila 3, pero sí en la fila 4,
    # movemos los de la fila 4 a la fila 3.
    if not row3_items and row4_items:
        row3_items = row4_items
        row4_items = []  # Quedan vacíos, ya que se muestran en fila 3

    # === Construcción dinámica de la Fila 3 ===
    if row3_items:
        if len(row3_items) == 2:
            # Si hay dos elementos, se asignan a las columnas 1 y 2 respectivamente.
            specs.append([row3_items[0][1], row3_items[1][1]])
            subplot_titles.extend([row3_items[0][0], row3_items[1][0]])
        elif len(row3_items) == 1:
            # Si hay un solo elemento, se coloca en la columna que indique el toggle.
            if toggle_row3_single:
                specs.append([None, row3_items[0][1]])
            else:
                specs.append([row3_items[0][1], None])
            subplot_titles.append(row3_items[0][0])
            toggle_row3_single = not toggle_row3_single
    else:
        # En caso extremo (ningún elemento en row3_items)
        specs.append([None, None])
        subplot_titles.extend(["", ""])
    
    # === Construcción dinámica de la Fila 4 ===
    # Se agregan solamente si quedan elementos en row4_items.
    if row4_items:
        if len(row4_items) == 2:
            specs.append([row4_items[0][1], row4_items[1][1]])
            subplot_titles.extend([row4_items[0][0], row4_items[1][0]])
        elif len(row4_items) == 1:
            if toggle_row4_single:
                specs.append([None, row4_items[0][1]])
                subplot_titles.extend(["", row4_items[0][0]])
            else:
                specs.append([row4_items[0][1], None])
                subplot_titles.extend([row4_items[0][0], ""])
            toggle_row4_single = not toggle_row4_single
    
    
    # Determinar número de filas finales
    num_filas = len(specs)

    # Ajuste dinámico del espaciado vertical basado en la cantidad de filas
    if num_filas == 2:
        vertical_spacing = 0.25  # Si solo hay dos filas, mayor separación
        height = 600  # Hacer los gráficos más grandes
    elif num_filas == 3:
        vertical_spacing = 0.15
        height = 1100
    else:
        vertical_spacing = 0.1  # Si hay más de 3 filas, espaciado normal
        height = 1400

   
    # Crear la figura con subplots dinámicos
    fig = make_subplots(
        rows=len(specs), 
        cols=2,
        vertical_spacing=vertical_spacing,
        horizontal_spacing=0.2,
        specs=specs,
        subplot_titles=subplot_titles
    )
    
    
    # ================================ Figura 1.1: Puntos Totales ================================ #
    
    max_gauge = max(1, puntos_totales, puntos_objetivo_totales)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=puntos_totales,
            title={"text": ""},
            gauge={
                "axis": {
                    "range": [0, max_gauge],
                    "showticklabels": True,
                    "tickvals": [0, puntos_objetivo_totales], 
                    "ticktext": ["0", f"{puntos_objetivo_totales}"]
                },
                "bar": {"color": "#0F4738"},
                "steps": [
                    {"range": [0, puntos_totales], "color": "#0F4738"},
                    {"range": [puntos_totales, max_gauge], "color": "#dd9faf"}    
                ],
                "borderwidth": 0
            },
            domain={"x": [0.2, 0.8], "y": [0.2, 0.4]}
        ),
        row=1, col=1
    )
    
    
    # ========================= Figura 1.2: Suma de puntos por categoría ========================= #

    # Separar los registros de hábitos diarios y semanales
    df_daily = df[df["frecuencia_objetivo"] == "diaria"]
    df_weekly = df[df["frecuencia_objetivo"] == "semanal"]

    # Para los hábitos semanales: por cada (id, habito, categoria) se toma el valor máximo de 'puntos'
    if not df_weekly.empty:
        weekly_summary = df_weekly.groupby(["id", "habito", "categoria"], as_index=False)["puntos"].max()
    else:
        weekly_summary = pd.DataFrame()

    # Para los diarios se usan tal cual
    if not df_daily.empty:
        daily_summary = df_daily.copy()
    else:
        daily_summary = pd.DataFrame()

    # Combinar ambos resúmenes
    df_summary = pd.concat([daily_summary, weekly_summary], ignore_index=True)

    # Calcular la suma de puntos por categoría a partir del resumen combinado
    resumen_categoria = df_summary.groupby("categoria")["puntos"].sum().reset_index()
    resumen_categoria = resumen_categoria.sort_values(by="puntos", ascending=True)


    # Crear gama de colores basada en #0F4738
    colores_categoria = [
        "#0F4738",  # Color principal
        "#1E5F4B",  # Más claro
        "#2A6F5B",  # Más oscuro
        "#4A937C",  # Muy claro
        "#165446",  # Más profundo
        "#044021"   # Oscuro saturado
    ]

    # Si se requiere que aparezcan todas las categorías registradas, se puede crear un DataFrame
    categorias_usuario = df['categoria'].unique()
    df_categorias = pd.DataFrame({"categoria": categorias_usuario})

    # Opcional: se puede unir con df_categorias para asegurar que aparezcan todas las categorías, incluso si su suma es cero
    resumen_categoria = df_categorias.merge(resumen_categoria, on="categoria", how="left").fillna(0)
    resumen_categoria = resumen_categoria.sort_values(by="puntos", ascending=True)

    # Diccionario para renombrar etiquetas del eje Y
    etiquetas_personalizadas = {
        "alimentacion": "Alimentación",
        "caminar": "Caminar",
        "deporte": "Deporte",
        "estilo-vida": "Estilo de Vida",
        "tiempo": "Planificación <br>& Reflexión",
        "dejar": "Hábitos <br>a eliminar"
    }

    # Aplicar los nombres personalizados si existen en el diccionario
    resumen_categoria['categoria'] = resumen_categoria['categoria'].apply(
        lambda x: etiquetas_personalizadas.get(x.lower(), x.capitalize())
    )
    # Asignar colores según el número de categorías disponibles
    colores = colores_categoria[:len(resumen_categoria)]    
    
    # Agregar gráfico de barras horizontal
    fig.add_trace(
        go.Bar(
            x=resumen_categoria['puntos'],
            y=resumen_categoria['categoria'],
            orientation='h',
            marker=dict(color=colores),  # Usar la gama de colores personalizada
            text=resumen_categoria['puntos'],  # Agregar etiquetas de puntos
            textposition='outside',  # Ubicar las etiquetas fuera de las barras
            name="Puntos por Categoría",
            showlegend=False  # Ocultar de la leyenda global
        ),
        row=1, col=2
    )
    max_range = (resumen_categoria["puntos"].max() + 15) if (resumen_categoria["puntos"].max() + 15) > 50 else 50
    fig.update_xaxes(range=[0, max_range + 15])
        
    # Agregar línea fija en x=50
    fig.add_shape(
        type="line",
        x0=50, x1=50,  # Línea fija en x=50
        y0=-0.5, y1=len(resumen_categoria['categoria']) - 0.5,  # Extender línea en el rango de las categorías
        line=dict(color="lightcoral", dash="dash"),  # Línea roja discontinua
        xref="x", yref="y"  # Referencias al eje x e y del gráfico
    )
    
    # Agregar etiqueta "Canjear Puntos" a la línea roja
    fig.add_annotation(
        x=50,  # Posición x de la etiqueta (en la misma posición de la línea roja)
        y=len(resumen_categoria['categoria']) - 0.5,  # Ubicar en el extremo superior de la línea
        text=f"<span style='font-size:13px;'>Mínimo puntos premios</span>",
        showarrow=False,  # No mostrar una flecha
        font=dict(color="lightcoral", size=8),  # Estilo de fuente para la etiqueta
        align="center",  # Alinear el texto al centro
        xref="x1", yref="y1",  # Referencias al eje x e y del gráfico
        xanchor="center",  # Anclar a la izquierda de x
        yanchor="bottom"  # Anclar a la parte inferior de y
    )
            
    
    # ============================= Figura 2.1: Estadísticas de hoy ============================== #
    # 1) Obtener la fecha de hoy sin hora (formato YYYY-MM-DD)
    hoy = pd.Timestamp.now().normalize().strftime('%Y-%m-%d')

    # 2) Filtrar los datos del DataFrame solo para el día de hoy
    df_hoy = df[df['fecha_realizacion'] == hoy].copy()

    # 4) Recalcular los puntos en df_hoy (para las nuevas filas agregadas)
    df_hoy["puntos"] = df_hoy.apply(calculate_points, axis=1).round(1)
    df_hoy["puntos_obj"] = df_hoy.apply(calculate_points_max, axis=1)

    # 5) Agrupar por categoría y hábito y sumar los puntos obtenidos hoy
    if not df_hoy.empty:
        resumen_hoy_habitos_categoria = (
            df_hoy.groupby(['categoria', 'habito'])['puntos']
            .sum()
            .reset_index()
        )
    else:
        resumen_hoy_habitos_categoria = pd.DataFrame(columns=['categoria','habito','puntos'])

    # 6) Excluir hábitos con 0 puntos (si no deseas mostrarlos)
    resumen_hoy_habitos_categoria = resumen_hoy_habitos_categoria[
        resumen_hoy_habitos_categoria['puntos'] > 0
    ]
    resumen_hoy_habitos_categoria = resumen_hoy_habitos_categoria[
        resumen_hoy_habitos_categoria['categoria'].str.lower() != "dejar"
    ]

    # 7) Aplicar nombres personalizados de categoría
    resumen_hoy_habitos_categoria['categoria'] = resumen_hoy_habitos_categoria['categoria'].apply(
        lambda x: etiquetas_personalizadas.get(x.lower(), x.capitalize())
    )

    # 8) Formatear el nombre del hábito (mayúscula inicial)
    resumen_hoy_habitos_categoria['habito'] = resumen_hoy_habitos_categoria['habito'].str.capitalize()

    # 9) Ordenar los hábitos de mayor a menor según categoría (o puntos, etc.)
    resumen_hoy_habitos_categoria = resumen_hoy_habitos_categoria.sort_values(
        by='categoria', 
        ascending=False
    )

    # 10) Agregar la tabla a la figura
    fig.add_trace(
        go.Table(
            columnwidth=[60, 40, 20],
            header=dict(
                values=["<b>Categoría</b>", "<b>Hábito</b>", "<b>Puntos</b>"],
                fill_color="#0F4738",
                font=dict(color="white", family="Quicksand", size=14),
                align="center",
                height=24
            ),
            cells=dict(
                values=[
                    resumen_hoy_habitos_categoria['categoria'] if not resumen_hoy_habitos_categoria.empty else ["-"],
                    resumen_hoy_habitos_categoria['habito'] if not resumen_hoy_habitos_categoria.empty else ["-"],
                    resumen_hoy_habitos_categoria['puntos'] if not resumen_hoy_habitos_categoria.empty else ["0"]
                ],
                fill_color="#E5ECF6",
                align="left",
                font=dict(color="black", family="Quicksand", size=13),
                height=25
            )
        ),
        row=2, col=1  
    )
    
    
    # ============================= Figura 2.2: Estadísticas de días ============================= #
    map_categorias = {
        "alimentacion": dias_alimentacion,
        "deporte": dias_deporte,
        "caminar": dias_caminar,
        "estilo-vida": dias_estilo,
        "tiempo": dias_tiempo,
        "dejar": dias_reducir
    }
    etiquetas_personalizadas = {
        "alimentacion": "Alimentación",
        "caminar": "Caminar",
        "deporte": "Deporte",
        "estilo-vida": "Estilo de Vida",
        "tiempo": "Planificación & Reflexión",
        "dejar": "Hábitos a eliminar"
    }
    
    # Filtrar el DataFrame por frecuencia 'diaria'
    df_diaria = df[df['frecuencia_objetivo'] == 'diaria']

    # Construir la lista de datos usando el DataFrame filtrado
    data_plot = []
    for cat in df_diaria['categoria'].unique().tolist():
        if cat in map_categorias:  # Solo categorías válidas en el diccionario
            valor = map_categorias[cat]
            etiqueta = etiquetas_personalizadas.get(cat, cat)  # Toma etiqueta, si no existe usa la categoría
            data_plot.append((cat, etiqueta, valor))

            
    # 2. Ordenar la lista por la cantidad de días cumplidos (valor), en orden descendente
    data_plot_sorted = sorted(data_plot, key=lambda x: x[2], reverse=True)
    
    # 3. Volver a separar en listas individuales ya ordenadas
    categorias_plot_ordenadas        = [item[0] for item in data_plot_sorted]
    categorias_plot_etiquetadas_ord  = [item[1] for item in data_plot_sorted]
    valores_plot_ordenados           = [item[2] for item in data_plot_sorted]
    
    # Definir colores limitados a la cantidad de categorías resultantes
    colores_barras = ["#0F4738", "#1E5F4B", "#2A6F5B", "#4A937C", "#165446", "#044021"]
    colores_barras_filtrados = colores_barras[:len(categorias_plot_ordenadas)]
    
    # Crear la barra
    fig.add_trace(
        go.Bar(
            x = categorias_plot_etiquetadas_ord,
            y = valores_plot_ordenados,
            marker_color = colores_barras_filtrados,
            text = [str(v) for v in valores_plot_ordenados],
            textposition = 'auto',
            showlegend = False
        ),
        row=2, col=2
    )
    # Ajuste de ejes
    fig.update_xaxes(
        tickfont=dict(size=12),
        automargin=True,
        range=[-0.75, len(categorias_plot_etiquetadas_ord)],
        row=2, col=2
    )
    fig.update_yaxes(
        range=[0, max(valores_plot_ordenados) + 0.5],
        row=2, col=2
    )


    # ============================ Figura 3.1: Estadísticas de caminar ============================ #
    if mostrar_caminar:
        # Filtro por el hábito "caminar"
        df_caminar = df[df['categoria'] == 'caminar'].copy()
        df_caminar['fecha_realizacion'] = pd.to_datetime(df_caminar['fecha_realizacion'], errors='coerce')
        
        # Generar el rango completo de días de la semana
        dias_semana_es = ["L", "M", "X", "J", "V", "S", "D"]
        #dias_semana_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dias_completos = pd.DataFrame({'dia_semana': dias_semana_es})

        # Agregar columna con días de la semana en español
        df_caminar['dia_semana'] = df_caminar['fecha_realizacion'].dt.day_name()
        dias_semana_map = {
            "Monday": "L",
            "Tuesday": "M",
            "Wednesday": "X",
            "Thursday": "J",
            "Friday": "V",
            "Saturday": "S",
            "Sunday": "D"
        }
        df_caminar['dia_semana'] = df_caminar['dia_semana'].map(dias_semana_map)

        # Agrupar los puntos por día de la semana
        df_puntos = df_caminar.groupby('dia_semana')['puntos'].sum().reset_index()

        # Unir los días completos con los datos existentes
        df_completo = dias_completos.merge(df_puntos, on='dia_semana', how='left')

        # Rellenar los días sin datos con ceros
        df_completo['puntos'] = df_completo['puntos'].fillna(0)

        # Ejes X e Y
        x_values = df_completo['dia_semana']  # Días de la semana ordenados
        y_values = df_completo['puntos']     # Puntos (rellenados con 0 si falta algún día)

        # Calcular un promedio de puntos
        promedio_caminar = y_values.mean() if not y_values.empty else 0
        
        # Agregar la serie de puntos al gráfico
        fig.add_trace(
            go.Scatter(
                x=x_values,  # Eje X: días de la semana
                y=y_values,  # Eje Y: puntos obtenidos ese día
                mode='lines+markers',  # Línea + marcadores
                line_shape='spline',  # Líneas curvas (spline)
                line=dict(color="#0F4738"),  # Color de la línea
                name="Puntos Diarios - Caminar",
                showlegend=False
            ),
            row=3, col=1
        )

        # Configurar el eje Y
        fig.update_yaxes(
            title_text="Puntos",
            title_font=dict(size=14, family="Quicksand", color="black"),
            tickmode="array",  # Definir manualmente los ticks
            tickvals=[int(round(val / 5) * 5) for val in np.linspace(0, df_completo['puntos'].max() * 1.1, 5).tolist()],
            range = [-df_completo['puntos'].max() * 0.1, df_completo['puntos'].max() * 1.1],
            row=3, col=1
        )

        # Configurar el eje X para que siempre muestre los días en orden
        fig.update_xaxes(
            title_text="Días de la semana",
            tickvals=dias_semana_es,  # Mostrar todos los días de la semana
            title_font=dict(size=14, family="Quicksand", color="black"),
            showgrid=False,
            range=[-1,8.5],
            row=3, col=1
        )

        # Añadir una línea fija en el promedio de puntos
        fig.add_trace(
            go.Scatter(
                x=x_values,  # Usar las mismas etiquetas del eje X
                y=[promedio_caminar] * len(x_values),  
                mode='lines',
                line=dict(dash='dash', color='lightcoral'),
                name="Promedio",
                showlegend=True
            ),
            row=3, col=1
        )

        # Anotación en el último día para etiquetar la línea “recomendada”
        fig.add_annotation(
            x=5.2,  # Última etiqueta del eje X
            y=0.85,          #promedio_caminar,
            text=f"<span style='font-size:15px;'>  -- Promedio</span>", 
            showarrow=False,
            font=dict(color="lightcoral", size=8),
            align="left",
            xref="x3",  # Referencia al eje X en fila 3, columna 1
            yref="y3 domain",
            xanchor="left",
            yanchor="bottom",
        )


    # ============================ Figura 3.2: Estadísticas de deporte ============================ #
    if mostrar_deporte:
        # Filtro por el hábito "deporte"
        df_deporte = df[df['categoria'] == 'deporte'].copy()
        df_deporte['fecha_realizacion'] = pd.to_datetime(df_deporte['fecha_realizacion'], errors='coerce')

        # Generar el rango completo de días de la semana
        dias_semana_es = ["L", "M", "X", "J", "V", "S", "D"]
        dias_completos = pd.DataFrame({'dia_semana': dias_semana_es})

        # Agregar columna con días de la semana en español
        dias_semana_map = {
            "Monday": "L",
            "Tuesday": "M",
            "Wednesday": "X",
            "Thursday": "J",
            "Friday": "V",
            "Saturday": "S",
            "Sunday": "D"
        }
        df_deporte['dia_semana'] = df_deporte['fecha_realizacion'].dt.day_name().map(dias_semana_map)

        # Agrupar los puntos por día de la semana
        df_puntos = df_deporte.groupby('dia_semana')['puntos'].sum().reset_index()

        # Unir con los días completos para no perder días
        df_completo = dias_completos.merge(df_puntos, on='dia_semana', how='left')
        df_completo['puntos'] = df_completo['puntos'].fillna(0)

        # Definir valores eje X e Y 
        x_values = df_completo['dia_semana']  
        y_values = df_completo['puntos']     
        promedio_deporte = y_values.mean() if not y_values.empty else 0
        
        # TrueFriends
        deporte_tf = get_all_users_truefriends_data(db)
        deporte_tf_df = convert_to_dataframe(deporte_tf)
        deporte_tf_df = deporte_tf_df[deporte_tf_df['categoria'] == 'deporte'].copy()
        deporte_tf_df['fecha_realizacion'] = pd.to_datetime(deporte_tf_df['fecha_realizacion'], errors='coerce')
        deporte_tf_df = deporte_tf_df[deporte_tf_df['id'] != user_id]
        deporte_tf_df['dia_semana'] = deporte_tf_df['fecha_realizacion'].dt.day_name().map(dias_semana_map)
        df_puntos_tg = deporte_tf_df.groupby('dia_semana')['puntos'].sum().reset_index()
        df_completo_tf = dias_completos.merge(df_puntos_tg, on='dia_semana', how='left')
        df_completo_tf['puntos'] = df_completo_tf['puntos'].fillna(0)
        x_values_tf = df_completo_tf['dia_semana']
        y_values_tf = df_completo_tf['puntos']  
           
        
        # Seleccionar posición (col) del gráfico según mostrar_caminar 
        #     - Si mostrar_caminar = True  -> col = 2
        #     - Si mostrar_caminar = False -> col = 1
        row_idx, col_idx = 3, (2 if mostrar_caminar else 1)
        
        # Añadir traza de línea en el gráfico 
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers',
                line_shape='spline',
                line=dict(color="#0F4738"),
                name="Puntos Diarios - Deporte",
                showlegend=False
            ),
            row=row_idx, col=col_idx
        )
        
        # Configurar el eje Y
        fig.update_yaxes(
            title_text="Puntos",
            title_font=dict(size=14, family="Quicksand", color="black"),
            tickmode="array",  # Definir manualmente los ticks
            tickvals=[int(round(val / 5) * 5) for val in np.linspace(0, df_completo_tf['puntos'].max() * 1.1, 5).tolist()],
            range = [-df_completo_tf['puntos'].max() * 0.1, df_completo_tf['puntos'].max() * 1.1],
            row=row_idx, col=col_idx
        )
        
        fig.update_xaxes(
            title_text="Días de la semana",
            tickvals=dias_semana_es,
            title_font=dict(size=14, family="Quicksand", color="black"),
            showgrid=False,
            range=[-1, 8.5],
            row=row_idx, col=col_idx
        )
        
        # Añadir una línea fija en el promedio de puntos
        fig.add_trace(
            go.Scatter(
                x=x_values,  # Usar las mismas etiquetas del eje X
                y=[promedio_deporte] * len(x_values),  
                mode='lines',
                line=dict(dash='dash', color='lightcoral'),
                name="Promedio",
                showlegend=True
            ),
            row=row_idx, col=col_idx
        )
        # Determinar las referencias de eje para la anotación según la posición 
        # fila 3: col 1 -> ("x5"/"y5"), col 2 -> ("x6"/"y6")
        xref_val = f"x4" if col_idx == 2 else f"x3" 
            
        # Anotación en el último día para etiquetar la línea “recomendada”
        fig.add_annotation(
            x=5.2, #x=x_values_tf.iloc[-2],  # Última etiqueta del eje X
            y=0.85,  #y_values_tf.max(),
            text=f"<span style='font-size:14px;'>  -- Promedio   </span>",  
            showarrow=False,
            font=dict(color="lightcoral", size=8),
            align="left",
            xref=xref_val, 
            yref="y3 domain",
            xanchor="left",
            yanchor="bottom",
        )
        
        # Añadir media de trueFriends
        fig.add_trace(
            go.Scatter(
                x=x_values_tf,  # Usar las mismas etiquetas del eje X
                y=y_values_tf,  
                mode='lines',
                line_shape='spline',
                line=dict(dash='dash', color='#31D3A9'),
                name="TrueFriends",
                showlegend=True
            ),
            row=row_idx, col=col_idx
        )
               
        
        # Anotación en el último día para etiquetar la línea “recomendada”
        fig.add_annotation(
            x=5.2,  # Última etiqueta del eje X
            y=0.75,    #y_values_tf.iloc[-1],      y_values_tf.max() + 10
            text=f"<span style='font-size:14px;'>  -- TrueFriends</span>",  
            showarrow=False,
            font=dict(color="#31D3A9", size=8),
            align="left",
            xref=xref_val, 
            yref="y3 domain",
            xanchor="left",
            yanchor="bottom",
        )
        
        
    # ============================ Figura 4.1: Estadísticas de estilo-vida ============================ #
    if mostrar_estilo_vida:
        # Filtro por el hábito "deporte"
        df_estilo_vida = df[df['categoria'] == 'estilo-vida'].copy()
        df_estilo_vida['fecha_realizacion'] = pd.to_datetime(df_estilo_vida['fecha_realizacion'], errors='coerce')

        # Generar el rango completo de días de la semana
        dias_semana_es = ["L", "M", "X", "J", "V", "S", "D"]
        dias_completos = pd.DataFrame({'dia_semana': dias_semana_es})

        # Agregar columna con días de la semana en español
        dias_semana_map = {
            "Monday": "L",
            "Tuesday": "M",
            "Wednesday": "X",
            "Thursday": "J",
            "Friday": "V",
            "Saturday": "S",
            "Sunday": "D"
        }
        df_estilo_vida['dia_semana'] = df_estilo_vida['fecha_realizacion'].dt.day_name().map(dias_semana_map)

        # Agrupar los puntos por día de la semana
        df_puntos = df_estilo_vida.groupby('dia_semana')['puntos'].sum().reset_index()

        # Unir con los días completos para no perder días
        df_completo = dias_completos.merge(df_puntos, on='dia_semana', how='left')
        df_completo['puntos'] = df_completo['puntos'].fillna(0)

        # Definir valores eje X e Y 
        x_values = df_completo['dia_semana']  
        y_values = df_completo['puntos']     
        promedio_estilo_vida = y_values.mean() if not y_values.empty else 0
        
        
        # Datos de TrueFriends (usuarios distintos al actual)
        estilo_vida_tf = get_all_users_truefriends_data(db)
        estilo_vida_tf_df = convert_to_dataframe(estilo_vida_tf)
        estilo_vida_tf_df = estilo_vida_tf_df[estilo_vida_tf_df['categoria'] == 'estilo-vida'].copy()
        estilo_vida_tf_df['fecha_realizacion'] = pd.to_datetime(estilo_vida_tf_df['fecha_realizacion'], errors='coerce')
        # Asegúrate de que la columna con el ID del usuario se llame 'id' o cámbiala a 'user_id' si es necesario
        estilo_vida_tf_df = estilo_vida_tf_df[estilo_vida_tf_df['id'] != user_id]
        estilo_vida_tf_df['dia_semana'] = estilo_vida_tf_df['fecha_realizacion'].dt.day_name().map(dias_semana_map)
        estilo_vida_df_puntos_tg = estilo_vida_tf_df.groupby('dia_semana')['puntos'].sum().reset_index()
        estilo_vida_df_completo_tf = dias_completos.merge(estilo_vida_df_puntos_tg, on='dia_semana', how='left')
        estilo_vida_df_completo_tf['puntos'] = estilo_vida_df_completo_tf['puntos'].fillna(0)
        x_values_tf = estilo_vida_df_completo_tf['dia_semana']
        y_values_tf = estilo_vida_df_completo_tf['puntos'] 
        
        
        # Seleccionar posición (col) del gráfico según mostrar_caminar 
        #     - Si mostrar_caminar = True  -> col = 2
        #     - Si mostrar_caminar = False -> col = 1
        
        if mostrar_caminar and mostrar_deporte: 
            row_idx, col_idx = 4, 1 
            xref_val, yref_val = f"x5", f"y5 domain"
        elif mostrar_caminar or mostrar_deporte: 
            row_idx, col_idx = 3, 2 
            xref_val, yref_val = f"x4", f"y3 domain"
        else:
            row_idx, col_idx = 3, 1 
            xref_val, yref_val = f"x3", f"y3 domain"
            

        
        # Añadir traza de línea en el gráfico 
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers',
                line_shape='spline',
                line=dict(color="#0F4738"),
                name="Puntos Diarios - Estilo de Vida",
                showlegend=False
            ),
            row=row_idx, col=col_idx
        )
        # Configurar el eje Y
        fig.update_yaxes(
            title_text="Puntos",
            title_font=dict(size=14, family="Quicksand", color="black"),
            tickmode="array",  # Definir manualmente los ticks
            #tickvals=[round(val, 1) for val in np.linspace(0, estilo_vida_df_completo_tf['puntos'].max() * 1.1, 5).tolist()],
            tickvals=[int(round(val / 5) * 5) for val in np.linspace(0, estilo_vida_df_completo_tf['puntos'].max() * 1.1, 5).tolist()],
            range = [-estilo_vida_df_completo_tf['puntos'].max() * 0.1, estilo_vida_df_completo_tf['puntos'].max() * 1.1],
            row=row_idx, col=col_idx
        )
        
        fig.update_xaxes(
            title_text="Días de la semana",
            tickvals=dias_semana_es,
            title_font=dict(size=14, family="Quicksand", color="black"),
            showgrid=False,
            range=[-1, 8.5],
            row=row_idx, col=col_idx
        )
        
        # Añadir una línea fija en el promedio de puntos
        fig.add_trace(
            go.Scatter(
                x=x_values,  # Usar las mismas etiquetas del eje X
                y=[promedio_estilo_vida] * len(x_values),  
                mode='lines',
                line=dict(dash='dash', color='lightcoral'),
                name="Promedio",
                showlegend=True
            ),
            row=row_idx, col=col_idx
        )
                
        # Anotación en el último día para etiquetar la línea “recomendada”
        fig.add_annotation(
            x=5.2,  # Última etiqueta del eje X
            y=0.85,
            text=f"<span style='font-size:14px;'>  -- Promedio</span>",   
            showarrow=False,
            font=dict(color="lightcoral", size=8),
            align="left",
            xref=xref_val, 
            yref=yref_val,
            xanchor="left",
            yanchor="bottom",
        )
        
        # Añadir media de trueFriends
        fig.add_trace(
            go.Scatter(
                x=x_values_tf,  # Usar las mismas etiquetas del eje X
                y=y_values_tf,  
                mode='lines',
                line_shape='spline',
                line=dict(dash='dash', color='#31D3A9'),
                name="TrueFriends",
                showlegend=True
            ),
            row=row_idx, col=col_idx
        )
               
        
        # Anotación en el último día para etiquetar la línea “recomendada”
        fig.add_annotation(
            x=5.2,  # Última etiqueta del eje X
            y=0.75,
            text=f"<span style='font-size:14px;'>  -- TrueFriends</span>",  
            showarrow=False,
            font=dict(color="#31D3A9", size=8),
            align="left",
            xref=xref_val, 
            yref=yref_val,
            xanchor="left",
            yanchor="bottom",
        )
        
        
        
    
            
    # ============================ Figura 4.2: Reducir malos hábitos ============================ #
    if mostrar_reducir:
        # 1) Cálculo de días superados y no superados
        dias_reducir_superados = dias_reducir
        dias_reducir_no_superados = max(0, 7 - dias_reducir)  # Asegurar que no sea negativo

        # Selección de posición (row_idx, col_idx)
        if (mostrar_caminar and (mostrar_deporte or mostrar_estilo_vida)) or (not mostrar_caminar and mostrar_deporte and mostrar_estilo_vida):
            row_idx = 4
        else:
            row_idx = 3

        if mostrar_caminar:
            col_idx = 2 if (mostrar_deporte == mostrar_estilo_vida) else 1
        else:
            col_idx = 1 if (mostrar_deporte == mostrar_estilo_vida) else 2

        # 2) Agregar la traza Pie con leyenda bien posicionada
        fig.add_trace(
            go.Pie(
                labels=["Días Superados", "Días No Superados"],
                values=[dias_reducir_superados, dias_reducir_no_superados],
                marker=dict(colors=["#0F4738", "#dd9faf"]),  # Colores definidos correctamente
                name="Días Reducción",
                textinfo='label+percent',
                rotation=120,
                pull=[0, 0.1, 0],
                direction='clockwise',
                textposition='outside'
                #hole=0.4  # Hace un gráfico de donut en lugar de pie
            ),
            row=row_idx, col=col_idx
        )

        # Aumentar margen/título
        fig.update_layout(
            title=dict(
                text="Hábitos a Eliminar",
                x=0.5,
                y=0.93,  # Un poco más abajo
                xanchor="center",
                yanchor="top",
                font=dict(size=16)
            ),
            margin=dict(t=120)
        )

    """if mostrar_reducir:
        # 1) Cálculo de días superados y no superados
        dias_reducir_superados = dias_reducir
        dias_reducir_no_superados = 7 - dias_reducir
        #dias_reducir_superados = df[(df['categoria'] == 'dejar') & (df['puntos'] >= df['puntos_obj'])]['fecha_realizacion'].nunique()
        #dias_reducir_no_superados = df[(df['categoria'] == 'dejar') & (df['puntos'] < df['puntos_obj'])]['fecha_realizacion'].nunique()

        # Selección de (row_idx, col_idx) según las combinaciones
        if (mostrar_caminar and (mostrar_deporte or mostrar_estilo_vida)) or (not mostrar_caminar and mostrar_deporte and mostrar_estilo_vida):
            row_idx = 4
        else:
            row_idx = 3

        if mostrar_caminar:
            # Si "caminar" es True, se asigna col=2 cuando deporte y estilo son iguales, de lo contrario col=1
            col_idx = 2 if (mostrar_deporte == mostrar_estilo_vida) else 1
        else:
            # Si "caminar" es False, se asigna col=1 cuando deporte y estilo son iguales, de lo contrario col=2
            col_idx = 1 if (mostrar_deporte == mostrar_estilo_vida) else 2

        # 3) Agregar la traza Pie en la ubicación elegida
        fig.add_trace(
            go.Pie(
                labels=["Días Superados", "No"],
                values=[dias_reducir_superados, dias_reducir_no_superados],
                marker_colors=["#0F4738", "#dd9faf"],
                name="Reducir",
                textinfo='label+percent',
                textposition='outside'
            ),
            row=row_idx, col=col_idx
        )
    """
           
            
    
    # ============================ Configurar el diseño del dashboard ============================ #

    user_name = get_user_name(db, user_id)
    """if not row4_items:
        height = 1130
        if not row3_items:
            height = 1000
    else:
        height = 1500
    """
    fig.update_layout(
        title={
            #"text": f"<b>{user_name}, tu informe semanal de TrueHabits</b>",
            #"text": f"<b><span style='text-shadow: 2px 2px 4px gray;'>¡Lo estás logrando, {user_name}! <br> Así va tu semana en TrueHabits</span></b>",  
            "text": f"<b><span style='text-shadow: 2px 2px 4px gray;'><br> Tu informe semanal de TrueHabits</span></b>",        
            "x": 0.5,
            "y": 0.95,
            "xanchor": "center",
            "font": {
                "size": 46,
                "color": "#0F4738", 
                "family": "Quicksand"
            }
        },
        margin={"t": 250, "b": 80, "l": 80, "r": 80},
        font={
            "family": "Quicksand",  
            "size": 14,
            "color": "black"  
        },
        height=height,
        width=1000,
        legend={
            "yanchor": "bottom",
            "y": -0.3,
            "xanchor": "center",
            "x": 0.5
        },
        showlegend=False
    )

    # Tamaño de fuente de los ítulos de subgráficos
    fig.update_annotations(font_size=18)
    
    fig.show()
    
    try:
        fig.write_image(output_path, engine="kaleido")
        return output_path
    except Exception as e:
        return None