import pandas as pd

# Orden fijo de las combinaciones Tipo/Turno dentro de un día
# Siempre: Fisico AM -> Cancha AM -> Cancha PM
SESSION_ORDER = {
    "Fisico AM": 0,
    "Cancha AM": 1,
    "Cancha PM": 2,
}

def compute_session_order(df: pd.DataFrame) -> pd.Series:
    """
    Devuelve una Serie con el orden de sesión dentro del día,
    según la combinación (Tipo sesion, Turno sesion).
    Si no matchea, queda al final (99).
    """
    key = df["Tipo sesion"].fillna("") + " " + df["Turno sesion"].fillna("")
    return key.map(SESSION_ORDER).fillna(99).astype(int)


def get_session_id(df: pd.DataFrame) -> pd.Series:
    """
    Devuelve la Serie de id_sesion (Fecha + Tipo + Turno).
    El DataFrame debe tener columnas: Fecha, Tipo sesion, Turno sesion.
    Reutilizable en asistencia, cargas (RPE), etc.
    """
    return (
        pd.to_datetime(df["Fecha"]).dt.strftime("%Y-%m-%d") + " | " +
        df["Tipo sesion"].fillna("").astype(str) + " " +
        df["Turno sesion"].fillna("").astype(str)
    )