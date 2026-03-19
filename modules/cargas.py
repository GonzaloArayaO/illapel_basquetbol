from datetime import date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.connector import get_data
from src.processors import (
    process_pre_entrenamiento,
    process_post_entrenamiento,
    _clean_rut_series,
)
from config import SHEETS_CONFIG


def build_carga_diaria_chart(df_daily: pd.DataFrame, etiqueta: str) -> go.Figure:
    """
    Gráfico de barras: carga diaria (RPE × duración) en el tiempo.
    df_daily debe tener columnas: Fecha, Carga_diaria
    """
    df = df_daily.sort_values("Fecha").copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Fecha_str"] = df["Fecha"].dt.strftime("%d/%m/%Y")

    # Títulos dinámicos para mayor claridad
    title_text = f"Carga Promedio por Día ({etiqueta})" if etiqueta == "Equipo" else f"Carga Total Diaria ({etiqueta})"
    y_axis_text = "Carga Promedio (AU)" if etiqueta == "Equipo" else "Carga Total (AU)"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["Fecha"],
            y=df["Carga_diaria"],
            name="Carga",
            customdata=df["RPE_diario"],  # Pasamos el RPE para usarlo en el tooltip
            marker_color="#3498db",
            hovertemplate="%{x|%d/%m/%Y}<br>Carga: %{y:.1f} AU<br>RPE Prom: %{customdata:.1f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title_text,
        xaxis_title="Fecha",
        yaxis_title=y_axis_text,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=60),
        xaxis=dict(
            tickformat="%d %b",
            tickmode="linear",
            dtick=86400000.0,
            tickangle=-45
        ),
        yaxis=dict(rangemode="tozero"),
    )
    return fig


def build_wellness_diario_chart(df_daily: pd.DataFrame, etiqueta: str) -> go.Figure:
    """
    Gráfico de barras: wellness_score en el tiempo.
    """
    df = df_daily.sort_values("Fecha").copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    title_text = f"Wellness Promedio ({etiqueta})" if etiqueta == "Equipo" else f"Wellness Diario ({etiqueta})"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["Fecha"],
            y=df["wellness_score"],
            name="Wellness",
            marker_color="#2ecc71",
            hovertemplate="%{x|%d/%m/%Y}<br>Wellness: %{y:.1f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title_text,
        xaxis_title="Fecha",
        yaxis_title="Wellness (mayor = mejor recuperación)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=60),
        xaxis=dict(
            tickformat="%d %b",
            tickmode="linear",
            dtick=86400000.0,
            tickangle=-45
        ),
        yaxis=dict(rangemode="tozero"),
    )
    return fig


def show_cargas():
    st.title("Control de Cargas de Entrenamiento")
    st.divider()
    # --- CARGA DE DATOS ---
    with st.spinner("Cargando datos..."):
        try:
            df_jug = get_data(
                SHEETS_CONFIG["bd_jugadores"]["url"],
                SHEETS_CONFIG["bd_jugadores"]["sheet"],
            )
        except Exception as e:
            st.error(f"No se pudo cargar BD jugadores: {e}")
            return
    if df_jug.empty:
        st.error("No se pudo cargar BD jugadores.")
        return
    if "Rut" not in df_jug.columns:
        st.error("BD jugadores no tiene la columna 'Rut'.")
        return
    df_jug = df_jug.copy()
    df_jug["Rut"] = _clean_rut_series(df_jug["Rut"])
    df_jug_min = df_jug[["Rut", "Nombre jugador"]].copy()
    try:
        df_pre_raw = get_data(
            SHEETS_CONFIG["pre_entrenamiento"]["url"],
            SHEETS_CONFIG["pre_entrenamiento"]["sheet"],
        )
        df_pre = process_pre_entrenamiento(df_pre_raw)
        df_pre = df_pre.merge(df_jug_min, on="Rut", how="left")
    except Exception as e:
        st.warning(
            "Hay datos con RUT o formato inválido en pre_entrenamiento. "
            "Verifica las respuestas del cuestionario manualmente."
        )
        st.exception(e)
        return
    try:
        df_post_raw = get_data(
            SHEETS_CONFIG["post_entrenamiento"]["url"],
            SHEETS_CONFIG["post_entrenamiento"]["sheet"],
        )
        df_post = process_post_entrenamiento(df_post_raw)
        df_post = df_post.merge(df_jug_min, on="Rut", how="left")
    except Exception as e:
        st.warning(
            "Hay datos con RUT o duración inválida en post_entrenamiento. "
            "Verifica las respuestas del cuestionario manualmente."
        )
        st.exception(e)
        return
    if df_pre.empty and df_post.empty:
        st.warning("No hay datos en pre_entrenamiento ni post_entrenamiento.")
        return
    fechas_carga = pd.Series(dtype="object")
    fechas_wellness = pd.Series(dtype="object")
    if not df_post.empty:
        fechas_carga = pd.to_datetime(df_post["Fecha"])
    if not df_pre.empty:
        fechas_wellness = pd.to_datetime(df_pre["Fecha"])
    all_dates = pd.concat([fechas_carga, fechas_wellness], ignore_index=True)
    if all_dates.empty:
        st.warning("No hay fechas disponibles.")
        return
    min_date = all_dates.min().date()
    max_date = all_dates.max().date()
    # --- SIDEBAR: FILTROS ---
    st.sidebar.subheader("Filtros de cargas")
    fecha_input = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(fecha_input, (list, tuple)):
        fecha_inicio, fecha_fin = (
            (fecha_input[0], fecha_input[1]) if len(fecha_input) == 2
            else (fecha_input[0], fecha_input[0]) if len(fecha_input) == 1
            else (min_date, max_date)
        )
    else:
        fecha_inicio = fecha_fin = fecha_input
    fecha_inicio = pd.to_datetime(fecha_inicio)
    fecha_fin = pd.to_datetime(fecha_fin)
    jugadores_post = df_post["Nombre jugador"].dropna().unique() if not df_post.empty else []
    jugadores_pre = df_pre["Nombre jugador"].dropna().unique() if not df_pre.empty else []
    jugadores = ["(Todos)"] + sorted(set(jugadores_post) | set(jugadores_pre))
    jugador_sel = st.sidebar.selectbox("Jugador", jugadores)
    # --- APLICAR FILTROS ---
    mask_post = (pd.to_datetime(df_post["Fecha"]) >= fecha_inicio) & (pd.to_datetime(df_post["Fecha"]) <= fecha_fin)
    mask_pre = (pd.to_datetime(df_pre["Fecha"]) >= fecha_inicio) & (pd.to_datetime(df_pre["Fecha"]) <= fecha_fin)
    df_post_f = df_post.loc[mask_post].copy()
    df_pre_f = df_pre.loc[mask_pre].copy()
    if jugador_sel != "(Todos)":
        df_post_f = df_post_f[df_post_f["Nombre jugador"] == jugador_sel]
        df_pre_f = df_pre_f[df_pre_f["Nombre jugador"] == jugador_sel]
    etiqueta = "Equipo" if jugador_sel == "(Todos)" else jugador_sel
    # --- AGREGAR POR DÍA ---
    if not df_post_f.empty:
        # 1. Calcular Carga TOTAL por JUGADOR para cada día (suma de sesiones AM + PM)
        #    También calculamos el RPE promedio del jugador en ese día
        df_player_day = df_post_f.groupby(["Fecha", "Nombre jugador"]).agg(
            daily_load=("CargaSesion", "sum"),
            daily_rpe=("RPE", "mean")
        ).reset_index()

        # 2. Calcular el PROMEDIO del equipo (o del jugador) para cada día
        df_temp = df_player_day.groupby("Fecha").agg(
            Carga_diaria=("daily_load", "mean"),
            RPE_diario=("daily_rpe", "mean")
        ).reset_index()

        df_temp["Fecha"] = pd.to_datetime(df_temp["Fecha"])
    else:
        df_temp = pd.DataFrame(columns=["Fecha", "Carga_diaria", "RPE_diario"])

    # Generar rango completo de fechas para rellenar vacíos con 0
    full_idx = pd.date_range(start=fecha_inicio, end=fecha_fin, freq="D")
    df_dates = pd.DataFrame({"Fecha": full_idx})
    df_carga_diaria = pd.merge(df_dates, df_temp, on="Fecha", how="left").fillna(0)

    # --- AGREGAR POR DÍA (Wellness) ---
    if not df_pre_f.empty:
        df_w_temp = df_pre_f.groupby("Fecha").agg(wellness_score=("wellness_score", "mean")).reset_index()
        df_w_temp["Fecha"] = pd.to_datetime(df_w_temp["Fecha"])
    else:
        df_w_temp = pd.DataFrame(columns=["Fecha", "wellness_score"])

    # Rellenar fechas vacías con 0 (igual que en cargas)
    df_wellness_diario = pd.merge(df_dates, df_w_temp, on="Fecha", how="left").fillna(0)

    # --- LAYOUT: KPIs + GRÁFICOS ---
    col_graf, col_kpis = st.columns([4, 1])
    with col_kpis:
        # --- CALCULO MÉTRICAS SEMANALES ---
        # Usamos df_post_f para obtener fechas reales con datos
        if not df_post_f.empty:
            last_real_date = pd.to_datetime(df_post_f["Fecha"]).max()
            
            # Identificar semana actual y anterior basada en la última data disponible
            curr_iso = last_real_date.isocalendar()
            curr_week_num, curr_year = curr_iso.week, curr_iso.year
            
            prev_date = last_real_date - pd.Timedelta(days=7)
            prev_iso = prev_date.isocalendar()
            prev_week_num, prev_year = prev_iso.week, prev_iso.year

            # Sumar cargas desde el df_carga_diaria (que ya tiene promedios por día)
            # Filtramos por año y semana
            mask_curr = (df_carga_diaria["Fecha"].dt.isocalendar().week == curr_week_num) & \
                        (df_carga_diaria["Fecha"].dt.year == curr_year)
            load_curr = df_carga_diaria.loc[mask_curr, "Carga_diaria"].sum()

            mask_prev = (df_carga_diaria["Fecha"].dt.isocalendar().week == prev_week_num) & \
                        (df_carga_diaria["Fecha"].dt.year == prev_year)
            load_prev = df_carga_diaria.loc[mask_prev, "Carga_diaria"].sum()

            st.metric("Carga Semana Actual (prom.)", f"{load_curr:.0f}", delta=f"{load_curr - load_prev:.0f} vs sem. ant.")
            st.metric("Carga Semana Anterior (prom.)", f"{load_prev:.0f}")
        else:
            st.info("Sin datos recientes")
            
        # --- MÉTRICAS WELLNESS ---
        if not df_wellness_diario.empty:
            # Importante: Filtramos > 0 para los cálculos, ya que rellenamos con 0s los días sin datos
            valid_w = df_wellness_diario[df_wellness_diario["wellness_score"] > 0].copy()
            
            # 1. Wellness Semana Actual (prom. de la semana del último dato disponible)
            if not valid_w.empty:
                last_w_date = valid_w["Fecha"].max()
                w_iso = last_w_date.isocalendar()
                mask_w_week = (valid_w["Fecha"].dt.isocalendar().week == w_iso.week) & \
                              (valid_w["Fecha"].dt.year == w_iso.year)
                w_avg_week = valid_w.loc[mask_w_week, "wellness_score"].mean()
                st.metric("Wellness Semanal (prom.)", f"{w_avg_week:.1f}")
            else:
                st.metric("Wellness Semanal (prom.)", "N/A")

            # 2. Wellness Hoy (Día actual) vs Ayer
            hoy = pd.Timestamp.now().normalize()
            ayer = hoy - pd.Timedelta(days=1)

            # Buscamos en el dataframe completo (que tiene todas las fechas)
            val_hoy_row = df_wellness_diario.loc[df_wellness_diario["Fecha"] == hoy, "wellness_score"]
            val_ayer_row = df_wellness_diario.loc[df_wellness_diario["Fecha"] == ayer, "wellness_score"]
            
            # Validamos que exista dato (>0)
            score_hoy = val_hoy_row.values[0] if not val_hoy_row.empty and val_hoy_row.values[0] > 0 else None
            score_ayer = val_ayer_row.values[0] if not val_ayer_row.empty and val_ayer_row.values[0] > 0 else None

            delta_val = (score_hoy - score_ayer) if (score_hoy is not None and score_ayer is not None) else None
                
            if score_hoy is not None:
                st.metric("Wellness Hoy", f"{score_hoy:.1f}", delta=f"{delta_val:.1f}" if delta_val is not None else None)
            else:
                st.metric("Wellness Hoy", "S/D") # Sin Datos (Aún no responden hoy)
        else:
            st.info("Sin datos de Wellness")

    with col_graf:
        if not df_carga_diaria.empty:
            st.plotly_chart(build_carga_diaria_chart(df_carga_diaria, etiqueta), width='stretch')
        else:
            st.info("No hay datos de carga para los filtros seleccionados.")
    st.divider()
    if not df_wellness_diario.empty:
        st.plotly_chart(build_wellness_diario_chart(df_wellness_diario, etiqueta), width='stretch')
    else:
        st.info("No hay datos de wellness para los filtros seleccionados.")