import os
from PIL import Image
import streamlit as st 
from streamlit_option_menu import option_menu

# Modulos propios
from modules.inicio import show_inicio
from modules.plantilla import show_plantilla
from modules.asistencia import show_asistencia
from modules.cargas import show_cargas
# from modules.estadisticas import show_stats

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logo_path = os.path.join(BASE_DIR, 'assets','CD ILLAPEL BASQUETBOL.png')

# Configuración de la página principal
im = Image.open(logo_path)
st.set_page_config(page_title='Illapel Basquetbol', page_icon=im, layout='wide')

# Función principal de la aplicación
def main():
    selected = option_menu(
        menu_title=None, 
        options=["Inicio", "Plantilla", "Asistencia", "Cargas", "Estadisticas"], 
        icons=["house", "people", "calendar-check", "activity", "graph-up"], 
        orientation="horizontal"
    )

    # El router: app.py solo decide qué función llamar
    if selected == "Inicio":
        show_inicio()
        
    elif selected == "Plantilla":
        show_plantilla()

    elif selected == "Asistencia":
        show_asistencia()

    elif selected == "Cargas":
        show_cargas()
                
    elif selected == "Estadisticas":
        st.write("Mostrando Estadisticas")
        # show_stats()

if __name__ == "__main__":
    main()