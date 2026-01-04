import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits, playergamelog
import plotly.graph_objects as go

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel 3.7", page_icon="🏀", layout="centered")

@st.cache_data(ttl=3600)
def buscar_historico_confronto(player_id, opponent_team_id):
    try:
        log = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26').get_data_frames()[0]
        # Filtra jogos contra o ID do adversário
        matchup_games = log[log['VIDEO_AVAILABLE'] >= 0] # Apenas para garantir que o log existe
        # Na NBA API, o confronto direto é identificado pela string 'Matchup' ou filtrando pelo time adversário
        # Vamos buscar os jogos onde o ID do time adversário aparece
        confrontos = log[log['MATCHUP'].str.contains(teams.find_team_name_by_id(opponent_team_id)['abbreviation'])]
        
        if not confrontos.empty:
            return {
                'media_pts': confrontos['PTS'].mean(),
                'max_pts': confrontos['PTS'].max(),
                'jogos': len(confrontos)
            }
        return None
    except:
        return None

# [Mantendo as funções carregar_lista_times, obter_ranking_defensivo, buscar_elenco da v3.6.1]
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
    return commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26').get_data_frames()[0][['PLAYER', 'PLAYER_ID']]

@st.cache_data(ttl=3600)
def buscar_stats_completas(player_id):
    try:
        df_season = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame').get_data_frames()[0]
        season_stats = df_season[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
        df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5).get_data_frames()[0]
        l5_stats = df_l5[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict() if not df_l5.empty else season_stats
        return season_stats, l5_stats
    except: return None, None

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast v3.7")

with st.sidebar:
    st.header("Configuração")
    dict_times = carregar_lista_times()
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    df_elenco = buscar_elenco(dict_times[time_nome])
    jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].tolist())
    player_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
    adversario_nome = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()))
    opp_id = dict_times[adversario_nome]

stats_s, stats_l5 = buscar_stats_completas(player_id)
hist = buscar_historico_confronto(player_id, opp_id)

if stats_s:
    st.subheader(f"🏟️ Histórico vs {adversario_nome}")
    if hist:
        c1, c2, c3 = st.columns(3)
        c1.metric("Média no Duelo", f"{hist['media_pts']:.1f} PTS")
        c2.metric("Melhor Marca", f"{hist['max_pts']} PTS")
        c3.metric("Jogos Realizados", hist['jogos'])
    else:
        st.info(f"Primeiro confronto entre {jogador_nome} e {adversario_nome} nesta temporada.")

    st.markdown("---")
    # [Gráficos e lógica de Veredito da v3.6.1 ajustada para considerar hist['media_pts'] se existir]
    u_pts = st.number_input("Sua Previsão de PONTOS", value=float(stats_s['PTS']))
    
    if st.button("ANALISAR AGORA"):
        # Lógica de Peso: 40% Temporada, 40% Recência, 20% Histórico Direto
        base = (stats_s['PTS'] * 0.4) + (stats_l5['PTS'] * 0.4)
        if hist: base += (hist['media_pts'] * 0.2)
        else: base = (stats_s['PTS'] + stats_l5['PTS']) / 2
        
        # Ajuste de Defesa
        rank_def = obter_ranking_defensivo()[obter_ranking_defensivo()['TEAM_NAME'] == adversario_nome]['RANK'].values[0]
        expectativa = base * (1 - (15 - rank_def) * 0.012)
        
        diff = (u_pts - expectativa) / expectativa
        if diff <= 0.05: st.success(f"✅ PROVÁVEL: {jogador_nome} tem histórico e fase para cumprir.")
        elif diff <= 0.20: st.warning(f"⚠️ INCERTO: A previsão está acima da tendência de {expectativa:.1f}.")
        else: st.error(f"❌ IMPROVÁVEL: Muito acima do esperado contra esta defesa.")
