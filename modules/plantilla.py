import streamlit as st
import pandas as pd
import os
from PIL import Image
from src.connector import get_data
from src.processors import calculate_age 
from config import SHEETS_CONFIG

def show_plantilla():
    # 1. CABECERA CON LOGO PEQUEÑO
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, 'assets', 'CD ILLAPEL BASQUETBOL.png')
    

    c1, c2 = st.columns([1, 6])
    with c1:
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            st.image(logo_img, width=100)
    with c2:
        st.title("Roster LNB2 - 2026")
    
    st.divider()

    # 2. CARGA Y PROCESAMIENTO
    with st.spinner("Cargando lista de jugadores..."):
        df = get_data(
            SHEETS_CONFIG["bd_jugadores"]["url"], 
            SHEETS_CONFIG["bd_jugadores"]["sheet"]
        )

    if not df.empty:
        # Procesamiento de datos
        df['Fecha de nacimiento'] = pd.to_datetime(df['Fecha de nacimiento'], dayfirst=True, errors='coerce')
        df['Edad'] = df['Fecha de nacimiento'].apply(calculate_age)
        df['Fecha de nacimiento'] = df['Fecha de nacimiento'].dt.strftime('%d/%m/%Y')
        df_final = df[['Nombre jugador', 'Rut', 'Fecha de nacimiento', 'Edad']]

        # 3. VISUALIZACIÓN
        _, col_tabla, _ = st.columns([1, 4, 2]) 
        
        with col_tabla:
            st.dataframe(
                df_final, 
                width='stretch', 
                height=600,
                hide_index=True,
                column_config={
                    "Nombre jugador": st.column_config.TextColumn("Nombre", width="medium"),
                    "Rut": st.column_config.TextColumn("RUT", width="small"),
                    "Fecha de nacimiento": st.column_config.TextColumn("Fecha Nac.", width="small"),
                    "Edad": st.column_config.NumberColumn("Edad", width=20, format="%d")
                }
            )
            st.caption(f"Total de jugadores: {len(df_final)}")
    
    else:
        st.error("No se pudo conectar con la base de datos de jugadores.")