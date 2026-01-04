import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits, playergamelog
import plotly.graph_objects as go
import time

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel v3.8.2", page_icon="🏀", layout="centered")

# Estilo CSS
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; }
    .alert-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=86400)
def carregar_lista_times():
    return {t['full_name']: t['id'] for t in teams.get_teams()}

@st.cache_data(ttl=3600)
def obter_ranking_defensivo():
    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df_def = team_stats[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df_def['RANK'] = range(1, 31)
        return df_def
    except:
        return pd.DataFrame({'TEAM_NAME': [t['full_name'] for t in teams.get_teams()], 'RANK': [15]*30})

@st.cache_data(ttl=7200)
def buscar_elenco(team_id):
    try:
        df = commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26').get_data_frames()[0]
        return df[['PLAYER', 'PLAYER_ID']]
    except Exception as e:
        return pd.DataFrame(columns=['PLAYER', 'PLAYER_ID'])

@st.cache_data(ttl=3600)
def buscar_stats_completas(player_id):
    try:
        # Busca temporada regular
        df_s = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        if df_s.empty: return None, None
        season = df_s[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
        
        # Busca últimos 5 jogos
        df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5, season='2025-26').get_data_frames()[0]
        l5 = df_l5[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict() if not df_l5.empty else season
        return season, l5
    except:
        return None, None

@st.cache_data(ttl=3600)
def buscar_historico_direto(player_id, opponent_name):
    try:
        log = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26').get_data_frames()[0]
        opp_team = teams.find_teams_by_full_name(opponent_name)[0]
        opp_abbrev = opp_team['abbreviation']
        confrontos = log[log['MATCHUP'].str.contains(opp_abbrev)]
        if not confrontos.empty:
            return {'media': confrontos['PTS'].mean(), 'jogos': len(confrontos)}
        return None
    except:
        return None

# --- UI PRINCIPAL ---
st.title("🏀 NBA Intel Forecast")

dict_times = carregar_lista_times()

with st.sidebar:
    st.header("Configuração")
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()), key='time_sel')
    
    # Carregamento do Elenco com trava de segurança
    df_elenco = buscar_elenco(dict_times[time_nome])
    
    if df_elenco.empty:
        st.error("Erro ao carregar elenco. Tente novamente.")
        st.stop()
    
    jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].tolist(), key='player_sel')
    p_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
    
    adversario_nome = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()), key='adv_sel')

# Só executa a análise se o jogador estiver corretamente selecionado
if p_id:
    s_stats, l5_stats = buscar_stats_completas(p_id)
    
    if s_stats is None:
        st.warning(f"A API da NBA ainda não tem dados de 2026 para {jogador_nome}. Tente outro jogador.")
        st.stop()

    df_def = obter_ranking_defensivo()
    rank_def = df_def[df_def['TEAM_NAME'] == adversario_nome]['RANK'].values[0]
    hist = buscar_historico_direto(p_id, adversario_nome)

    # Métricas de topo
    c1, c2 = st.columns(2)
    c1.metric("Média Temporada", f"{s_stats['PTS']:.1f} PTS")
    c2.metric("Últimos 5 Jogos", f"{l5_stats['PTS']:.1f} PTS")

    if hist:
        st.info(f"🏟️ **Histórico Direto:** Média de {hist['media']:.1f} PTS contra o {adversario_nome}.")

    u_pts = st.number_input("Sua Previsão de PONTOS", value=float(s_stats['PTS']), step=0.5)

    if st.button("ANALISAR AGORA"):
        # Lógica de cálculo
        base = (s_stats['PTS'] * 0.4) + (l5_stats['PTS'] * 0.4)
        if hist: base += (hist['media'] * 0.2)
        else: base = (s_stats['PTS'] + l5_stats['PTS']) / 2

        fator = (rank_def - 15) * (0.020 if rank_def >= 20 else 0.012)
        expectativa = base * (1 + fator)

        # Risco de Blowout
        if rank_def >= 25:
            st.error("⚠️ **ALERTA DE BLOWOUT:** Risco de redução de minutos.")
            expectativa = expectativa * 0.88

        # Veredito
        diff = (u_pts - expectativa) / expectativa
        if diff <= 0.10: cor, txt, icon = "#D4EDDA", "PROVÁVEL", "✅"
        elif diff <= 0.25: cor, txt, icon = "#FFF3CD", "INCERTO", "⚠️"
        else: cor, txt, icon = "#F8D7DA", "IMPROVÁVEL", "❌"

        st.markdown(f'<div class="alert-box" style="background-color:{cor};"><h3>{icon} {txt}</h3>Expectativa: {expectativa:.1f} PTS</div>', unsafe_allow_html=True)
