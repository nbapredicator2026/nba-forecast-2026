import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="NBA Intel Forecast v16", layout="centered")

# Estilos dos Cards (Baseado em image_1e4204.png)
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BUSCA DE DADOS COM TRATAMENTO DE ERROS ---
@st.cache_data(ttl=3600)
def get_full_intel(p_id):
    try:
        # Médias da Temporada
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]
        
        # INFO DE DESEMPENHO (Histórico Recente)
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        fase_pts = log['PTS'].head(5).mean()
        
        return {
            'stats': base[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
            'fase': fase_pts
        }
    except Exception as e:
        return f"Erro ao buscar dados: {e}"

# --- 3. INTERFACE (SIDEBAR) ---
st.sidebar.header("Configuração")
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
t_nome = st.sidebar.selectbox("Escolha o Time", sorted(all_teams.keys()))

try:
    # Busca o elenco do time selecionado
    roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_nome]).get_data_frames()[0]
    p_nome = st.sidebar.selectbox("Escolha o Jogador", roster['PLAYER'].tolist())
    p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
except:
    st.error("Não foi possível carregar a lista de jogadores deste time.")
    st.stop()

adv_nome = st.sidebar.selectbox("Adversário", sorted(all_teams.keys()))

# --- 4. EXIBIÇÃO ---
intel = get_full_intel(p_id)

if isinstance(intel, dict):
    st.subheader(f"📊 Real: {p_nome}")
    diff = intel['fase'] - intel['stats']['PTS']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("PTS (Média)", f"{intel['stats']['PTS']:.1f}", delta=f"{diff:+.1f} Fase")
    col2.metric("AST", f"{intel['stats']['AST']:.1f}")
    col3.metric("REB", f"{intel['stats']['REB']:.1f}")

    st.markdown("---")
    u_pts = st.number_input("Sua Linha de Pontos", value=float(intel['stats']['PTS']))

    if st.button("ANALISAR AGORA", use_container_width=True):
        # Gráfico Comparativo de Desempenho (Estável)
        df_viz = pd.DataFrame({
            'Valor': [intel['stats']['PTS'], u_pts, intel['fase']],
            'Tipo': ['Média Anual', 'Sua Previsão', 'Fase Recente (5 J)']
        }).set_index('Tipo')
        st.bar_chart(df_viz)
        
        # Veredito (Igual image_1e4204.png)
        st.subheader("📋 Veredito Final")
        is_prov = u_pts <= (intel['stats']['PTS'] * 1.1)
        estilo = "provavel" if is_prov else "improvavel"
        txt = "Provável ✅" if is_prov else "Improvável ❌"
        st.markdown(f'<div class="status-card {estilo}">PONTOS: {txt}</div>', unsafe_allow_html=True)
else:
    st.warning("Aguardando resposta da NBA API... Tente selecionar o jogador novamente.")
