import streamlit as st
import os
from PIL import Image

def show_inicio():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, 'assets', 'CD ILLAPEL BASQUETBOL.png')
    
    # Contenedor principal
    with st.container():
        # --- FILA 1: CABECERA (Logo y Título) ---
        col_logo, col_titulo = st.columns([1, 4])
        
        with col_logo:
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                
                c_izq, c_img, c_der = st.columns([1, 5, 1]) 
                
                with c_img:
                    st.image(logo_img, width='stretch')
            else:
                st.error("⚠️ Archivo de logo no encontrado en 'assets/'.")
        
        with col_titulo:
            st.title("CD Illapel Basquetbol")
            st.markdown('<h4 style="margin-top: 0; color: #737272;">- Plataforma de Gestión del club</h4>', unsafe_allow_html=True)
            st.divider()
            
        # --- FILA 2: CUERPO DE TEXTO ---
        st.markdown("### Bienvenido al Sistema de Gestión")
        
        st.write("""
        Esta plataforma centraliza información importante del club, 
        utilizando datos para optimizar el rendimiento de los jugadores.
        Utiliza el menú superior para navegar.
        """)
        
        # Usamos un expander para detallar las secciones sin saturar la vista inicial
        with st.expander("🔍 Detalle de los Módulos Disponibles", expanded=True):
            st.markdown("""
            * **👥 Plantilla:** Datos personales de jugadores.
            * **📅 Asistencia:** Control de asistencia por sesión (AM/PM) y tipo de entrenamiento.
            * **⚡ Cargas:** Monitoreo de Wellness y RPE (Esfuerzo Percibido).
            * **📊 Estadísticas:** Estadisticas CLNB 2.
            """)