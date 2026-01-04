import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits, playergamelog
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NBA Intel v3.8", page_icon="🏀", layout="centered")

# CSS para interface moderna e responsiva
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; height: 3em; background-color: #1f77b4; color: white; }
    .alert-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS COM TRATAMENTO DE ERRO ---
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
        return commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26').get_data_frames()[0][['PLAYER', 'PLAYER_ID']]
    except:
        return pd.DataFrame(columns=['PLAYER', 'PLAYER_ID'])

@st.cache_data(ttl=3600)
def buscar_stats_completas(player_id):
    try:
        df_s = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame').get_data_frames()[0]
        if df_s.empty: return None, None
        season = df_s[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
        
        df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5).get_data_frames()[0]
        l5 = df_l5[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict() if not df_l5.empty else season
        return season, l5
    except: return None, None

@st.cache_data(ttl=3600)
def buscar_historico_direto(player_id, opponent_name):
    try:
        log = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26').get_data_frames()[0]
        opp_abbrev = teams.find_teams_by_full_name(opponent_name)[0]['abbreviation']
        confrontos = log[log['MATCHUP'].str.contains(opp_abbrev)]
        if not confrontos.empty:
            return {'media': confrontos['PTS'].mean(), 'jogos': len(confrontos)}
        return None
    except: return None

# --- INTERFACE PRINCIPAL ---
st.title("🏀 NBA Intel Forecast v3.8")

with st.sidebar:
    st.header("Configuração")
    dict_times = carregar_lista_times()
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    df_elenco = buscar_elenco(dict_times[time_nome])
    
    if not df_elenco.empty:
        jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].tolist())
        p_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
    else:
        st.error("Erro ao carregar elenco.")
        st.stop()
        
    adversario_nome = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()))

# Processamento de Dados
s_stats, l5_stats = buscar_stats_completas(p_id)
df_def = obter_ranking_defensivo()
rank_def = df_def[df_def['TEAM_NAME'] == adversario_nome]['RANK'].values[0]
hist = buscar_historico_direto(p_id, adversario_nome)

if s_stats:
    # Cabeçalho de Métricas
    col1, col2 = st.columns(2)
    with col1: st.metric("Média Temporada", f"{s_stats['PTS']:.1f} PTS")
    with col2: 
        diff_l5 = l5_stats['PTS'] - s_stats['PTS']
        st.metric("Últimos 5 Jogos", f"{l5_stats['PTS']:.1f} PTS", delta=f"{diff_l5:+.1f}")

    if hist:
        st.info(f"🏟️ **Histórico Direto:** {jogador_nome} tem média de {hist['media']:.1f} PTS contra o {adversario_nome}.")

    st.markdown("---")
    u_pts = st.number_input("Sua Previsão de PONTOS", value=float(s_stats['PTS']), step=0.5)

    if st.button("ANALISAR AGORA"):
        # 1. Base Ponderada (Temporada 40% / Recência 40% / Histórico 20%)
        base = (s_stats['PTS'] * 0.4) + (l5_stats['PTS'] * 0.4)
        if hist: base += (hist['media'] * 0.2)
        else: base = (s_stats['PTS'] + l5_stats['PTS']) / 2

        # 2. Ajuste Agressivo de Defesa (Rank 20+ ganha 2% de bônus por nível)
        fator = (rank_def - 15) * (0.020 if rank_def >= 20 else 0.012)
        expectativa = base * (1 + fator)

        # 3. Detector de Blowout (Rank 25+ dispara alerta)
        if rank_def >= 25:
            st.error("⚠️ **ALERTA DE BLOWOUT:** Defesa adversária muito frágil. Risco de redução de minutos no 4º quarto.")
            expectativa_segura = expectativa * 0.88
            st.info(f"💡 **Ajuste de Segurança:** Meta ideal de **{expectativa_segura:.1f} PTS**.")
            expectativa = expectativa_segura

        # 4. Veredito Visual
        diff = (u_pts - expectativa) / expectativa
        if diff <= 0.10:
            cor, txt, icon = "#D4EDDA", "PROVÁVEL", "✅"
        elif diff <= 0.25:
            cor, txt, icon = "#FFF3CD", "INCERTO", "⚠️"
        else:
            cor, txt, icon = "#F8D7DA", "IMPROVÁVEL", "❌"

        st.markdown(f"""
            <div class="alert-box" style="background-color:{cor}; border-color: gray;">
                <h3 style="margin:0;">{icon} {txt}</h3>
                <p style="margin:0;">A expectativa para este matchup é de <b>{expectativa:.1f} pontos</b>.</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.caption(f"Fator: Defesa do {adversario_nome} ocupa o Rank {rank_def} de 30.")
else:
    st.warning("Aguardando carregamento de dados da API da NBA...")
