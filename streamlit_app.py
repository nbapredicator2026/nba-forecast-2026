import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- CONFIGURAÇÃO E ESTILO (ESTRUTURA ATUAL) ---
st.set_page_config(page_title="NBA Intel Forecast", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_intel_estavel(p_id):
    try:
        # 1. Médias da Temporada (Barra Azul)
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]
        
        # 2. DESEMPENHO REAL: Média dos últimos 5 jogos
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        fase_pts = log['PTS'].head(5).mean()
        fase_ast = log['AST'].head(5).mean()
        
        return {
            'stats': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(),
            'fase': {'pts': fase_pts, 'ast': fase_ast}
        }
    except: return None

# --- SIDEBAR ---
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
with st.sidebar:
    st.header("Configuração")
    t_nome = st.selectbox("Time do Jogador", sorted(all_teams.keys()))
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_nome]).get_data_frames()[0]
        p_nome = st.selectbox("Jogador", roster['PLAYER'].tolist())
        p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
    except: st.stop()
    adv_nome = st.selectbox("Adversário", sorted(all_teams.keys()))

# --- DASHBOARD DE ALTA EFICIÊNCIA ---
intel = get_intel_estavel(p_id)

if intel:
    st.subheader(f"📊 Real: {p_name}")
    
    # Cálculo de tendência para o indicador Delta
    d_pts = intel['fase']['pts'] - intel['stats']['PTS']
    d_ast = intel['fase']['ast'] - intel['stats']['AST']
    
    c1, c2, c3 = st.columns(3)
    # Mostra a média com o indicador de fase (seta verde/vermelha)
    c1.metric("PTS (Média)", f"{intel['stats']['PTS']:.1f}", delta=f"{d_pts:+.1f} Fase")
    c2.metric("AST (Média)", f"{intel['stats']['AST']:.1f}", delta=f"{d_ast:+.1f} Fase")
    c3.metric("REB", f"{intel['stats']['REB']:.1f}")

    st.markdown("---")
    st.subheader(f"🔮 Previsão vs {adv_name}")
    u_pts = st.number_input("Sua Linha de Pontos", value=float(intel['stats']['PTS']), step=0.5)

    if st.button("ANALISAR AGORA", use_container_width=True):
        # Gráfico de Barras Estável (Média vs Previsão como em image_1e4204.png)
        df_viz = pd.DataFrame({
            'Valor': [intel['stats']['PTS'], u_pts],
            'Tipo': ['Média Temporada', 'Sua Previsão']
        }).set_index('Tipo')
        st.bar_chart(df_viz)

        # Veredito Final (Mesmo visual da image_1e4204.png)
        st.subheader("📋 Veredito por Atributo")
        is_provavel = u_pts <= (intel['stats']['PTS'] * 1.1)
        classe = "provavel" if is_provavel else "improvavel"
        msg = "Provável ✅" if is_provavel else "Improvável ❌"
        
        st.markdown(f"""<div class="status-card {classe}">PONTOS: {msg}</div>""", unsafe_allow_html=True)
        
        # INFORMAÇÃO DE DESEMPENHO TEXTUAL (Alta Qualidade)
        st.info(f"💡 Info de Desempenho: {p_name} está com média de {intel['fase']['pts']:.1f} PTS nos últimos 5 jogos.")
