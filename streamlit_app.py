import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits
import plotly.graph_objects as go

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel 3.6.1", page_icon="🏀", layout="centered")

@st.cache_data(ttl=86400)
def carregar_lista_times():
    return {t['full_name']: t['id'] for t in teams.get_teams()}

@st.cache_data(ttl=3600)
def obter_ranking_defensivo():
    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df_def = team_stats[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df_def['RANK'] = range(1, 31)
        return df_def
    except:
        return pd.DataFrame({'TEAM_NAME': [t['full_name'] for t in teams.get_teams()], 'RANK': [15]*30})

@st.cache_data(ttl=7200)
def buscar_elenco(team_id):
    return commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26').get_data_frames()[0][['PLAYER', 'PLAYER_ID']]

@st.cache_data(ttl=3600)
def buscar_stats_completas(player_id):
    try:
        # Busca Temporada 2026
        df_season = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame').get_data_frames()[0]
        if df_season.empty: return None, None
        season_stats = df_season[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
        
        # Busca Últimos 5 Jogos (Onde o Banchero brilhou em 02/01/26)
        df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5).get_data_frames()[0]
        l5_stats = df_l5[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict() if not df_l5.empty else season_stats
        return season_stats, l5_stats
    except:
        return None, None

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast")

with st.sidebar:
    st.header("Configuração")
    dict_times = carregar_lista_times()
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    df_elenco = buscar_elenco(dict_times[time_nome])
    jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].tolist())
    player_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
    adversario_nome = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()))

season_s, last5_s = buscar_stats_completas(player_id)

if season_s is None:
    st.error(f"⚠️ Erro de sincronização com a API da NBA para {jogador_nome}. Tente recarregar a página ou escolher outro atleta.")
else:
    # Métricas de Topo
    col1, col2 = st.columns(2)
    with col1: st.metric("Média Temporada", f"{season_s['PTS']:.1f} PTS")
    with col2: st.metric("Últimos 5 Jogos", f"{last5_s['PTS']:.1f} PTS", delta=round(last5_s['PTS'] - season_s['PTS'], 1))

    # Inputs de Previsão
    st.markdown("---")
    cats = ['PTS', 'AST', 'REB']
    labels = ['PONTOS', 'ASSISTÊNCIAS', 'REBOUNDS']
    u_vals = {cat: st.number_input(labels[i], value=float(season_s[cat]), step=0.5) for i, cat in enumerate(cats)}

    if st.button("ANALISAR AGORA"):
        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Temporada', x=labels, y=[season_s[c] for c in cats], marker_color='#1f77b4'))
        fig.add_trace(go.Bar(name='Últimos 5', x=labels, y=[last5_s[c] for c in cats], marker_color='#2ca02c'))
        fig.update_layout(barmode='group', height=350, legend=dict(orientation="h", y=1.2))
        st.plotly_chart(fig, use_container_width=True)

        # Veredito Dinâmico
        for i, cat in enumerate(cats):
            tendencia = (season_s[cat] + last5_s[cat]) / 2
            if u_vals[cat] <= tendencia * 1.05: cor, txt = "#D4EDDA", "Provável ✅"
            else: cor, txt = "#F8D7DA", "Improvável ❌"
            st.markdown(f"<div style='background-color:{cor}; padding:15px; border-radius:10px; margin-bottom:5px'><b>{labels[i]}</b>: {txt}</div>", unsafe_allow_html=True)
