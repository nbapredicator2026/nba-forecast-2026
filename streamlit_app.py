import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_nba_data(p_id):
    # Médias da Temporada
    base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
        player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
    ).get_data_frames()[0]
    
    # DESEMPENHO RECENTE (A Chave do Gráfico de Desempenho)
    log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
    media_recente = log['PTS'].head(5).mean()
    
    return {
        'stats': base[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
        'fase': media_recente
    }

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast")

# Sidebar para seleções
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
t_nome = st.sidebar.selectbox("Time", sorted(all_teams.keys()))
roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_nome]).get_data_frames()[0]
p_nome = st.sidebar.selectbox("Jogador", roster['PLAYER'].tolist())
p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
adv_nome = st.sidebar.selectbox("Adversário", sorted(all_teams.keys()))

data = get_nba_data(p_id)

if data:
    # 1. Cards com Indicador de Desempenho (Delta)
    diff = data['fase'] - data['stats']['PTS']
    st.subheader(f"📊 Real: {p_name}")
    c1, c2, c3 = st.columns(3)
    c1.metric("PTS (Média)", f"{data['stats']['PTS']:.1f}", delta=f"{diff:+.1f} Fase")
    c2.metric("AST", f"{data['stats']['AST']:.1f}")
    c3.metric("REB", f"{data['stats']['REB']:.1f}")

    # 2. Previsão e Veredito
    st.markdown("---")
    previsao = st.number_input("Sua Linha de Pontos", value=float(data['stats']['PTS']))

    if st.button("ANALISAR AGORA", use_container_width=True):
        # Gráfico Comparativo de Desempenho Estável
        df_viz = pd.DataFrame({
            'Valor': [data['stats']['PTS'], previsao, data['fase']],
            'Tipo': ['Média Anual', 'Sua Previsão', 'Desempenho (Últimos 5)']
        }).set_index('Tipo')
        st.bar_chart(df_viz)

        # Veredito Visual
        is_prov = previsao <= (data['stats']['PTS'] * 1.1)
        estilo = "provavel" if is_prov else "improvavel"
        txt = "Provável ✅" if is_prov else "Improvável ❌"
        st.markdown(f'<div class="status-card {estilo}">PONTOS: {txt}</div>', unsafe_allow_html=True)
