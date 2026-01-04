import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, playerdashboardbygeneralsplits, playergamelog)

# ==============================================================================
# CONFIGURAÇÃO INICIAL E CABEÇALHOS (ANTI-BLOQUEIO)
# ==============================================================================
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

# Headers para evitar timeout da NBA (Simula um navegador real)
custom_headers = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# CSS Visual
st.markdown("""
    <style>
    .stMetric { background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 10px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# Tente usar a temporada anterior se a atual estiver vazia ou instável
TEMPORADA_ATUAL = '2024-25' 

# ==============================================================================
# FUNÇÕES DE DADOS COM FEEDBACK
# ==============================================================================
@st.cache_data(ttl=3600)
def get_roster(team_id):
    """Busca o elenco do time com tratamento de erro."""
    try:
        # Passando headers (embora a lib gerencie, às vezes ajuda forçar via request se necessário, 
        # mas aqui vamos confiar no try/except padrão da lib com timeout implícito do Streamlit)
        roster = commonteamroster.CommonTeamRoster(
            team_id=team_id, 
            season=TEMPORADA_ATUAL
        ).get_data_frames()[0]
        return roster
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_player_stats(p_id):
    """Busca stats do jogador."""
    try:
        # 1. Stats Gerais
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, 
            per_mode_detailed='PerGame', 
            season=TEMPORADA_ATUAL
        ).get_data_frames()[0]

        if base.empty: return None

        # 2. Game Log (Últimos jogos)
        log = playergamelog.PlayerGameLog(
            player_id=p_id, 
            season=TEMPORADA_ATUAL
        ).get_data_frames()[0]
        
        media_recente = log['PTS'].head(5).mean() if not log.empty else 0.0
        
        return {
            'stats': base[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
            'fase': media_recente
        }
    except Exception:
        return None

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("🏀 NBA Intel Forecast")

# --- DEBUG: Verifica se o código chegou até aqui ---
st.write("🔄 Inicializando sistema...")

# 1. Carregar Times
try:
    nba_teams = teams.get_teams()
    all_teams = {t['full_name']: t['id'] for t in nba_teams}
    st.sidebar.header("Configuração")
    t_nome = st.sidebar.selectbox("Escolha o Time", sorted(all_teams.keys()))
except Exception as e:
    st.error(f"Erro ao carregar lista de times. Verifique sua internet. Erro: {e}")
    st.stop()

# 2. Carregar Elenco (Ponto Crítico de Travamento)
if t_nome:
    with st.spinner(f"Baixando elenco do {t_nome}..."):
        roster_df = get_roster(all_teams[t_nome])
        
    if roster_df is not None and not roster_df.empty:
        p_nome = st.sidebar.selectbox("Escolha o Jogador", roster_df['PLAYER'].tolist())
        p_id = roster_df[roster_df['PLAYER'] == p_nome]['PLAYER_ID'].values[0]
    else:
        st.sidebar.error("Elenco não encontrado ou API bloqueou a conexão.")
        st.stop()

# 3. Carregar Dados do Jogador
if 'p_id' in locals():
    st.subheader(f"Análise: {p_nome}")
    
    with st.spinner("Analisando estatísticas..."):
        data = get_player_stats(p_id)

    if data:
        # Exibe Interface
        diff = data['fase'] - data['stats']['PTS']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Média Pontos", f"{data['stats']['PTS']:.1f}", delta=f"{diff:+.1f} Fase Recente")
        c2.metric("Assistências", f"{data['stats']['AST']:.1f}")
        c3.metric("Rebotes", f"{data['stats']['REB']:.1f}")

        st.divider()
        
        # Área de Aposta
        previsao = st.number_input("Linha da Aposta (Pontos)", value=float(data['stats']['PTS']))
        
        if st.button("GERAR VEREDITO", use_container_width=True):
            # Gráfico
            df_viz = pd.DataFrame({
                'Métrica': ['Média Temp.', 'Sua Linha', 'Fase (L5)'],
                'Pontos': [data['stats']['PTS'], previsao, data['fase']]
            }).set_index('Métrica')
            
            st.bar_chart(df_viz, color=["#FF4B4B"])

            # Veredito
            is_prov = previsao <= (data['stats']['PTS'] * 1.1)
            classe = "provavel" if is_prov else "improvavel"
            msg = "Provável (OVER) ✅" if is_prov else "Arriscado (UNDER) ❌"
            
            st.markdown(f'<div class="status-card {classe}">{msg}</div>', unsafe_allow_html=True)
            
    else:
        st.warning(f"Sem dados para {p_nome} nesta temporada ({TEMPORADA_ATUAL}).")
