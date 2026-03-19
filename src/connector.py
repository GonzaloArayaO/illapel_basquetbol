import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def get_data(url: str, sheet_name: str, ttl: str = "10m") -> pd.DataFrame:
    """
    Conecta y descarga datos de una Google Sheet específica.
    """
    try:
        # Inicializar conexión con Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Lectura hoja especifica
        df = conn.read(
            spreadsheet=url,
            worksheet=sheet_name,
            ttl=ttl
        )
        return df
    except Exception as e:
        st.error(f"Error al conectar con la hoja '{sheet_name}': {e}")
        return pd.DataFrame()