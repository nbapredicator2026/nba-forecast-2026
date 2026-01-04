import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits
import plotly.graph_objects as go

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel 3.6", page_icon="🏀", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    [data-testid="stMetric"] { background: #f0f2f6; padding: 10px; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; background-color: #1f77b4; color: white; }
    </style>
    """, unsafe_allow_html=True)

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
    # Stats da Temporada
    df_season = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame').get_data_frames()[0]
    season_stats = df_season[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
    
    # Stats Últimos 5 Jogos
    df_l5 = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame', last_n_games=5).get_data_frames()[0]
    l5_stats = df_l5[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict() if not df_l5.empty else season_stats
    
    return season_stats, l5_stats

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast v3.6")

with st.sidebar:
    st.header("Configuração")
    dict_times = carregar_lista_times()
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    df_elenco = buscar_elenco(dict_times[time_nome])
    jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].tolist())
    player_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
    adversario_nome = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()))

try:
    season_s, last5_s = buscar_stats_completas(player_id)
    df_def = obter_ranking_defensivo()
    rank_def_adv = df_def[df_def['TEAM_NAME'] == adversario_nome]['RANK'].values[0]

    st.subheader(f"📊 Desempenho: {jogador_nome}")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Média Temporada**")
        st.metric("PTS", f"{season_s['PTS']:.1f}")
    with col2:
        st.write("**Últimos 5 Jogos**")
        st.metric("PTS L5", f"{last5_s['PTS']:.1f}", delta=round(last5_s['PTS'] - season_s['PTS'], 1))

    st.markdown("---")
    cats = ['PTS', 'AST', 'REB', 'STL', 'BLK']
    labels = ['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS']
    u_vals = {cat: st.number_input(labels[i], value=float(season_s[cat]), step=0.5) for i, cat in enumerate(cats)}

    if st.button("ANALISAR AGORA"):
        # Gráfico comparando Temporada, L5 e Sua Previsão
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Temporada', x=labels, y=[season_s[c] for c in cats], marker_color='#1f77b4'))
        fig.add_trace(go.Bar(name='Últimos 5', x=labels, y=[last5_s[c] for c in cats], marker_color='#2ca02c'))
        fig.add_trace(go.Bar(name='Previsão', x=labels, y=[u_vals[c] for c in cats], marker_color='#ff7f0e'))
        
        fig.update_layout(barmode='group', height=350, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📈 Veredito (Com Fator Recência)")
        for i, cat in enumerate(cats):
            # O sistema agora usa a média entre a temporada e os últimos 5 para projetar
            tendencia = (season_s[cat] + last5_s[cat]) / 2
            exp = tendencia * (1 - (15 - rank_def_adv) * 0.012)
            diff = (u_vals[cat] - exp) / (exp if exp != 0 else 1)
            
            if diff <= 0.05: cor, txt = "#D4EDDA", "Provável ✅"
            elif diff <= 0.20: cor, txt = "#FFF3CD", "Incerto ⚠️"
            else: cor, txt = "#F8D7DA", "Improvável ❌"
            
            st.markdown(f"""<div style="background-color:{cor}; padding:15px; border-radius:12px; margin-bottom:10px; border-left: 5px solid gray">
                <b>{labels[i]}</b>: {txt} <br><small>Baseado na tendência atual de {tendencia:.1f}</small></div>""", unsafe_allow_html=True)

except Exception as e:
    st.info("Aguardando seleção do jogador...")
