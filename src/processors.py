from datetime import datetime
import pandas as pd

from src.session_utils import get_session_id

# Funcion para calcular edad desde la fecha de nacimiento
def calculate_age(born_date):
    """Calcula la edad a partir de un objeto datetime o string"""
    try:
        if pd.isna(born_date):
            return "N/A"
        if isinstance(born_date, (pd.Timestamp, datetime)):
            born = born_date
        else:
            born = pd.to_datetime(born_date, dayfirst=True)   
        today = datetime.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except:
        return "N/A"


# Funcion para procesar los datos de asistencia
def process_attendance(df):
    """Limpia y prepara los datos de asistencia"""
    # Columna Fecha a datetime
    df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    # Columna Asistencia a booleano
    df['Asistencia'] = df['Asistencia'].astype(bool)
    # Crear un ID de sesión único (Fecha + Turno)
    df['id_sesion'] = get_session_id(df)
    
    return df


# Funcion para calcular los KPIs de asistencia por sesiones
def get_attendance_metrics(df):
    """Calcula KPIs por sesiones"""
    total_sesiones = df['id_sesion'].nunique()
    asistencia_por_sesion = df.groupby('id_sesion')['Asistencia'].mean()
    porcentaje_total = asistencia_por_sesion.mean() * 100 if not asistencia_por_sesion.empty else 0 
    return {
        "pct_asistencia": porcentaje_total,
        "total_sesiones": total_sesiones
    }


# Funcion para generar el conteo de Presentes/Ausentes por sesión
def get_session_summary(df):
    """Genera el conteo de Presentes/Ausentes por sesión para gráficos del equipo"""
    summary = df.groupby(['Fecha', 'Turno sesion', 'Tipo sesion']).agg(
        Presentes=('Asistencia', 'sum'),
        Ausentes=('Asistencia', lambda x: (~x).sum())
    ).reset_index()
    return summary


# Funcion para normalizar los RUTs
def _clean_rut_series(series: pd.Series) -> pd.Series:
    """
    Normaliza RUTs eliminando cualquier caracter no numérico.
    Ejemplos:
    '18.580.993-5' -> '185809935'
    '18580993-5'   -> '185809935'
    '185809935'    -> '185809935'
    """
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\D", "", regex=True)
    )


# Funcion para procesar los datos de bienestar (pre_entrenamiento)
def process_pre_entrenamiento(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y prepara los datos de bienestar (pre_entrenamiento).
    - Convierte Marca temporal a Fecha.
    - Normaliza RUT.
    - Renombra columnas a nombres cortos.
    - Calcula wellness_score como suma de las 5 escalas 1-5.
    """
    df = df.copy()
    # 1) Marca temporal -> Fecha (suponiendo formato día/mes/año en Google Forms)
    df["Fecha"] = pd.to_datetime(df["Marca temporal"], dayfirst=True).dt.date
    # 2) Normalizar RUT
    df["Rut"] = _clean_rut_series(df["Rut (sin guion ni puntos)"])
    # 3) Renombrar columnas de interés
    df = df.rename(
        columns={
            "Nivel de fatiga": "fatiga",
            "Nivel de dolor muscular": "dolor_muscular",
            "Calidad de sueño": "calidad_sueno",
            "Nivel de estrés": "estres",
            "Humor": "humor",
            "Horas de sueño": "horas_sueno",
            'En caso de tener dolor muscular, indicar: "Sobrecarga (indicar zona muscular)" ': "sobrecarga_texto",
        }
    )
    # 4) Asegurar que las escalas numéricas son numéricas
    escala_cols = ["fatiga", "dolor_muscular", "calidad_sueno", "estres", "humor"]
    for col in escala_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["horas_sueno"] = pd.to_numeric(df["horas_sueno"], errors="coerce")
    # 5) Calcular wellness_score como suma de las 5 escalas
    df["wellness_score"] = df[escala_cols].sum(axis=1)
    # Devolvemos solo las columnas limpias más útiles (puedes ajustar)
    columnas_salida = [
        "Fecha",
        "Rut",
        "fatiga",
        "dolor_muscular",
        "calidad_sueno",
        "estres",
        "humor",
        "horas_sueno",
        "wellness_score",
        "sobrecarga_texto",
    ]
    return df[columnas_salida]


# Funcion para procesar los datos de carga de entrenamiento (post_entrenamiento)
def process_post_entrenamiento(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y prepara los datos de RPE (post_entrenamiento).
    - Convierte Marca temporal a Fecha.
    - Normaliza RUT.
    - Renombra columnas (Jornada, Tipo de sesión, RPE, Duracion_min).
    - Crea id_sesion usando get_session_id (Fecha + Tipo + Turno).
    - Calcula CargaSesion = RPE * Duracion_min.
    """

    df = df.copy()

    df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()

    # 1) Marca temporal -> Fecha (solo fecha)
    df["Fecha"] = pd.to_datetime(df["Marca temporal"], dayfirst=True).dt.date

    # 2) Normalizar RUT
    df["Rut"] = _clean_rut_series(df["Rut (sin guion ni puntos)"])

    # 3) Renombrar columnas clave
    df = df.rename(
        columns={
            "Jornada": "Turno sesion",
            "Tipo de sesión": "Tipo sesion",
            "Percepción de esfuerzo de sesión de entrenamiento": "RPE",
            "Duración de sesión (minutos) * Aproximado: 60 - 90 - 120, etc": "Duracion_min",
        }
    )

    # 4) Asegurar numéricos
    df["RPE"] = pd.to_numeric(df["RPE"], errors="coerce")
    df["Duracion_min"] = pd.to_numeric(df["Duracion_min"], errors="coerce")

    # 5) Crear id_sesion coherente con asistencia (usa Fecha, Tipo sesion, Turno sesion)
    #   get_session_id internamente convierte Fecha a datetime, así que usamos la columna "Fecha"
    df["id_sesion"] = get_session_id(df)

    # 6) Calcular carga de la sesión (sRPE): RPE * Duracion_min
    df["CargaSesion"] = df["RPE"] * df["Duracion_min"]

    # Devolver columnas limpias más útiles
    columnas_salida = [
        "Fecha",
        "Rut",
        "Tipo sesion",
        "Turno sesion",
        "RPE",
        "Duracion_min",
        "CargaSesion",
        "id_sesion",
    ]

    return df[columnas_salida]