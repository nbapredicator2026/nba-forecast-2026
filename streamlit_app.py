import streamlit as st
import pandas as pd
import plotly.express as px
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel Elite v11", page_icon="🏀", layout="centered")

# Estilos para os Cards de Veredito (iguais às suas imagens)
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 10px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def load_data():
    all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'PACE', 'DEF_RATING']].sort_values('DEF_RATING')
        df['DEF_RANK'] = range(1, 31)
        return all_teams, df
    except: return all_teams, pd.DataFrame()

@st.cache_data(ttl=3600)
def get_intel(p_id):
    try:
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        # BUSCA O HISTÓRICO PARA O GRÁFICO DE DESEMPENHO
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        trend = log[['GAME_DATE', 'PTS']].head(10)[::-1]
        return {'main': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(), 'trend': trend}
    except: return None

# --- SIDEBAR ---
dict_teams, league_db = load_data()
with st.sidebar:
    st.header("⚙️ Configuração")
    t_player = st.selectbox("Time do Jogador", sorted(dict_teams.keys()))
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=dict_teams[t_player], season='2025-26').get_data_frames()[0]
        p_name = st.selectbox("Jogador", roster['PLAYER'].tolist())
        p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
    except: st.stop()
    t_adv = st.selectbox("Adversário", sorted(dict_teams.keys()))

# --- DASHBOARD ---
intel = get_intel(p_id)
if intel:
    st.subheader(f"📊 Real: {p_name}")
    col1, col2, col3 = st.columns(3)
    col1.metric("PTS", f"{intel['main']['PTS']:.1f}")
    col2.metric("AST", f"{intel['main']['AST']:.1f}")
    col3.metric("REB", f"{intel['main']['REB']:.1f}")

    # --- EXIBIÇÃO DO GRÁFICO DE DESEMPENHO (LINHA) ---
    st.markdown("---")
    st.write(f"**📈 Tendência de Pontuação (Últimos 10 Jogos)**")
    fig = px.line(intel['trend'], x='GAME_DATE', y='PTS', markers=True, color_discrete_sequence=['#007bff'])
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # SEÇÃO DE PREVISÃO
    st.markdown("---")
    u_pts = st.number_input("Sua Previsão de PONTOS", value=float(intel['main']['PTS']))
    
    if st.button("ANALISAR AGORA", use_container_width=True):
        adv_info = league_db[league_db['TEAM_NAME'] == t_adv].iloc[0]
        st.subheader("📋 Veredito Final")
        
        # Lógica Profissional: Compara previsão com média ajustada pela defesa
        expectativa = intel['main']['PTS'] * (1 + (adv_info['DEF_RANK'] - 15) * 0.01)
        estilo = "provavel" if u_pts <= expectativa * 1.1 else "improvavel"
        msg = "Provável ✅" if u_pts <= expectativa * 1.1 else "Improvável ❌"
        
        st.markdown(f"""<div class="status-card {estilo}">PONTOS: {msg}</div>""", unsafe_allow_html=True)
        st.info(f"💡 Defesa do {t_adv} é Rank {adv_info['DEF_RANK']}/30.")
