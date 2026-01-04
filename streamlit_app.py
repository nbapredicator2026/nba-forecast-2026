import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- 1. CONFIGURAÇÃO VISUAL (IDENTICA ÀS SUAS IMAGENS) ---
st.set_page_config(page_title="NBA Intel Forecast", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS (RÁPIDO E LEVE) ---
@st.cache_data(ttl=3600)
def get_player_intel(p_id):
    try:
        # Médias da Temporada
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]
        
        # DESEMPENHO RECENTE: Média de pontos nos últimos 5 jogos
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        desempenho_recente = log['PTS'].head(5).mean()
        
        return {
            'stats': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(),
            'fase_pts': desempenho_recente
        }
    except: return None

# --- 3. INTERFACE DE SELEÇÃO (ESTRUTURA ATUAL) ---
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
with st.sidebar:
    st.header("Configuração")
    t_name = st.selectbox("Time do Jogador", sorted(all_teams.keys()))
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_name]).get_data_frames()[0]
        p_name = st.selectbox("Jogador", roster['PLAYER'].tolist())
        p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
    except: st.stop()
    adv_name = st.selectbox("Adversário", sorted(all_teams.keys()))

# --- 4. EXIBIÇÃO PROFISSIONAL ---
data = get_player_intel(p_id)

if data:
    st.subheader(f"📊 Real: {p_name}")
    
    # Cálculo da tendência (Fase vs Média)
    tendencia = data['fase_pts'] - data['stats']['PTS']
    
    c1, c2, c3 = st.columns(3)
    # Mostra a média e se a fase atual está acima (+) ou abaixo (-)
    c1.metric("PTS (Média)", f"{data['stats']['PTS']:.1f}", delta=f"{tendencia:+.1f} Fase Recente")
    c2.metric("AST", f"{data['stats']['AST']:.1f}")
    c3.metric("REB", f"{data['stats']['REB']:.1f}")

    st.markdown("---")
    st.subheader(f"🔮 Previsão vs {adv_name}")
    u_pts = st.number_input("Sua Linha de Pontos", value=float(data['stats']['PTS']), step=0.5)

    if st.button("ANALISAR AGORA", use_container_width=True):
        # Gráfico de Barras Estável (Mostrando Média, Sua Previsão e Desempenho Recente)
        # Isso substitui o gráfico de linha de forma eficiente
        df_viz = pd.DataFrame({
            'Valor': [data['stats']['PTS'], u_pts, data['fase_pts']],
            'Tipo': ['Média Temporada', 'Sua Previsão', 'Desempenho (Últimos 5)']
        }).set_index('Tipo')
        
        st.bar_chart(df_viz)

        # Veredito por Atributo (Idêntico ao das suas fotos)
        st.subheader("📋 Veredito por Atributo")
        is_provavel = u_pts <= (data['stats']['PTS'] * 1.1)
        classe = "provavel" if is_provavel else "improvavel"
        msg = "Provável ✅" if is_provavel else "Improvável ❌"
        
        st.markdown(f"""<div class="status-card {classe}">PONTOS: {msg}</div>""", unsafe_allow_html=True)
        
        # Informação Extra de Qualidade
        st.info(f"💡 O jogador está em uma fase de {data['fase_pts']:.1f} pontos por jogo recentemente.")
