import streamlit as st
import pandas as pd
import plotly.express as px
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Intel Elite v13", page_icon="🏀", layout="centered")

# Estilos dos Cards das suas imagens
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 12px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def carregar_liga():
    all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced', season='2025-26').get_data_frames()[0]
        df = df[['TEAM_NAME', 'PACE', 'DEF_RATING']].sort_values('DEF_RATING')
        df['DEF_RANK'] = range(1, 31)
        return all_teams, df
    except: return all_teams, pd.DataFrame()

@st.cache_data(ttl=3600)
def obter_intelecto(p_id):
    try:
        # Médias e histórico de jogos
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        # Pegamos os últimos 10 jogos para o gráfico de linha
        trend = log[['GAME_DATE', 'PTS']].head(10)[::-1]
        
        return {
            'medias': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(),
            'trend': trend
        }
    except: return None

# --- 2. SIDEBAR ---
times, db_liga = carregar_liga()
with st.sidebar:
    st.header("Configuração")
    t_sel = st.selectbox("Time", sorted(times.keys()))
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=times[t_sel], season='2025-26').get_data_frames()[0]
        p_sel = st.selectbox("Jogador", roster['PLAYER'].tolist())
        p_id = roster[roster['PLAYER'] == p_sel]['PLAYER_ID'].values[0]
    except: st.stop()
    adv_sel = st.selectbox("Adversário", sorted(times.keys()))

# --- 3. DASHBOARD ---
dados = obter_intelecto(p_id)

if dados:
    st.subheader(f"📊 Desempenho Real: {p_sel}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Média PTS", f"{dados['medias']['PTS']:.1f}")
    c2.metric("Média AST", f"{dados['medias']['AST']:.1f}")
    c3.metric("Média REB", f"{dados['medias']['REB']:.1f}")

    # --- NOVO: GRÁFICO DE DESEMPENHO (LINHA) ---
    st.markdown("---")
    st.write(f"**📈 Tendência de Pontos (Últimos 10 Jogos)**")
    
    # Este é o gráfico que estava faltando
    fig_linha = px.line(dados['trend'], x='GAME_DATE', y='PTS', markers=True, 
                       color_discrete_sequence=['#007bff'])
    fig_linha.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_linha, use_container_width=True)

    # --- SEÇÃO DE COMPARATIVO E VEREDITO ---
    st.markdown("---")
    st.subheader("🔮 Previsão e Análise")
    p_pts = st.number_input("Sua Linha de Pontos", value=float(dados['medias']['PTS']), step=0.5)

    if st.button("ANALISAR AGORA", use_container_width=True):
        adv_info = db_liga[db_liga['TEAM_NAME'] == adv_sel].iloc[0]
        
        # Gráfico Comparativo (Igual às suas imagens)
        df_comp = pd.DataFrame({
            'Categoria': ['PONTOS'],
            'Média': [dados['medias']['PTS']],
            'Previsão': [p_pts]
        }).set_index('Categoria')
        
        st.bar_chart(df_comp)

        # Veredito Final
        st.subheader("📋 Veredito por Atributo")
        expectativa = dados['medias']['PTS'] * (1 + (adv_info['DEF_RANK'] - 15) * 0.01)
        status = "Provável ✅" if p_pts <= expectativa * 1.1 else "Improvável ❌"
        classe = "provavel" if p_pts <= expectativa * 1.1 else "improvavel"
        
        st.markdown(f"""<div class="status-card {classe}">PONTOS: {status}</div>""", unsafe_allow_html=True)
        st.info(f"💡 Defesa do {adv_sel}: Rank {adv_info['DEF_RANK']} de 30.")
else:
    st.warning("Buscando dados históricos...")
