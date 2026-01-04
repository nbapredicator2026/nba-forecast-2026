import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits

# --- CONFIGURAÇÃO ULTRA-LEVE ---
st.set_page_config(page_title="NBA Intel Turbo", page_icon="⚡", layout="centered")

# CSS para esconder erros e otimizar mobile
st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fb; border-radius: 12px; padding: 10px; border: 1px solid #eef0f2; }
    .stAlert { border-radius: 12px; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CAMADA 1: CACHE DE DADOS (SERVIDOR) ---
@st.cache_data(ttl=86400)
def get_base_data():
    """Carrega times e estatísticas avançadas da liga de uma vez só."""
    all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
    try:
        # Busca estatísticas de ritmo (Pace) e defesa
        league_stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced', season='2025-26').get_data_frames()[0]
        league_stats = league_stats[['TEAM_NAME', 'PACE', 'DEF_RATING']].sort_values('DEF_RATING')
        league_stats['DEF_RANK'] = range(1, 31)
        return all_teams, league_stats
    except:
        return all_teams, pd.DataFrame()

# --- CAMADA 2: PROCESSAMENTO ANALÍTICO ---
@st.cache_data(ttl=3600)
def analyze_player_pro(p_id):
    """Calcula Usage Rate e tendências sem pesar no celular."""
    try:
        # Busca dados avançados do jogador
        adv_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', measure_type_detailed='Advanced', season='2025-26'
        ).get_data_frames()[0]
        
        # Busca dados básicos (PTS, AST, REB)
        base_df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]

        if adv_df.empty or base_df.empty: return None

        return {
            'pts': base_df['PTS'].iloc[0],
            'ast': base_df['AST'].iloc[0],
            'reb': base_df['REB'].iloc[0],
            'usage': adv_df['USG_PCT'].iloc[0] * 100, # % de jogadas que passam por ele
            'ts_pct': adv_df['TS_PCT'].iloc[0] * 100  # Eficiência real de arremesso
        }
    except: return None

# --- INTERFACE DE DECISÃO ---
all_teams, league_data = get_base_data()

with st.sidebar:
    st.header("⚡ Configuração")
    t_sel = st.selectbox("Time", sorted(all_teams.keys()), key="t_s")
    
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_sel], season='2025-26').get_data_frames()[0]
        p_sel = st.selectbox("Jogador", roster['PLAYER'].tolist(), key="p_s")
        p_id = roster[roster['PLAYER'] == p_sel]['PLAYER_ID'].values[0]
    except:
        st.stop()
    
    adv_sel = st.selectbox("Adversário", sorted(all_teams.keys()), key="a_s")

# --- EXECUÇÃO DO MOTOR DE PREVISÃO ---
p_stats = analyze_player_pro(p_id)

if p_stats:
    # Painel de Métricas Avançadas
    st.subheader(f"📊 Intel: {p_sel}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Média PTS", f"{p_stats['pts']:.1f}")
    c2.metric("Usage Rate", f"{p_stats['usage']:.1f}%")
    c3.metric("Eficiência", f"{p_stats['ts_pct']:.1f}%")

    st.markdown("---")
    u_pts = st.number_input("Sua Linha de Pontos", value=float(p_stats['pts']), step=0.5)

    if st.button("ANALISAR AGORA (PRO)"):
        if not league_data.empty:
            adv_info = league_data[league_data['TEAM_NAME'] == adv_sel].iloc[0]
            
            # ALGORITMO PREDITIVO v8.0
            # 1. Base pela média e importância (Usage)
            expectativa = p_stats['pts'] * (1 + (p_stats['usage'] - 20) / 100)
            
            # 2. Ajuste por Ritmo (Pace) - Jogos rápidos geram mais pontos
            pace_factor = (adv_info['PACE'] - 100) / 100
            expectativa *= (1 + pace_factor)
            
            # 3. Ajuste por Defesa (Rank)
            def_bonus = (adv_info['DEF_RANK'] - 15) * 0.015
            expectativa *= (1 + def_bonus)

            # Resultado
            diff = (u_pts - expectativa) / expectativa
            if diff <= 0.08: st.success(f"✅ ALTA CONFIANÇA: {expectativa:.1f} PTS")
            elif diff <= 0.18: st.warning(f"⚠️ MÉDIA CONFIANÇA: {expectativa:.1f} PTS")
            else: st.error(f"❌ BAIXA CONFIANÇA: {expectativa:.1f} PTS")
            
            st.caption(f"Ajustes: Ritmo ({pace_factor*100:+.1f}%) | Defesa ({def_bonus*100:+.1f}%) | Usage (Incluso)")
else:
    st.info("Sincronizando estatísticas avançadas...")
