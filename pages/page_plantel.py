"""
page_plantel.py
===============
Módulo de la página "📋 Plantel" para FUTDB.

Incluir en app.py:
    from pages.page_plantel import render_plantel
    ...
    elif pagina.startswith("📋"):
        render_plantel()

Requiere que ConectorPlantel esté inicializado y pasado como argumento,
o bien se instancia internamente con caché de Streamlit.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# CSS adicional específico del módulo Plantel (inyectado una sola vez)
_CSS_PLANTEL = """
<style>
/* ── Plantel: tabla jugadores ── */
.plantel-table { width:100%; border-collapse:collapse; font-family:'Barlow',sans-serif; font-size:.86rem; color:#cdd5ca; }
.plantel-table thead tr { background:#0d0f0e; border-bottom:1px solid #1e2420; }
.plantel-table thead th { padding:.55rem .9rem; text-align:left; font-family:'DM Mono',monospace;
    font-size:.65rem; font-weight:400; color:#4b5a4d; text-transform:uppercase; letter-spacing:.08em; }
.plantel-table tbody tr { border-bottom:1px solid #141714; transition:background .1s; }
.plantel-table tbody tr:hover { background:#141714; }
.plantel-table tbody td { padding:.6rem .9rem; vertical-align:middle; }
.plantel-table tbody td.num { text-align:right; font-family:'DM Mono',monospace; font-size:.8rem; }

/* ── Estado badges ── */
.estado-badge { display:inline-block; padding:.15rem .55rem; border-radius:4px;
    font-family:'DM Mono',monospace; font-size:.65rem; font-weight:500; }
.estado-Activo      { background:#162119; color:#4ade80; }
.estado-Lesionado   { background:#2a1616; color:#f87171; }
.estado-Suspendido  { background:#2a1f00; color:#f59e0b; }
.estado-Baja        { background:#1a1a1a; color:#6b7a6d; }

/* ── Posición dots ── */
.pos-badge { display:inline-block; padding:.15rem .55rem; border-radius:4px;
    font-family:'DM Mono',monospace; font-size:.65rem; }
.pos-Portero        { background:#1a2330; color:#60a5fa; }
.pos-Defensor       { background:#162119; color:#4ade80; }
.pos-Mediocampista  { background:#2a1f00; color:#f59e0b; }
.pos-Delantero      { background:#2a1616; color:#f87171; }

/* ── Selector jugador card ── */
.jugador-selector-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:8px; margin-bottom:1.2rem; }
.jugador-chip { background:#111412; border:1px solid #1e2420; border-radius:10px;
    padding:.7rem 1rem; cursor:pointer; transition:all .15s; }
.jugador-chip:hover { border-color:#4ade80; background:#162119; }
.jugador-chip .jc-num { font-family:'Barlow Condensed',sans-serif; font-size:1.4rem;
    font-weight:900; color:#1e2420; line-height:1; }
.jugador-chip .jc-name { font-size:.82rem; font-weight:500; color:#e2e8df; margin-top:.15rem; }
.jugador-chip .jc-pos  { font-size:.7rem; color:#4b5a4d; margin-top:.1rem; }

/* ── Progress bar métrica ── */
.metric-bar-wrap { margin-bottom:.7rem; }
.metric-bar-label { display:flex; justify-content:space-between; font-family:'DM Mono',monospace;
    font-size:.68rem; color:#4b5a4d; margin-bottom:.25rem; }
.metric-bar-bg { height:5px; background:#1e2420; border-radius:3px; overflow:hidden; }
.metric-bar-fill { height:100%; border-radius:3px; background:linear-gradient(90deg,#4ade80,#22c55e); }
.metric-bar-fill.amber { background:linear-gradient(90deg,#f59e0b,#d97706); }
.metric-bar-fill.red   { background:linear-gradient(90deg,#f87171,#ef4444); }
</style>
"""

# Mapeos de color Plotly por posición
_POS_COLORS = {
    "Portero":       "#60a5fa",
    "Defensor":      "#4ade80",
    "Mediocampista": "#f59e0b",
    "Delantero":     "#f87171",
}
_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#111412",
    font=dict(family="DM Mono", color="#4b5a4d", size=10),
    margin=dict(l=10, r=10, t=30, b=30),
    xaxis=dict(gridcolor="#1a1f1c", tickfont=dict(size=9)),
    yaxis=dict(gridcolor="#1a1f1c", tickfont=dict(size=9)),
)


# ── Helpers internos ──────────────────────────────────────────────────────────

def _estado_badge(estado: str) -> str:
    cls = estado.replace(" ", "-")
    return f'<span class="estado-badge estado-{cls}">{estado}</span>'

def _pos_badge(pos: str) -> str:
    cls = pos.replace(" ", "")
    return f'<span class="pos-badge pos-{cls}">{pos}</span>'

def _section(titulo: str, sub: str = ""):
    sub_html = f'<span style="font-family:\'DM Mono\',monospace;font-size:.72rem;color:#4b5a4d">— {sub}</span>' if sub else ""
    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:1rem;margin:2rem 0 1rem;
                padding-bottom:.6rem;border-bottom:1px solid #1e2420">
        <span style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.4rem;
                     font-weight:700;color:#e2e8df;letter-spacing:.04em;text-transform:uppercase">
            {titulo}</span>
        {sub_html}
    </div>""", unsafe_allow_html=True)

def _kpi(label, value, sub="", color=""):
    accent = {"gold": "#f59e0b", "coral": "#f87171", "blue": "#60a5fa"}.get(color, "#4ade80")
    st.markdown(f"""
    <div style="background:#111412;border:1px solid #1e2420;border-radius:12px;
                padding:1rem 1.2rem;border-top:2px solid {accent}">
        <div style="font-family:'DM Mono',monospace;font-size:.65rem;color:#4b5a4d;
                    text-transform:uppercase;letter-spacing:.1em;margin-bottom:.35rem">{label}</div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:1.9rem;
                    font-weight:700;color:#fff;line-height:1">{value}</div>
        <div style="font-size:.72rem;color:#4b5a4d;margin-top:.25rem">{sub}</div>
    </div>""", unsafe_allow_html=True)

def _progress_bar(label, value, max_val, color="green"):
    pct = min(int(value / max_val * 100), 100) if max_val else 0
    cls = "amber" if color == "amber" else ("red" if color == "red" else "")
    st.markdown(f"""
    <div class="metric-bar-wrap">
        <div class="metric-bar-label"><span>{label}</span><span>{value}</span></div>
        <div class="metric-bar-bg"><div class="metric-bar-fill {cls}" style="width:{pct}%"></div></div>
    </div>""", unsafe_allow_html=True)


# ── Tabs de la página ─────────────────────────────────────────────────────────

def _tab_jugadores(cp):
    df = cp.jugadores()
    if df.empty:
        st.warning("No se encontraron jugadores.")
        return

    # KPIs globales
    col1, col2, col3, col4 = st.columns(4)
    with col1: _kpi("Total plantel",  str(len(df)), "jugadores registrados")
    with col2: _kpi("Activos",        str(len(df[df["ESTADO"] == "Activo"])),   "disponibles", "")
    with col3: _kpi("Lesionados",     str(len(df[df["ESTADO"] == "Lesionado"])), "bajas médicas", "coral")
    with col4:
        avg_w = df["PESO INICIAL (kg)"].mean() if "PESO INICIAL (kg)" in df.columns else 0
        _kpi("Peso promedio", f"{avg_w:.1f} kg", "plantel completo", "blue")

    # Gráfico distribución posiciones
    _section("Distribución por posición")
    col_g, col_t = st.columns([1, 2])
    with col_g:
        pos_counts = df["POSICIÓN"].value_counts().reset_index()
        pos_counts.columns = ["Posición", "Cantidad"]
        colors = [_POS_COLORS.get(p, "#4b5a4d") for p in pos_counts["Posición"]]
        fig = go.Figure(go.Pie(
            labels=pos_counts["Posición"], values=pos_counts["Cantidad"],
            marker=dict(colors=colors, line=dict(color="#0d0f0e", width=2)),
            hole=0.55, textfont=dict(family="DM Mono", size=10),
        ))
        fig.update_layout(**{**_PLOTLY_LAYOUT, "height": 240, "showlegend": False,
                             "margin": dict(l=0, r=0, t=10, b=10)})
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        # Tabla completa
        filas = ""
        for _, r in df.iterrows():
            filas += f"""<tr>
                <td class="num" style="color:#4b5a4d">{r.get('NÚMERO CAMISETA','—')}</td>
                <td style="font-weight:500;color:#e2e8df">{r.get('APELLIDO','')} {r.get('NOMBRE','')}</td>
                <td>{_pos_badge(str(r.get('POSICIÓN','')))}</td>
                <td class="num">{r.get('EDAD','—')}</td>
                <td class="num">{r.get('PESO INICIAL (kg)','—')}</td>
                <td class="num">{r.get('ALTURA (cm)','—')}</td>
                <td>{_estado_badge(str(r.get('ESTADO','—')))}</td>
            </tr>"""
        st.markdown(f"""
        <div style="background:#111412;border:1px solid #1e2420;border-radius:12px;overflow:hidden">
            <table class="plantel-table">
                <thead><tr>
                    <th class="num">#</th><th>Jugador</th><th>Posición</th>
                    <th class="num">Edad</th><th class="num">Peso kg</th>
                    <th class="num">Alt cm</th><th>Estado</th>
                </tr></thead>
                <tbody>{filas}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)


def _tab_fisico(cp):
    df_j = cp.jugadores()
    df_f = cp.sesiones_fisico()

    if df_f.empty:
        st.info("No hay sesiones físicas registradas.")
        return

    # Selector de jugador
    _section("Seleccioná un jugador")
    opciones = {f"{r['APELLIDO']} {r['NOMBRE']} (#{r['NÚMERO CAMISETA']})": r["ID_JUGADOR"]
                for _, r in df_j.iterrows()}
    sel_nombre = st.selectbox("Jugador", list(opciones.keys()), label_visibility="collapsed")
    pid = opciones[sel_nombre]
    df = df_f[df_f["ID_JUGADOR"] == pid].copy()
    df = df.sort_values("FECHA")

    if df.empty:
        st.warning("No hay sesiones físicas para este jugador.")
        return

    # KPIs últimas sesiones
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        delta = f"↓ {abs(last['PESO (kg)'] - prev['PESO (kg)']):.1f}" if prev is not None else ""
        _kpi("Peso actual", f"{last['PESO (kg)']} kg", delta, "")
    with col2:
        _kpi("Km última sesión", f"{last['KM RECORRIDOS']}", "km recorridos", "")
    with col3:
        _kpi("Kcal quemadas", f"{int(last['KCAL QUEMADAS'])}", "última sesión", "gold")
    with col4:
        _kpi("Vel. máx", f"{last['VEL. MÁX (km/h)']} km/h", "última sesión", "blue")

    # Gráficos evolución
    _section("Evolución física", f"{len(df)} sesiones registradas")
    col_a, col_b = st.columns(2)

    with col_a:
        fig1 = px.line(df, x="FECHA", y="KM RECORRIDOS", markers=True,
                       color_discrete_sequence=["#4ade80"], title="Km recorridos por sesión")
        fig1.update_traces(line=dict(width=2), marker=dict(size=5))
        fig1.update_layout(**{**_PLOTLY_LAYOUT, "height": 240, "title_font_color": "#6b7a6d",
                               "title_font_size": 11})
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        fig2 = px.line(df, x="FECHA", y="PESO (kg)", markers=True,
                       color_discrete_sequence=["#60a5fa"], title="Evolución de peso corporal")
        fig2.update_traces(line=dict(width=2), marker=dict(size=5))
        fig2.update_layout(**{**_PLOTLY_LAYOUT, "height": 240, "title_font_color": "#6b7a6d",
                               "title_font_size": 11})
        st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        fig3 = px.bar(df, x="FECHA", y="KCAL QUEMADAS", title="Calorías quemadas",
                      color_discrete_sequence=["#f59e0b"])
        fig3.update_layout(**{**_PLOTLY_LAYOUT, "height": 220, "title_font_color": "#6b7a6d",
                               "title_font_size": 11})
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        fig4 = px.line(df, x="FECHA", y=["FC MÁXIMA (bpm)", "FC PROMEDIO (bpm)"],
                       color_discrete_sequence=["#f87171", "#f59e0b"],
                       title="Frecuencia cardíaca")
        fig4.update_layout(**{**_PLOTLY_LAYOUT, "height": 220, "title_font_color": "#6b7a6d",
                               "title_font_size": 11,
                               "legend": dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)")})
        st.plotly_chart(fig4, use_container_width=True)

    # Promedios del jugador vs plantel
    _section("Comparativa vs plantel")
    col_p, col_v = st.columns(2)
    avg_jugador = df[["KM RECORRIDOS","KCAL QUEMADAS","VEL. MÁX (km/h)","SPRINTS >25km/h"]].mean()
    avg_plantel = df_f[["KM RECORRIDOS","KCAL QUEMADAS","VEL. MÁX (km/h)","SPRINTS >25km/h"]].mean()
    with col_p:
        st.markdown("<div style='font-family:DM Mono,monospace;font-size:.7rem;color:#4b5a4d;margin-bottom:.8rem'>PROMEDIOS DEL JUGADOR</div>", unsafe_allow_html=True)
        _progress_bar("Km / sesión",    round(avg_jugador["KM RECORRIDOS"], 1),    12)
        _progress_bar("Kcal / sesión",  round(avg_jugador["KCAL QUEMADAS"]),       1000, "amber")
        _progress_bar("Vel. máx km/h",  round(avg_jugador["VEL. MÁX (km/h)"], 1), 38)
        _progress_bar("Sprints",        round(avg_jugador["SPRINTS >25km/h"]),     25)
    with col_v:
        st.markdown("<div style='font-family:DM Mono,monospace;font-size:.7rem;color:#4b5a4d;margin-bottom:.8rem'>PROMEDIO PLANTEL</div>", unsafe_allow_html=True)
        _progress_bar("Km / sesión",    round(avg_plantel["KM RECORRIDOS"], 1),    12)
        _progress_bar("Kcal / sesión",  round(avg_plantel["KCAL QUEMADAS"]),       1000, "amber")
        _progress_bar("Vel. máx km/h",  round(avg_plantel["VEL. MÁX (km/h)"], 1), 38)
        _progress_bar("Sprints",        round(avg_plantel["SPRINTS >25km/h"]),     25)

    # Historial tabla
    _section("Historial de sesiones")
    st.dataframe(
        df[["FECHA","PESO (kg)","KM RECORRIDOS","KCAL QUEMADAS",
            "FC MÁXIMA (bpm)","FC PROMEDIO (bpm)","VEL. MÁX (km/h)","SPRINTS >25km/h"
            ]].sort_values("FECHA", ascending=False).reset_index(drop=True),
        use_container_width=True, height=280,
    )


def _tab_tecnico(cp):
    df_j = cp.jugadores()
    df_t = cp.sesiones_tecnico()

    if df_t.empty:
        st.info("No hay sesiones técnicas registradas.")
        return

    opciones = {f"{r['APELLIDO']} {r['NOMBRE']} (#{r['NÚMERO CAMISETA']})": r["ID_JUGADOR"]
                for _, r in df_j.iterrows()}
    _section("Seleccioná un jugador")
    sel_nombre = st.selectbox("Jugador técnico", list(opciones.keys()), label_visibility="collapsed")
    pid = opciones[sel_nombre]
    df = df_t[df_t["ID_JUGADOR"] == pid].copy()
    df = df.sort_values("FECHA")

    if df.empty:
        st.warning("No hay sesiones técnicas para este jugador.")
        return

    last = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    with col1: _kpi("% Pases",    f"{last['% PASES (auto)']}%", f"{int(last['PASES COMPLET.'])}/{int(last['PASES INTENT.'])} última sesión")
    with col2: _kpi("Recuper.",   str(int(last["RECUP. PELOTA"])),  "última sesión", "")
    with col3: _kpi("Pérdidas",   str(int(last["PÉRD. PELOTA"])),   "última sesión", "coral")
    with col4: _kpi("% Duelos",   f"{last['% DUELOS (auto)']}%",    f"{int(last['DUELOS GANADOS'])}/{int(last['DUELOS TOTALES'])}", "gold")

    _section("Evolución técnica", f"{len(df)} sesiones")
    col_a, col_b = st.columns(2)
    with col_a:
        fig1 = px.line(df, x="FECHA", y="% PASES (auto)", markers=True,
                       color_discrete_sequence=["#4ade80"], title="% pases correctos")
        fig1.update_traces(line=dict(width=2), marker=dict(size=5))
        fig1.add_hline(y=75, line_dash="dot", line_color="#4b5a4d",
                       annotation_text="objetivo 75%", annotation_font_color="#4b5a4d")
        fig1.update_layout(**{**_PLOTLY_LAYOUT, "height": 240,
                               "yaxis": dict(range=[0, 100], gridcolor="#1a1f1c"),
                               "title_font_color": "#6b7a6d", "title_font_size": 11})
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        fig2 = px.bar(df, x="FECHA", y=["RECUP. PELOTA", "PÉRD. PELOTA"],
                      barmode="group", title="Recuperaciones vs Pérdidas",
                      color_discrete_sequence=["#4ade80", "#f87171"])
        fig2.update_layout(**{**_PLOTLY_LAYOUT, "height": 240,
                               "legend": dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                               "title_font_color": "#6b7a6d", "title_font_size": 11})
        st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        fig3 = px.line(df, x="FECHA", y="% DUELOS (auto)", markers=True,
                       color_discrete_sequence=["#f59e0b"], title="% duelos ganados")
        fig3.update_traces(line=dict(width=2), marker=dict(size=5))
        fig3.update_layout(**{**_PLOTLY_LAYOUT, "height": 220,
                               "yaxis": dict(range=[0, 100], gridcolor="#1a1f1c"),
                               "title_font_color": "#6b7a6d", "title_font_size": 11})
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        fig4 = px.bar(df, x="FECHA", y="GOLES", title="Goles por sesión",
                      color_discrete_sequence=["#60a5fa"])
        fig4.update_layout(**{**_PLOTLY_LAYOUT, "height": 220,
                               "title_font_color": "#6b7a6d", "title_font_size": 11})
        st.plotly_chart(fig4, use_container_width=True)

    _section("Historial técnico")
    st.dataframe(
        df[["FECHA","TIPO SESIÓN","PASES INTENT.","PASES COMPLET.","% PASES (auto)",
            "RECUP. PELOTA","PÉRD. PELOTA","% DUELOS (auto)","GOLES","KM CON PELOTA"
            ]].sort_values("FECHA", ascending=False).reset_index(drop=True),
        use_container_width=True, height=280,
    )


def _tab_resumen(cp):
    df_j = cp.jugadores()
    df_f = cp.sesiones_fisico()
    df_t = cp.sesiones_tecnico()

    _section("Resumen del plantel")

    # Fila 1: KPIs globales
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: _kpi("Plantel", str(len(df_j)), "jugadores")
    with col2: _kpi("Activos", str(len(df_j[df_j["ESTADO"]=="Activo"])), "disponibles")
    with col3: _kpi("Sesiones físicas", str(len(df_f)), "en total")
    with col4: _kpi("Sesiones técnicas", str(len(df_t)), "en total")
    with col5:
        total_goles = int(df_t["GOLES"].sum()) if not df_t.empty else 0
        _kpi("Goles totales", str(total_goles), "todas las sesiones", "gold")

    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2)

    # Distribución posiciones
    with col_l:
        _section("Distribución por posición")
        pos_c = df_j["POSICIÓN"].value_counts().reset_index()
        pos_c.columns = ["Posición", "Cantidad"]
        colors = [_POS_COLORS.get(p, "#4b5a4d") for p in pos_c["Posición"]]
        fig_pos = go.Figure(go.Bar(
            x=pos_c["Posición"], y=pos_c["Cantidad"],
            marker_color=colors, marker_line_width=0,
            text=pos_c["Cantidad"], textposition="outside",
            textfont=dict(family="DM Mono", size=10, color="#6b7a6d"),
        ))
        fig_pos.update_layout(**{**_PLOTLY_LAYOUT, "height": 220,
                                  "yaxis": dict(gridcolor="#1a1f1c", range=[0, pos_c["Cantidad"].max()+2])})
        st.plotly_chart(fig_pos, use_container_width=True)

    # Promedio % pases por posición
    with col_r:
        if not df_t.empty and not df_j.empty:
            _section("% pases promedio por posición")
            df_merge = df_t.merge(df_j[["ID_JUGADOR","POSICIÓN"]], on="ID_JUGADOR", how="left")
            pos_pases = df_merge.groupby("POSICIÓN")["% PASES (auto)"].mean().reset_index()
            pos_pases.columns = ["Posición", "% Pases"]
            colors2 = [_POS_COLORS.get(p, "#4b5a4d") for p in pos_pases["Posición"]]
            fig_pp = go.Figure(go.Bar(
                x=pos_pases["Posición"], y=pos_pases["% Pases"].round(1),
                marker_color=colors2, marker_line_width=0,
                text=pos_pases["% Pases"].round(1), textposition="outside",
                textfont=dict(family="DM Mono", size=10, color="#6b7a6d"),
            ))
            fig_pp.update_layout(**{**_PLOTLY_LAYOUT, "height": 220,
                                     "yaxis": dict(gridcolor="#1a1f1c", range=[0, 105])})
            st.plotly_chart(fig_pp, use_container_width=True)

    # Ranking físico y técnico
    col_rf, col_rt = st.columns(2)

    with col_rf:
        _section("Ranking físico — Km promedio")
        if not df_f.empty:
            km_rank = df_f.groupby("ID_JUGADOR")["KM RECORRIDOS"].mean().reset_index()
            km_rank = km_rank.merge(df_j[["ID_JUGADOR","APELLIDO","NOMBRE"]], on="ID_JUGADOR", how="left")
            km_rank["Jugador"] = km_rank["APELLIDO"] + " " + km_rank["NOMBRE"]
            km_rank = km_rank.sort_values("KM RECORRIDOS", ascending=False).head(8)
            filas = ""
            for i, (_, r) in enumerate(km_rank.iterrows()):
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}"
                filas += f"""<tr>
                    <td style="color:#4b5a4d;font-family:'DM Mono',monospace;font-size:.75rem">{medal}</td>
                    <td style="font-weight:500;color:#e2e8df">{r['Jugador']}</td>
                    <td class="num" style="color:#4ade80;font-family:'DM Mono',monospace">
                        {r['KM RECORRIDOS']:.1f}</td>
                </tr>"""
            st.markdown(f"""<div style="background:#111412;border:1px solid #1e2420;border-radius:10px;overflow:hidden">
                <table class="plantel-table"><thead><tr><th>#</th><th>Jugador</th><th class="num">Km prom.</th></tr></thead>
                <tbody>{filas}</tbody></table></div>""", unsafe_allow_html=True)

    with col_rt:
        _section("Ranking técnico — % pases")
        if not df_t.empty:
            pases_rank = df_t.groupby("ID_JUGADOR")["% PASES (auto)"].mean().reset_index()
            pases_rank = pases_rank.merge(df_j[["ID_JUGADOR","APELLIDO","NOMBRE"]], on="ID_JUGADOR", how="left")
            pases_rank["Jugador"] = pases_rank["APELLIDO"] + " " + pases_rank["NOMBRE"]
            pases_rank = pases_rank.sort_values("% PASES (auto)", ascending=False).head(8)
            filas2 = ""
            for i, (_, r) in enumerate(pases_rank.iterrows()):
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}"
                pct = r["% PASES (auto)"]
                color = "#4ade80" if pct >= 75 else ("#f59e0b" if pct >= 60 else "#f87171")
                filas2 += f"""<tr>
                    <td style="color:#4b5a4d;font-family:'DM Mono',monospace;font-size:.75rem">{medal}</td>
                    <td style="font-weight:500;color:#e2e8df">{r['Jugador']}</td>
                    <td class="num" style="color:{color};font-family:'DM Mono',monospace">
                        {pct:.1f}%</td>
                </tr>"""
            st.markdown(f"""<div style="background:#111412;border:1px solid #1e2420;border-radius:10px;overflow:hidden">
                <table class="plantel-table"><thead><tr><th>#</th><th>Jugador</th><th class="num">% Pases</th></tr></thead>
                <tbody>{filas2}</tbody></table></div>""", unsafe_allow_html=True)


# ── Función principal exportable ──────────────────────────────────────────────

@st.cache_resource
def _get_conector():
    """Instancia el ConectorPlantel una sola vez por sesión de Streamlit."""
    try:
        from data.connector_plantel import ConectorPlantel
        return ConectorPlantel()
    except ImportError:
        # Fallback: usar datos demo directamente desde este módulo
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from data.connector_plantel import ConectorPlantel
        return ConectorPlantel()


def render_plantel():
    """
    Punto de entrada del módulo Plantel.
    Llamar desde app.py: render_plantel()
    """
    st.markdown(_CSS_PLANTEL, unsafe_allow_html=True)

    # Header
    cp = _get_conector()
    modo_badge_color = "#4ade80" if "Google" in cp.modo else "#f59e0b"
    st.markdown(f"""
    <div style="display:flex;align-items:baseline;justify-content:space-between;
                margin-bottom:1.5rem;flex-wrap:wrap;gap:8px">
        <div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:2.2rem;
                        font-weight:900;color:#fff;letter-spacing:.04em;line-height:1">
                GESTIÓN DE <span style="color:#4ade80">PLANTEL</span>
            </div>
            <div style="font-family:'DM Mono',monospace;font-size:.72rem;color:#4b5a4d;margin-top:.3rem">
                Rendimiento físico y técnico · seguimiento por jugador
            </div>
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:.65rem;
                    color:{modo_badge_color};background:{modo_badge_color}18;
                    padding:.3rem .8rem;border-radius:4px;border:1px solid {modo_badge_color}40">
            ● {cp.modo}
        </div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["👥 Jugadores", "💪 Físico", "⚽ Técnico", "📊 Resumen"])

    with tab1:
        _tab_jugadores(cp)
    with tab2:
        _tab_fisico(cp)
    with tab3:
        _tab_tecnico(cp)
    with tab4:
        _tab_resumen(cp)
