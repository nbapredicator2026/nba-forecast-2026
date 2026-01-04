import streamlit as st
import pandas as pd
import plotly.express as px  # Para gráficos profissionais e leves
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- 1. CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(page_title="NBA Intel Elite v10", page_icon="📈", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-box { padding: 10px; border-radius: 8px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS PROFISSIONAL ---
@st.cache_data(ttl=86400)
def load_engine():
    all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'PACE', 'DEF_RATING']].sort_values('DEF_RATING')
        df['DEF_RANK'] = range(1, 31)
        return all_teams, df
    except: return all_teams, pd.DataFrame()

@st.cache_data(ttl=3600)
def get_player_full_intel(p_id):
    """Busca médias, avançados e histórico de jogos (Tendência)."""
    try:
        # Médias e Avançados
        adv = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', measure_type_detailed='Advanced', season='2025-26').get_data_frames()[0]
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        # Histórico para gráfico de tendência
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        
        return {
            'stats': {'pts': base['PTS'].iloc[0], 'ast': base['AST'].iloc[0], 'reb': base['REB'].iloc[0], 
                      'usg': adv['USG_PCT'].iloc[0] * 100, 'ts': adv['TS_PCT'].iloc[0] * 100},
            'trend': log[['GAME_DATE', 'PTS']].head(10)[::-1] # Últimos 10 jogos em ordem cronológica
        }
    except: return None

# --- 3. INTERFACE E CONTROLE ---
times, db_liga = load_engine()

with st.sidebar:
    st.header("🏆 Painel de Controle")
    t_sel = st.selectbox("Time", sorted(times.keys()), key="v10_t")
    try:
        elenco = commonteamroster.CommonTeamRoster(team_id=times[t_sel], season='2025-26').get_data_frames()[0]
        j_sel = st.selectbox("Jogador", elenco['PLAYER'].tolist(), key="v10_j")
        j_id = elenco[elenco['PLAYER'] == j_sel]['PLAYER_ID'].values[0]
    except: st.stop()
    adv_sel = st.selectbox("Adversário", sorted(times.keys()), key="v10_a")

# --- 4. DASHBOARD DE ELITE ---
intel = get_player_full_intel(j_id)

if intel:
    st.subheader(f"💎 Inteligência: {j_sel}")
    
    # Grid de Métricas (Inspirado na image_1dce67.png)
    c1, c2, c3 = st.columns(3)
    c1.metric("Média Temporada", f"{intel['stats']['pts']:.1f}")
    c2.metric("Usage (Volume)", f"{intel['stats']['usg']:.1f}%")
    c3.metric("Fase (Last 5)", f"{intel['trend']['PTS'].tail(5).mean():.1f}")

    # Gráfico de Tendência Histórica
    st.markdown("---")
    st.write("**📈 Tendência de Pontuação (Últimos 10 Jogos)**")
    fig = px.line(intel['trend'], x='GAME_DATE', y='PTS', markers=True, color_discrete_sequence=['#d4af37'])
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # Veredito e Matchup (Inspirado na image_1e4204.png)
    with st.expander("🛡️ Análise de Matchup e Valor", expanded=True):
        adv_info = db_liga[db_liga['TEAM_NAME'] == adv_sel].iloc[0]
        st.write(f"Defesa do {adv_sel}: **Rank {adv_info['DEF_RANK']} de 30**")
        
        linha = st.number_input("Linha de Pontos da Casa", value=float(intel['stats']['pts']), step=0.5)
        odd = st.number_input("Odd Oferecida", value=1.90)

        # Algoritmo Profissional v10
        base = (intel['stats']['pts'] * 0.6) + (intel['trend']['PTS'].tail(5).mean() * 0.4)
        ajuste = ((adv_info['DEF_RANK'] - 15) * 0.02) + ((adv_info['PACE'] - 100) * 0.01)
        expectativa = base * (1 + ajuste)
        
        diff = (linha - expectativa) / expectativa
        if diff <= 0.05:
            st.success(f"🔥 VALOR ALTO: Expectativa {expectativa:.1f} PTS")
        else:
            st.error(f"❄️ SEM VALOR: Expectativa {expectativa:.1f} PTS")
else:
    st.info("Sincronizando banco de dados de performance...")
