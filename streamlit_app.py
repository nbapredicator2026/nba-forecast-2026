import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel v4.0", page_icon="🏀", layout="centered")

# CSS para esconder mensagens de erro nativas do Python
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} .stError {display: none;}</style>", unsafe_allow_html=True)

# --- FUNÇÕES COM PROTEÇÃO MÁXIMA ---
@st.cache_data(ttl=86400)
def get_all_teams():
    try:
        return {t['full_name']: t['id'] for t in teams.get_teams()}
    except: return {}

@st.cache_data(ttl=3600)
def get_defense_data():
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df['RANK'] = range(1, 31)
        return df
    except: return pd.DataFrame()

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast v4.0")

dict_times = get_all_teams()
if not dict_times:
    st.error("Erro de conexão com a NBA. Atualize a página.")
    st.stop()

with st.sidebar:
    st.header("Configuração")
    time_p = st.selectbox("Time do Jogador", sorted(dict_times.keys()), key="sb_time")
    
    # Carregamento do elenco protegido
    try:
        elenco = commonteamroster.CommonTeamRoster(team_id=dict_times[time_p], season='2025-26').get_data_frames()[0]
        lista_jogadores = elenco['PLAYER'].tolist()
    except:
        lista_jogadores = []

    if not lista_jogadores:
        st.info("Buscando jogadores...")
        st.stop()

    jogador_sel = st.selectbox("Jogador", lista_jogadores, key="sb_player")
    p_id = elenco[elenco['PLAYER'] == jogador_sel]['PLAYER_ID'].values[0]
    time_adv = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()), key="sb_adv")

# --- BUSCA DE ESTATÍSTICAS ---
@st.cache_data(ttl=3600)
def fetch_stats(pid):
    try:
        # Busca temporada regular
        s_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=pid, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        if s_df.empty: return None
        
        # Busca últimos 5 jogos
        l5_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=pid, per_mode_detailed='PerGame', last_n_games=5, season='2025-26').get_data_frames()[0]
        
        return {
            's': s_df[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
            'l5': l5_df[['PTS', 'AST', 'REB']].iloc[0].to_dict() if not l5_df.empty else s_df[['PTS', 'AST', 'REB']].iloc[0].to_dict()
        }
    except: return None

data = fetch_stats(p_id)

if data:
    # Mostra os cards de stats
    c1, c2 = st.columns(2)
    c1.metric("Temporada", f"{data['s']['PTS']:.1f} PTS")
    c2.metric("Últimos 5", f"{data['l5']['PTS']:.1f} PTS")

    st.markdown("---")
    user_val = st.number_input("Previsão de Pontos", value=float(data['s']['PTS']), step=0.5)

    if st.button("ANALISAR CONFRONTO"):
        df_def = get_defense_data()
        if not df_def.empty:
            rank = df_def[df_def['TEAM_NAME'] == time_adv]['RANK'].values[0]
            
            # Cálculo
            base = (data['s']['PTS'] + data['l5']['PTS']) / 2
            fator = (rank - 15) * (0.02 if rank >= 20 else 0.012)
            expectativa = base * (1 + fator)
            
            if rank >= 25:
                st.warning(f"🚨 Risco de Blowout (Rank {rank})")
                expectativa *= 0.88

            diff = (user_val - expectativa) / expectativa
            if diff <= 0.10: st.success(f"✅ PROVÁVEL: {expectativa:.1f} PTS")
            elif diff <= 0.25: st.warning(f"⚠️ INCERTO: {expectativa:.1f} PTS")
            else: st.error(f"❌ IMPROVÁVEL: {expectativa:.1f} PTS")
        else:
            st.warning("Dados defensivos indisponíveis no momento.")
else:
    st.warning(f"Sincronizando dados de {jogador_sel}... Se persistir, o jogador pode estar sem jogos em 2026.")
