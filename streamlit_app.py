import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="NBA Intel v3.9", page_icon="🏀", layout="centered")

# CSS para esconder erros nativos e estilizar cards
st.markdown("""
    <style>
    .stAlert { border-radius: 10px; }
    .stMetric { background-color: #f8f9fb; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# --- CACHE DE DADOS (EFICIÊNCIA) ---
@st.cache_data(ttl=86400)
def get_teams_list():
    return {t['full_name']: t['id'] for t in teams.get_teams()}

@st.cache_data(ttl=3600)
def get_defense_rankings():
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df['RANK'] = range(1, 31)
        return df
    except:
        return pd.DataFrame({'TEAM_NAME': [t['full_name'] for t in teams.get_teams()], 'RANK': [15]*30})

# --- INTERFACE LATERAL ---
st.title("🏀 NBA Intel Forecast")
all_teams = get_teams_list()

with st.sidebar:
    st.header("Configuração")
    # Uso de chaves (keys) únicas para evitar conflitos de sessão
    team_player = st.selectbox("Time do Jogador", sorted(all_teams.keys()), key="team_p")
    
    # Carregamento do elenco com tratamento de erro silencioso
    try:
        roster_df = commonteamroster.CommonTeamRoster(team_id=all_teams[team_player], season='2025-26').get_data_frames()[0]
        player_list = roster_df['PLAYER'].tolist()
    except:
        player_list = []

    if not player_list:
        st.error("Conectando à API da NBA...")
        st.stop()

    selected_player = st.selectbox("Jogador", player_list, key="player_p")
    p_id = roster_df[roster_df['PLAYER'] == selected_player]['PLAYER_ID'].values[0]
    
    team_adv = st.selectbox("Adversário (Defesa)", sorted(all_teams.keys()), key="team_a")

# --- LÓGICA DE CARREGAMENTO SEGURO ---
# O segredo da v3.9: Verificar dados antes de qualquer tentativa de renderização
@st.cache_data(ttl=3600)
def fetch_secure_stats(player_id):
    try:
        # Busca temporada
        s_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        if s_df.empty: return None
        
        # Busca L5
        l5_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5, season='2025-26').get_data_frames()[0]
        
        stats = {
            'season': s_df[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
            'l5': l5_df[['PTS', 'AST', 'REB']].iloc[0].to_dict() if not l5_df.empty else s_df[['PTS', 'AST', 'REB']].iloc[0].to_dict()
        }
        return stats
    except:
        return None

# Execução da busca
with st.spinner(f"Sincronizando dados de {selected_player}..."):
    player_data = fetch_secure_stats(p_id)

if player_data is None:
    st.warning(f"⚠️ Aguardando dados de 2026 para {selected_player}. Se o jogador ainda não estreou na temporada, tente outro atleta.")
else:
    # --- RENDERIZAÇÃO DA INTERFACE (SÓ ACONTECE SE HOUVER DADOS) ---
    s = player_data['season']
    l5 = player_data['l5']
    
    col1, col2 = st.columns(2)
    col1.metric("Média Temporada", f"{s['PTS']:.1f} PTS")
    col2.metric("Últimos 5 Jogos", f"{l5['PTS']:.1f} PTS", delta=f"{l5['PTS'] - s['PTS']:.1f}")

    st.markdown("---")
    user_val = st.number_input("Sua Previsão (PONTOS)", value=float(s['PTS']), step=0.5)

    if st.button("ANALISAR AGORA"):
        def_df = get_defense_rankings()
        rank = def_df[def_df['TEAM_NAME'] == team_adv]['RANK'].values[0]
        
        # Cálculo de Expectativa
        base = (s['PTS'] + l5['PTS']) / 2
        bonus = (rank - 15) * (0.02 if rank >= 20 else 0.012)
        expectativa = base * (1 + bonus)
        
        # Alerta de Blowout
        if rank >= 25:
            st.error(f"🚨 Risco de Blowout: Defesa do {team_adv} é muito fraca (Rank {rank}).")
            expectativa *= 0.88

        # Veredito
        diff = (user_val - expectativa) / expectativa
        if diff <= 0.10: st.success(f"✅ PROVÁVEL: Expectativa de {expectativa:.1f} PTS")
        elif diff <= 0.25: st.warning(f"⚠️ INCERTO: Expectativa de {expectativa:.1f} PTS")
        else: st.error(f"❌ IMPROVÁVEL: Expectativa de {expectativa:.1f} PTS")
