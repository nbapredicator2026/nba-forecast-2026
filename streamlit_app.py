import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits, playergamelog
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NBA Intel v3.8", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; height: 3em; background-color: #1f77b4; color: white; }
    .alert-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
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
        df_s = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame').get_data_frames()[0]
        if df_s.empty: return None, None
        season = df_s[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
        
        df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5).get_data_frames()[0]
        l5 = df_l5[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict() if not df_l5.empty else season
        return season, l5
    except: return None, None

@st.cache_data(ttl=3600)
def buscar_historico_direto(player_id, opponent_name):
    try:
        log = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26').get_data_frames()[0]
        opp_abbrev = teams.find_teams_by_full_name(opponent_name)[0]['abbreviation']
        confrontos = log[log['MATCHUP'].str.contains(opp_abbrev)]
        if not confrontos.empty:
            return {'media': confrontos['PTS'].mean(), 'jogos': len(confrontos)}
        return None
    except: return None

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast v3.8")

with st.sidebar:
    st.header("Configuração")
    dict_times = carregar_lista_times()
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    df_elenco = buscar_elenco(dict_times[time_nome])
    jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].
