import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

from src.connector import get_data
from src.processors import process_attendance, get_session_summary, get_attendance_metrics
from src.session_utils import compute_session_order

from config import SHEETS_CONFIG

# -----------------------------
# Funciones de gráficos
# -----------------------------

def build_team_session_chart(df_summary: pd.DataFrame):
    """
    Gráfico de barras apiladas: asistentes vs ausentes por sesión
    df_summary viene de get_session_summary(df) y debe tener:
    ['Fecha', 'Turno sesion', 'Tipo sesion', 'Presentes', 'Ausentes']
    """

    df = df_summary.copy()

    # Día de la semana en español
    dias_es = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}
    df["DiaSemana"] = df["Fecha"].dt.weekday.map(dias_es)

    # Orden fijo dentro del día (Fisico AM, Cancha AM, Cancha PM)
    df["session_order"] = compute_session_order(df)

    # Ordenar por fecha y luego por orden de sesión dentro del día (cronológico)
    df = df.sort_values(["Fecha", "session_order"])

    # Etiqueta legible de sesión (ej: "Lun 02-03 | AM Fisico")
    df["Sesion"] = (
        df["DiaSemana"] + " " +
        df["Fecha"].dt.strftime("%d-%m") + " | " +
        df["Turno sesion"] + " " +
        df["Tipo sesion"]
    )

    # Asegurar que el eje X respete este orden
    sesion_order = df["Sesion"].tolist()

    # Pasamos a formato largo para barras apiladas
    df_long = df.melt(
        id_vars=["Sesion"],
        value_vars=["Presentes", "Ausentes"],
        var_name="Estado",
        value_name="Jugadores"
    )

    fig = px.bar(
        df_long,
        x="Sesion",
        y="Jugadores",
        color="Estado",
        barmode="stack",
        color_discrete_map={
            "Presentes": "#2ecc71",  # verde
            "Ausentes": "#e74c3c",   # rojo
        },
        category_orders={"Sesion": sesion_order},
        title="Asistencia por sesión (equipo)"
    )

    fig.update_layout(
        xaxis_title="Sesión",
        yaxis_title="Número de jugadores",
        xaxis_tickangle=-30,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def build_player_session_chart(df_attendance: pd.DataFrame, jugador: str):
    """
    Gráfico de barras para un jugador:
    Sesiones en las que asistió (verde) vs ausente (rojo).
    df_attendance ya viene filtrado por fechas / tipo / turno.
    """

    df = df_attendance[df_attendance["Nombre jugador"] == jugador].copy()
    if df.empty:
        return None

    dias_es = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}
    df["DiaSemana"] = df["Fecha"].dt.weekday.map(dias_es)

    # Orden fijo dentro del día (Fisico AM, Cancha AM, Cancha PM)
    df["session_order"] = compute_session_order(df)

    # Ordenar por fecha (cronológico) y luego por orden de sesión dentro del día
    df = df.sort_values(["Fecha", "session_order"])

    # Etiqueta de sesión usando este orden
    df["Sesion"] = (
        df["DiaSemana"] + " " +
        df["Fecha"].dt.strftime("%d-%m") + " | " +
        df["Turno sesion"] + " " +
        df["Tipo sesion"]
    )
    sesion_order = df["Sesion"].tolist()

    # Asistencia booleana -> texto
    df["Estado"] = df["Asistencia"].map({True: "Asistió", False: "Ausente"})
    df["Valor"] = 1  # siempre 1, solo cambia el color (presente/ausente)

    fig = px.bar(
        df,
        x="Sesion",
        y="Valor",
        color="Estado",
        barmode="stack",
        color_discrete_map={
            "Asistió": "#2ecc71",
            "Ausente": "#e74c3c",
        },
        category_orders={"Sesion": sesion_order},  # fija el orden del eje X
        title=f"Asistencia de {jugador} por sesión"
    )

    fig.update_layout(
        xaxis_title="Sesión",
        yaxis_title="Sesión (presente/ausente)",
        xaxis_tickangle=-30,
        yaxis=dict(showticklabels=False, range=[0, 1.2]),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


# -----------------------------
# Página principal de Asistencia
# -----------------------------

def show_asistencia():

    st.title("Asistencia a Entrenamientos")

    st.divider()

    # --- CARGA DE DATOS DESDE SHEETS ---
    with st.spinner("Cargando datos de asistencia..."):
        df_raw = get_data(
            SHEETS_CONFIG["asistencia"]["url"],
            SHEETS_CONFIG["asistencia"]["sheet"],
        )

    if df_raw.empty:
        st.error("No se pudo obtener información de asistencia desde Sheets.")
        return

    # Limpieza / estandarización (usa tus helpers en src.processors)
    df = process_attendance(df_raw)

    # --- SIDEBAR: FILTROS ---
    st.sidebar.subheader("Filtros de asistencia")

    # Rango de fechas
    min_date = df["Fecha"].min().date() if not df.empty else date.today()
    max_date = df["Fecha"].max().date() if not df.empty else date.today()

    fecha_input = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Soportar: una fecha, lista/tupla de 1 fecha o de 2 fechas
    if isinstance(fecha_input, (list, tuple)):
        if len(fecha_input) == 2:
            fecha_inicio, fecha_fin = fecha_input
        elif len(fecha_input) == 1:
            fecha_inicio = fecha_fin = fecha_input[0]
        else:
            # caso raro, volvemos a todo el rango
            fecha_inicio, fecha_fin = min_date, max_date
    else:
        # un solo objeto date
        fecha_inicio = fecha_fin = fecha_input

    fecha_inicio = pd.to_datetime(fecha_inicio)
    fecha_fin = pd.to_datetime(fecha_fin)

    # Turnos
    turnos_unicos = sorted(df["Turno sesion"].dropna().unique().tolist())
    turnos_sel = st.sidebar.multiselect(
        "Turno sesión",
        options=turnos_unicos,
        default=turnos_unicos,
    )

    # Tipo de sesión
    tipos_unicos = sorted(df["Tipo sesion"].dropna().unique().tolist())
    tipos_sel = st.sidebar.multiselect(
        "Tipo de sesión",
        options=tipos_unicos,
        default=tipos_unicos,
    )

    # Jugador (opcional)
    jugadores = ["(Todos)"] + sorted(df["Nombre jugador"].dropna().unique().tolist())
    jugador_sel = st.sidebar.selectbox("Jugador", jugadores)

    # --- APLICAR FILTROS ---

    # Si no se selecciona nada en turno/tipo, interpretamos como "todas las opciones"
    if len(turnos_sel) == 0:
        turnos_mask = True
    else:
        turnos_mask = df["Turno sesion"].isin(turnos_sel)

    if len(tipos_sel) == 0:
        tipos_mask = True
    else:
        tipos_mask = df["Tipo sesion"].isin(tipos_sel)

    mask = (
        (df["Fecha"] >= fecha_inicio)
        & (df["Fecha"] <= fecha_fin)
        & turnos_mask
        & tipos_mask
    )

    df_filtro = df.loc[mask].copy()

    if df_filtro.empty:
        st.warning("No hay registros para los filtros seleccionados.")
        return

    # --- LAYOUT PRINCIPAL: GRÁFICO + KPIs ---
    col_graf, col_kpis = st.columns([4, 1])

    with col_graf:
        if jugador_sel == "(Todos)":
            # Vista de equipo
            df_summary = get_session_summary(df_filtro)
            fig = build_team_session_chart(df_summary)
        else:
            # Vista individual
            fig = build_player_session_chart(df_filtro, jugador_sel)

        if fig is not None:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("El jugador seleccionado no tiene registros en el rango elegido.")

    with col_kpis:
        # Si se filtra un jugador, las métricas se calculan solo con ese jugador
        if jugador_sel == "(Todos)":
            df_for_metrics = df_filtro
        else:
            df_for_metrics = df_filtro[df_filtro["Nombre jugador"] == jugador_sel].copy()

        # Métricas globales (sobre todo el rango filtrado)
        metrics_total = get_attendance_metrics(df_for_metrics)

        st.metric("Asistencia promedio (total)", f"{metrics_total['pct_asistencia']:.1f}%")
        st.metric("Total de sesiones (total)", metrics_total["total_sesiones"])

        # Métricas de la semana actual (según la última fecha del filtro)
        iso = df_for_metrics["Fecha"].dt.isocalendar()
        ultima_semana = int(iso.week.max())
        ultimo_anio = int(iso.year.max())

        df_week = df_for_metrics[
            (iso.week == ultima_semana) & (iso.year == ultimo_anio)
        ].copy()

        if not df_week.empty:
            metrics_week = get_attendance_metrics(df_week)
            st.metric("Asistencia semana actual", f"{metrics_week['pct_asistencia']:.1f}%")
            st.metric("Sesiones semana actual", metrics_week["total_sesiones"])
        else:
            st.metric("Asistencia semana actual", "N/A")
            st.metric("Sesiones semana actual", 0)

    st.divider()

    # --- TABLA DE DETALLE ---
    st.subheader("Detalle de sesiones")

    if jugador_sel == "(Todos)":
        # Preparar datos para el selectbox (mismo orden que el gráfico, pero más reciente primero en tablas)
        dias_es = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}

        df_sesiones_detalle = df_filtro.copy()
        df_sesiones_detalle["DiaSemana"] = df_sesiones_detalle["Fecha"].dt.weekday.map(dias_es)
        df_sesiones_detalle["SesionLabel"] = (
            df_sesiones_detalle["DiaSemana"] + " " +
            df_sesiones_detalle["Fecha"].dt.strftime("%d-%m") + " | " +
            df_sesiones_detalle["Turno sesion"] + " " +
            df_sesiones_detalle["Tipo sesion"]
        )
        df_sesiones_detalle["session_order"] = compute_session_order(df_sesiones_detalle)
        # Más reciente primero en la tabla/select, pero respetando orden dentro del día
        df_sesiones_detalle = df_sesiones_detalle.sort_values(
            ["Fecha", "session_order"],
            ascending=[False, True],
        )

        # 1. Resumen por sesión (equipo) - PRIMERO
        df_summary = get_session_summary(df_filtro)
        df_summary["% Asistencia"] = (
            df_summary["Presentes"] /
            (df_summary["Presentes"] + df_summary["Ausentes"])
        ) * 100

        df_summary["session_order"] = compute_session_order(df_summary)
        df_summary = df_summary.sort_values(
            ["Fecha", "session_order"],
            ascending=[False, True],
        )

        df_mostrar = df_summary[[
            "Fecha",
            "Turno sesion",
            "Tipo sesion",
            "Presentes",
            "Ausentes",
            "% Asistencia",
        ]].copy()
        df_mostrar["Fecha"] = df_mostrar["Fecha"].dt.strftime("%d/%m/%Y")
        df_mostrar["% Asistencia"] = df_mostrar["% Asistencia"].round(1)

        st.dataframe(
            df_mostrar,
            hide_index=True,
            width='stretch',
        )

        # 2. Selectbox - DESPUÉS del resumen
        session_options = ["(Todas las sesiones)"] + df_sesiones_detalle["SesionLabel"].unique().tolist()
        selected_session = st.selectbox(
            "Ver detalle de jugadores para la sesión:",
            options=session_options,
        )

        # 3. Detalle de jugadores para la sesión seleccionada (con formato condicional)
        if selected_session and selected_session != "(Todas las sesiones)":
            st.markdown("### Jugadores en la sesión seleccionada")

            df_det = df_sesiones_detalle[df_sesiones_detalle["SesionLabel"] == selected_session].copy()
            df_det["Estado"] = df_det["Asistencia"].map({True: "Presente", False: "Ausente"})

            df_det_mostrar = df_det[[
                "Nombre jugador",
                "Estado",
                "Observaciones",
            ]].sort_values(["Estado", "Nombre jugador"])

            # Formato condicional: solo la celda "Ausente" (fondo rojo oscuro, texto blanco)
            def style_ausente(cell):
                if cell == "Ausente":
                    return "background-color: #c0392b; color: white"
                return ""

            df_styled = df_det_mostrar.style.map(style_ausente, subset=["Estado"])
            st.dataframe(df_styled, hide_index=True, width='stretch')
    else:
        # Detalle de ese jugador
        df_j = df_filtro[df_filtro["Nombre jugador"] == jugador_sel].copy()
        df_j["session_order"] = compute_session_order(df_j)
        # Más reciente primero, respetando orden dentro del día
        df_j = df_j.sort_values(
            ["Fecha", "session_order"],
            ascending=[False, True],
        )

        df_j["Fecha"] = df_j["Fecha"].dt.strftime("%d/%m/%Y")
        df_j["Asistencia"] = df_j["Asistencia"].map({True: "Sí", False: "No"})

        st.dataframe(
            df_j[[
                "Fecha",
                "Turno sesion",
                "Tipo sesion",
                "Asistencia",
                "Observaciones",
            ]],
            hide_index=True,
            width='stretch',
        )