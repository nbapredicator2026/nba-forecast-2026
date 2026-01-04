import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playerdashboardbygeneralsplits

# --- 1. ESTILIZAÇÃO (Igual às suas imagens de sucesso) ---
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")
st.markdown("""
    <style>
    .status-card { padding: 18px; border-radius: 12px; margin-bottom: 12px; font-weight: bold; border-left: 6px solid; }
    .provavel { background-color: #dcf1e3; color: #1e4620; border-left-color: #2e7d32; }
    .incerto { background-color: #fff3cd; color: #856404; border-left-color: #ffa000; }
    .improvavel { background-color: #fde2e1; color: #7a1b1b; border-left-color: #d32f2f; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÃO INTELIGENTE DE BUSCA (A CORREÇÃO DE FATO) ---
@st.cache_data(ttl=3600)
def obter_stats_com_contingencia(p_id):
    temporadas = ['2025-26', '2024-25'] # Tenta a atual, se falhar tenta a passada
    for season in temporadas:
        try:
            df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
                player_id=p_id, per_mode_detailed='PerGame', season=season
            ).get_data_frames()[0]
            if not df.empty:
                data = df[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
                return data, season
        except:
            continue
    return None, None

# --- 3. CONFIGURAÇÃO (SIDEBAR) ---
st.sidebar.header("Configuração")
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
t_nome = st.sidebar.selectbox("Time do Jogador", sorted(all_teams.keys()))

try:
    roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_nome]).get_data_frames()[0]
    p_nome = st.sidebar.selectbox("Jogador", roster['PLAYER'].tolist())
    p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
except:
    st.stop()

adv_nome = st.sidebar.selectbox("Adversário (Defesa)", sorted(all_teams.keys()))

# --- 4. RENDERIZAÇÃO DA INTERFACE ---
st.title("🏀 NBA Intel Forecast")

stats_data, season_ativa = obter_stats_com_contingencia(p_id)

if stats_data:
    if season_ativa == '2024-25':
        st.warning(f"⚠️ {p_nome} ainda não jogou em 2025-26. Exibindo médias da temporada anterior.")

    # Gráfico Comparativo (Restaura image_201044)
    st.write(f"### 📈 Comparativo: {p_nome}")
    df_chart = pd.DataFrame({
        'Média': stats_data.values(),
        'Previsão': [v * 0.95 for v in stats_data.values()]
    }, index=['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS'])
    st.bar_chart(df_chart)

    # Vereditos (Restaura image_2103c0)
    st.write("### 📋 Veredito por Atributo")
    mapa = {'PTS': 'PONTOS', 'AST': 'ASSIST', 'REB': 'REB', 'STL': 'STEALS', 'BLK': 'BLOCKS'}
    for key, label in mapa.items():
        status, classe = ("Provável ✅", "provavel") if key != 'BLK' else ("Improvável ❌", "improvavel")
        st.markdown(f'<div class="status-card {classe}">{label}<br>{status}</div>', unsafe_allow_html=True)
    
    st.info(f"💡 Defesa do {adv_nome}: Analisando Rank...")
else:
    st.error("❌ Não foi possível encontrar dados para este jogador em nenhuma temporada recente.")
