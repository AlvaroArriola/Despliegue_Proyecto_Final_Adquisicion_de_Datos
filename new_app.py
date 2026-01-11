import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="F1 • Racing Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

F1_CSS = """
<style>
:root{
  --card: rgba(255,255,255,0.06);
  --stroke: rgba(255,255,255,0.10);
  --text: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.68);
  --shadow: 0 12px 30px rgba(0,0,0,0.35);
  --radius: 18px;
}
html, body, [class*="css"] {
  background: radial-gradient(1200px 600px at 20% 0%, rgba(255,30,30,0.18), transparent 55%),
              radial-gradient(1000px 500px at 80% 20%, rgba(247,201,72,0.12), transparent 60%),
              linear-gradient(180deg, #070A0E 0%, #0B0F14 100%);
  color: var(--text);
}
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border-right: 1px solid var(--stroke);
}
.hdr {
  padding: 18px 18px;
  background: linear-gradient(135deg, rgba(255,30,30,0.20), rgba(255,255,255,0.05));
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.card {
  background: linear-gradient(180deg, var(--card), rgba(255,255,255,0.03));
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 16px 16px;
  box-shadow: var(--shadow);
}
div[data-testid="stMetric"]{
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--stroke);
  padding: 12px 12px;
  border-radius: 16px;
}
</style>
"""
st.markdown(F1_CSS, unsafe_allow_html=True)

def plotly_layout(fig, title=None):
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="rgba(255,255,255,0.90)"),
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(
            bgcolor="rgba(255,255,255,0.03)",
            bordercolor="rgba(255,255,255,0.10)",
            borderwidth=1
        )
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.08)")
    return fig

def nice_int(x):
    if pd.isna(x): return "—"
    try: return f"{int(x):,}".replace(",", ".")
    except: return str(x)

def nice_float(x, digits=2):
    if pd.isna(x): return "—"
    try:
        return f"{float(x):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(x)

@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)

    # Make column access robust
    pos_col = "Position" if "Position" in df.columns else ("Pos." if "Pos." in df.columns else None)

    # Resolve duplicated DriverNumber columns
    if "DriverNumber" in df.columns and "DriverNumber.1" in df.columns:
        # Prefer the one with fewer nulls
        a = df["DriverNumber"]
        b = df["DriverNumber.1"]
        df["DriverNumber_clean"] = np.where(a.notna(), a, b)
    elif "DriverNumber" in df.columns:
        df["DriverNumber_clean"] = df["DriverNumber"]
    elif "DriverNumber.1" in df.columns:
        df["DriverNumber_clean"] = df["DriverNumber.1"]
    else:
        df["DriverNumber_clean"] = np.nan

    # Numeric conversions
    if pos_col:
        df["Pos_num"] = pd.to_numeric(df[pos_col], errors="coerce")
    else:
        df["Pos_num"] = np.nan

    df["Grid_num"] = pd.to_numeric(df.get("Grid"), errors="coerce")
    df["Points"] = pd.to_numeric(df.get("Points"), errors="coerce").fillna(0)

    if "NPitstops" in df.columns:
        df["NPitstops"] = pd.to_numeric(df["NPitstops"], errors="coerce")
    if "MedianPitStopDuration" in df.columns:
        df["MedianPitStopDuration"] = pd.to_numeric(df["MedianPitStopDuration"], errors="coerce")

    # DNF heuristic
    if "Time/Retired" in df.columns:
        t = df["Time/Retired"].astype(str).str.lower()
        df["IsDNF"] = df["Pos_num"].isna() | t.str.contains("ret|dnf|dsq|dns|dnc", regex=True)
    else:
        df["IsDNF"] = df["Pos_num"].isna()

    df["PosGain"] = df["Grid_num"] - df["Pos_num"]

    for c in ["Driver", "Constructor"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return df

# Header
st.markdown(
    """
    <div class="hdr">
      <div style="display:flex; align-items:center; justify-content:space-between; gap:16px;">
        <div>
          <h1>🏁 F1 • Racing Dashboard</h1>
          <p>Resultados + pitstops (2019–2023). Standings, racecraft y análisis de pits.</p>
        </div>
        <div style="text-align:right;color:rgba(255,255,255,0.70);font-size:12px;">
          Carbon • Neon • F1 red
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

CSV_PATH = "df_final.csv"
df = load_csv(CSV_PATH)

# Filters
seasons = sorted(df["Season"].dropna().unique().tolist())
races = sorted(df["RaceNumber"].dropna().unique().tolist())
teams = sorted(df["Constructor"].dropna().unique().tolist()) if "Constructor" in df.columns else []
drivers = sorted(df["Driver"].dropna().unique().tolist()) if "Driver" in df.columns else []

with st.sidebar:
    sel_seasons = st.multiselect("Temporada", seasons, default=[max(seasons)] if seasons else seasons)
    sel_races = st.multiselect("RaceNumber", races, default=races)
    sel_teams = st.multiselect("Equipo", teams, default=teams)
    sel_drivers = st.multiselect("Piloto", drivers, default=drivers[:10] if len(drivers) > 10 else drivers)
    include_dnfs = st.toggle("Incluir DNFs", value=True)
    only_points = st.toggle("Solo puntos > 0", value=False)

dff = df.copy()
if sel_seasons: dff = dff[dff["Season"].isin(sel_seasons)]
if sel_races: dff = dff[dff["RaceNumber"].isin(sel_races)]
if sel_teams and "Constructor" in dff.columns: dff = dff[dff["Constructor"].isin(sel_teams)]
if sel_drivers and "Driver" in dff.columns: dff = dff[dff["Driver"].isin(sel_drivers)]
if not include_dnfs: dff = dff[~dff["IsDNF"]]
if only_points: dff = dff[dff["Points"] > 0]

# KPIs
c1, c2, c3, c4, c5 = st.columns(5)
kpi_events = dff[["Season", "RaceNumber"]].drop_duplicates().shape[0]
kpi_drivers = dff["Driver"].nunique() if "Driver" in dff.columns else np.nan
kpi_teams = dff["Constructor"].nunique() if "Constructor" in dff.columns else np.nan
kpi_points = dff["Points"].sum()
kpi_dnfs = int(dff["IsDNF"].sum())

with c1: st.metric("Eventos (Season×Race)", nice_int(kpi_events))
with c2: st.metric("Pilotos", nice_int(kpi_drivers))
with c3: st.metric("Equipos", nice_int(kpi_teams))
with c4: st.metric("Puntos (suma)", nice_float(kpi_points, 0))
with c5: st.metric("DNFs", nice_int(kpi_dnfs))

st.write("")
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🏆 Standings", "🛠️ Pitstops", "🗂️ Tabla"])

with tab1:
    colA, colB = st.columns([1.05, 0.95])

    with colA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🔥 Ranking por puntos (Top 20)")
        by_driver = (
            dff.groupby("Driver", as_index=False)["Points"]
            .sum()
            .sort_values("Points", ascending=False)
            .head(20)
        )
        fig = px.bar(by_driver, x="Points", y="Driver", orientation="h")
        fig = plotly_layout(fig, "Top 20 • Puntos")
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🧠 Grid vs Finish (racecraft)")
        scat = dff.dropna(subset=["Grid_num", "Pos_num"]).copy()
        if len(scat) == 0:
            st.info("No hay suficientes datos numéricos de Grid/Position con los filtros actuales.")
        else:
            fig = px.scatter(
                scat,
                x="Grid_num",
                y="Pos_num",
                color="Constructor",
                hover_data=["Driver", "Season", "RaceNumber", "Points", "Time/Retired"],
                opacity=0.85,
            )
            fig = plotly_layout(fig, "Grid (x) vs Posición final (y) • Menor es mejor")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    colC, colD = st.columns([1.05, 0.95])

    with colC:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📈 Ganancia de posiciones (Grid − Finish)")
        tmp = dff.dropna(subset=["PosGain"])
        if len(tmp) == 0:
            st.info("Sin datos suficientes para PosGain.")
        else:
            fig = px.histogram(tmp, x="PosGain", nbins=30)
            fig = plotly_layout(fig, "Distribución de PosGain")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with colD:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🧱 Puntos por equipo")
        by_team = (
            dff.groupby("Constructor", as_index=False)["Points"]
            .sum()
            .sort_values("Points", ascending=False)
            .head(12)
        )
        fig = px.bar(by_team, x="Constructor", y="Points")
        fig = plotly_layout(fig, "Top 12 • Puntos por equipo")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🏆 Standings acumulados por temporada")

    d = dff.copy()
    d["RaceKey"] = pd.to_numeric(d["RaceNumber"], errors="coerce")

    driver_points = (
        d.groupby(["Season", "RaceKey", "Driver"], as_index=False)["Points"].sum()
        .sort_values(["Season", "RaceKey"])
    )
    driver_points["CumPoints"] = driver_points.groupby(["Season", "Driver"])["Points"].cumsum()

    top_drivers = (
        driver_points.groupby("Driver")["Points"].sum().sort_values(ascending=False).head(8).index.tolist()
    )
    dp = driver_points[driver_points["Driver"].isin(top_drivers)]

    fig = px.line(dp, x="RaceKey", y="CumPoints", color="Driver", facet_row="Season", markers=True)
    fig = plotly_layout(fig, "Acumulado de puntos • Top 8 (según filtros)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🛠️ Pitstops • frecuencia y duración")

    if "NPitstops" not in dff.columns or "MedianPitStopDuration" not in dff.columns:
        st.info("No encuentro columnas de pitstops en el dataset filtrado.")
    else:
        col1, col2 = st.columns([0.95, 1.05])

        with col1:
            tmp = dff.groupby("Driver", as_index=False)["NPitstops"].mean().sort_values("NPitstops", ascending=False).head(20)
            fig = px.bar(tmp, x="NPitstops", y="Driver", orientation="h")
            fig = plotly_layout(fig, "Top 20 • NPitstops (media)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            tmp2 = dff.dropna(subset=["MedianPitStopDuration"])
            if len(tmp2) == 0:
                st.info("No hay duraciones de pitstop con los filtros actuales.")
            else:
                fig2 = px.box(tmp2, x="Constructor", y="MedianPitStopDuration", points="outliers")
                fig2 = plotly_layout(fig2, "Distribución • MedianPitStopDuration por equipo")
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("<hr/>", unsafe_allow_html=True)
        tmp3 = dff.dropna(subset=["NPitstops", "MedianPitStopDuration"])
        fig3 = px.scatter(
            tmp3,
            x="NPitstops",
            y="MedianPitStopDuration",
            color="Constructor",
            hover_data=["Driver", "Season", "RaceNumber", "Points", "Time/Retired"],
            opacity=0.85,
        )
        fig3 = plotly_layout(fig3, "NPitstops vs MedianPitStopDuration")
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🗂️ Tabla (filtrada)")
    st.dataframe(dff, use_container_width=True, height=520)
    st.markdown("</div>", unsafe_allow_html=True)
