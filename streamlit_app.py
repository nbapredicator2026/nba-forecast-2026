import streamlit as st
import pandas as pd
import plotly.express as px  # ESSENCIAL PARA O GRÁFICO DE DESEMPENHO
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="NBA Intel Elite v12", page_icon="📈", layout="centered")

# Estilo dos Cards de Veredito (baseado em suas imagens)
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
def obter_dados_completos(p_id):
    try:
        # Médias da Temporada
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=p_id, per_mode_detailed='PerGame', season='2025-26').get_data_frames()[0]
        # HISTÓRICO REAL PARA O GRÁFICO DE DESEMPENHO
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        trend_data = log[['GAME_DATE', 'PTS']].head(10)[::-1] # Últimos 10 jogos
        
        return {
            'medias': base[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(),
            'historico': trend_data
        }
    except: return None

# --- SIDEBAR ---
dict_times, db_liga = carregar_liga()
with st.sidebar:
    st.header("⚙️ Configuração")
    t_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    try:
        elenco = commonteamroster.CommonTeamRoster(team_id=dict_times[t_nome], season='2025-26').get_data_frames()[0]
        j_nome = st.selectbox("Jogador", elenco['PLAYER'].tolist())
        j_id = elenco[elenco['PLAYER'] == j_nome]['PLAYER_ID'].values[0]
    except: st.stop()
    adv_nome = st.selectbox("Adversário", sorted(dict_times.keys()))

# --- DASHBOARD PRINCIPAL ---
intel = obter_dados_completos(j_id)

if intel:
    st.subheader(f"📊 Real: {j_nome}")
    c1, c2, c3 = st.columns(3)
    c1.metric("PTS", f"{intel['medias']['PTS']:.1f}")
    c2.metric("AST", f"{intel['medias']['AST']:.1f}")
    c3.metric("REB", f"{intel['medias']['REB']:.1f}")

    # --- AQUI ESTÁ O GRÁFICO DE DESEMPENHO ---
    st.markdown("---")
    st.write(f"**📈 Gráfico de Desempenho: Pontos nos Últimos Jogos**")
    
    # Criando o gráfico de linha (Tendência)
    fig = px.line(intel['historico'], x='GAME_DATE', y='PTS', markers=True, 
                 color_discrete_sequence=['#007bff'], template="plotly_white")
    
    fig.update_layout(
        height=300, 
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Data do Jogo",
        yaxis_title="Pontos Marcados"
    )
    
    # Exibe o gráfico no Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # --- SEÇÃO DE PREVISÃO E VEREDITO ---
    st.markdown("---")
    st.subheader(f"🔮 Veredito vs {adv_nome}")
    p_user = st.number_input("Sua Linha de Pontos", value=float(intel['medias']['PTS']), step=0.5)

    if st.button("ANALISAR AGORA", use_container_width=True):
        info_adv = db_liga[db_liga['TEAM_NAME'] == adv_nome].iloc[0]
        rank = info_adv['DEF_RANK']
        
        # Lógica de Veredito Profissional
        expectativa = intel['medias']['PTS'] * (1 + (rank - 15) * 0.01)
        eh_provavel = p_user <= expectativa * 1.1
        
        classe = "provavel" if eh_provavel else "improvavel"
        status = "Provável ✅" if eh_provavel else "Improvável ❌"
        
        st.markdown(f"""<div class="status-card {classe}">PONTOS: {status}</div>""", unsafe_allow_html=True)
        st.info(f"💡 Dica: A defesa do {adv_nome} é Rank {rank} de 30.")

else:
    st.warning("Carregando histórico de desempenho...")
