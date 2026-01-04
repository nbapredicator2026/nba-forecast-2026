import streamlit as st
import pandas as pd
import plotly.express as px
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- 1. CONFIGURAÇÃO E ESTILO (MOBILE-FIRST) ---
st.set_page_config(page_title="NBA Intel Vegas v11", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 10px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS (CACHE DE ALTA PERFORMANCE) ---
@st.cache_data(ttl=86400)
def load_league_data():
    all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'PACE', 'DEF_RATING']].sort_values('DEF_RATING')
        df['DEF_RANK'] = range(1, 31)
        return all_teams, df
    except: return all_teams, pd.DataFrame()

@st.cache_data(ttl=3600)
def get_full_player_intel(p_id):
    try:
        # 1. Estatísticas Básicas e Avançadas (Usage Rate)
        adv = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', measure_type_detailed='Advanced', season='2025-26').get_data_frames()[0]
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        
        # 2. Log de Jogos para Gráfico de Tendência (Últimos 10)
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        trend = log[['GAME_DATE', 'PTS', 'AST', 'REB']].head(10)[::-1]
        
        return {
            'main': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(),
            'adv': {'usg': adv['USG_PCT'].iloc[0] * 100, 'ts': adv['TS_PCT'].iloc[0] * 100},
            'trend': trend
        }
    except:
