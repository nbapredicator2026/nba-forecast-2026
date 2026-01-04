import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel Pro v5.0", page_icon="🏀", layout="centered")

# CSS para esconder erros nativos e polir a interface
st.markdown("<style>.stError, .stException {display: none;} .stMetric {border: 1px solid #eee; padding: 10px; border-radius: 8px;}</style>", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE ESTADO (O SEGREDO DA ESTABILIDADE) ---
if 'data_ready' not in st.session_state:
    st.session_state.data_ready = False

# --- FUNÇÕES NATIVAS ---
@st.cache_data(ttl=86400)
def load_teams():
    return {t['full_name']: t['id'] for t in teams.get_teams()}

@st.cache_data(ttl=3600)
def get_ranks():
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df['RANK'] = range(1, 31)
        return df
    except: return pd.DataFrame()

# --- SIDEBAR COM VALIDAÇÃO ---
st.title("🏀 NBA Intel Forecast")
all_teams = load_teams()

with st.sidebar:
    st.header("Configuração")
    t_player = st.selectbox("Time do Jogador", sorted(all_teams.keys()), key="tp")
    
    # Carregamento seguro de elenco
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_player], season='2025-26').get_data_frames()[0]
        p_list = roster['PLAYER'].tolist()
    except:
        p_list = []

    if not p_list:
        st.info("🔄 Sincronizando elenco da NBA...")
        st.stop()

    sel_p = st.selectbox("Jogador", p_list, key="pp")
    p_id = roster[roster['PLAYER'] == sel_p]['PLAYER_ID'].values[0]
    t_adv = st.selectbox("Adversário (Defesa)", sorted(all_teams.keys()), key="ta")

# --- PROCESSAMENTO BLINDADO ---
@st.cache_data(ttl=3600)
def fetch_all(pid):
    try:
        s_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=pid, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        l5_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=pid, per_mode_detailed='PerGame', last_n_games=5, season='2025-26').get_data_frames()[0]
        if s_df.empty: return None
        return {
            's': s_df[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
            'l5': l5_df[['PTS', 'AST', 'REB']].iloc[0].to_dict() if not l5_df.empty else s_df[['PTS', 'AST', 'REB']].iloc[0].to_dict()
        }
    except: return None

# Tenta buscar os dados
data = fetch_all(p_id)

if data:
    st.session_state.data_ready = True
    # Mostra médias reais (vistas na image_0f3b03.png)
    c1, c2, c3 = st.columns(3)
    c1.metric("PTS", f"{data['s']['PTS']:.1f}")
    c2.metric("AST", f"{data['s']['AST']:.1f}")
    c3.metric("REB", f"{data['s']['REB']:.1f}")

    st.markdown("---")
    u_pts = st.number_input("Sua Previsão (PONTOS)", value=float(data['s']['PTS']), step=0.5)

    if st.button("ANALISAR AGORA"):
        ranks = get_ranks()
        if not ranks.empty:
            r = ranks[ranks['TEAM_NAME'] == t_adv]['RANK'].values[0]
            # Lógica de expectativa ajustada
            base = (data['s']['PTS'] * 0.5) + (data['l5']['PTS'] * 0.5)
            mod = (r - 15) * (0.02 if r >= 20 else 0.01)
            expect = base * (1 + mod)
            
            # Alerta de Blowout (Defesas Ranks 25-30)
            if r >= 25:
                st.warning(f"🚨 Risco de Blowout (Defesa Rank {r})")
                expect *= 0.90

            diff = (u_pts - expect) / expect
            if diff <= 0.10: st.success(f"✅ PROVÁVEL: {expect:.1f} PTS")
            elif diff <= 0.25: st.warning(f"⚠️ INCERTO: {expect:.1f} PTS")
            else: st.error(f"❌ IMPROVÁVEL: {expect:.1f} PTS")
else:
    st.session_state.data_ready = False
    st.warning(f"⏳ Aguardando estatísticas estáveis para {sel_p}...")
