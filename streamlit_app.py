import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel Forecast", page_icon="🏀", layout="centered")

# Mantendo o estilo visual das suas imagens
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_player_performance(p_id):
    """Busca médias e calcula a tendência de desempenho recente."""
    try:
        # Médias da Temporada
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]
        
        # Histórico Recente (Últimos 5 jogos) para medir o desempenho atual
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        fase_atual = log['PTS'].head(5).mean()
        
        return {
            'stats': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(),
            'tendencia_pts': fase_atual
        }
    except: return None

# --- SIDEBAR (ESTRUTURA ATUAL MANTIDA) ---
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
with st.sidebar:
    st.header("Configuração")
    t_name = st.selectbox("Time do Jogador", sorted(all_teams.keys()))
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_name]).get_data_frames()[0]
        p_name = st.selectbox("Jogador", roster['PLAYER'].tolist())
        p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
    except: st.stop()
    adv_name = st.selectbox("Adversário (Defesa)", sorted(all_teams.keys()))

# --- DASHBOARD (QUALIDADE E EFICIÊNCIA) ---
data = get_player_performance(p_id)

if data:
    st.subheader(f"📊 Real: {p_name}")
    
    # Adicionando a Informação de Desempenho (Delta) nas métricas que você já tem
    # Isso mostra se o jogador está produzindo MAIS ou MENOS que a média nos últimos jogos
    diff = data['tendencia_pts'] - data['stats']['PTS']
    
    c1, c2, c3 = st.columns(3)
    c1.metric("PTS (Média)", f"{data['stats']['PTS']:.1f}", delta=f"{diff:+.1f} (Fase)")
    c2.metric("AST", f"{data['stats']['AST']:.1f}")
    c3.metric("REB", f"{data['stats']['REB']:.1f}")

    st.markdown("---")
    st.subheader(f"🔮 Previsão vs {adv_name}")
    u_pts = st.number_input("Sua Linha de Pontos", value=float(data['stats']['PTS']), step=0.5)

    if st.button("ANALISAR AGORA", use_container_width=True):
        # Gráfico de Barras que você já utiliza (Eficiente e Estável)
        df_viz = pd.DataFrame({
            'Valor': [data['stats']['PTS'], u_pts, data['tendencia_pts']],
            'Tipo': ['Média Temporada', 'Sua Previsão', 'Fase (Últimos 5)']
        }).set_index('Tipo')
        
        st.bar_chart(df_viz)

        # Seção de Veredito (Identica às suas imagens)
        st.subheader("📋 Veredito por Atributo")
        is_provavel = u_pts <= (data['stats']['PTS'] * 1.1)
        classe = "provavel" if is_provavel else "improvavel"
        msg = "Provável ✅" if is_provavel else "Improvável ❌"
        
        st.markdown(f"""<div class="status-card {classe}">PONTOS: {msg}</div>""", unsafe_allow_html=True)
        st.caption(f"Nota: O jogador está com média de {data['tendencia_pts']:.1f} pontos nos últimos 5 jogos.")
