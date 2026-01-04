import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits, playergamelog

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel v3.8.5", page_icon="🏀", layout="centered")

# Estilo para os cards de veredito
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; }
    .alert-box { padding: 20px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE BUSCA ---
@st.cache_data(ttl=86400)
def get_all_teams():
    return {t['full_name']: t['id'] for t in teams.get_teams()}

@st.cache_data(ttl=3600)
def get_defense_rank():
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df['RANK'] = range(1, 31)
        return df
    except:
        return pd.DataFrame({'TEAM_NAME': [t['full_name'] for t in teams.get_teams()], 'RANK': [15]*30})

@st.cache_data(ttl=3600)
def get_player_stats(p_id):
    try:
        # Busca Temporada Atual
        df_s = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        if df_s.empty: return None, None
        s_stats = df_s[['PTS', 'AST', 'REB']].iloc[0].to_dict()
        
        # Busca Últimos 5 Jogos
        df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', last_n_games=5, season='2025-26').get_data_frames()[0]
        l5_stats = df_l5[['PTS', 'AST', 'REB']].iloc[0].to_dict() if not df_l5.empty else s_stats
        return s_stats, l5_stats
    except: return None, None

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast")

teams_dict = get_all_teams()

with st.sidebar:
    st.header("Configuração")
    sel_team = st.selectbox("Time do Jogador", sorted(teams_dict.keys()))
    
    # Carregamento seguro do elenco
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=teams_dict[sel_team], season='2025-26').get_data_frames()[0]
        sel_player = st.selectbox("Jogador", roster['PLAYER'].tolist())
        p_id = roster[roster['PLAYER'] == sel_player]['PLAYER_ID'].values[0]
    except:
        st.error("Erro ao carregar dados do time. Tente novamente.")
        st.stop()
        
    sel_adv = st.selectbox("Adversário (Defesa)", sorted(teams_dict.keys()))

# BLOCO DE SEGURANÇA: Só avança se a API responder
s_stats, l5_stats = get_player_stats(p_id)

if s_stats is None:
    st.warning(f"Sincronizando estatísticas de 2026 para {sel_player}... Por favor, aguarde.")
    st.info("Se este aviso persistir, o jogador pode não ter entrado em quadra nesta temporada ainda.")
else:
    # Mostra Métricas
    c1, c2 = st.columns(2)
    c1.metric("Média 25-26", f"{s_stats['PTS']:.1f} PTS")
    c2.metric("Últimos 5 Jogos", f"{l5_stats['PTS']:.1f} PTS")

    st.markdown("---")
    u_val = st.number_input("Previsão de PONTOS", value=float(s_stats['PTS']), step=0.5)

    if st.button("ANALISAR AGORA"):
        df_def = get_defense_rank()
        rank = df_def[df_def['TEAM_NAME'] == sel_adv]['RANK'].values[0]
        
        # Cálculo Ponderado com Bônus Agressivo
        base = (s_stats['PTS'] + l5_stats['PTS']) / 2
        fator = (rank - 15) * (0.020 if rank >= 20 else 0.012)
        expectativa = base * (1 + fator)
        
        # Alerta de Blowout
        if rank >= 25:
            st.error(f"⚠️ **Risco de Blowout:** A defesa do {sel_adv} é muito fraca (Rank {rank}).")
            expectativa *= 0.88

        # Veredito Final
        diff = (u_val - expectativa) / expectativa
        if diff <= 0.10: cor, txt, icon = "#D4EDDA", "PROVÁVEL", "✅"
        elif diff <= 0.25: cor, txt, icon = "#FFF3CD", "INCERTO", "⚠️"
        else: cor, txt, icon = "#F8D7DA", "IMPROVÁVEL", "❌"

        st.markdown(f"""
            <div class="alert-box" style="background-color:{cor};">
                <h3 style="margin:0;">{icon} {txt}</h3>
                <p style="margin:0;">Expectativa calculada: <b>{expectativa:.1f} pontos</b>.</p>
            </div>
            """, unsafe_allow_html=True)
