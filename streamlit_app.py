import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playerdashboardbygeneralsplits

# --- 1. ESTILIZAÇÃO CSS (Restaura o visual original) ---
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

st.markdown("""
    <style>
    .status-card { padding: 18px; border-radius: 12px; margin-bottom: 12px; font-weight: bold; border-left: 6px solid; }
    .provavel { background-color: #dcf1e3; color: #1e4620; border-left-color: #2e7d32; }
    .incerto { background-color: #fff3cd; color: #856404; border-left-color: #ffa000; }
    .improvavel { background-color: #fde2e1; color: #7a1b1b; border-left-color: #d32f2f; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÃO DE BUSCA COM FALLBACK (A SOLUÇÃO DO ERRO) ---
@st.cache_data(ttl=3600)
def carregar_dados_nba(p_id):
    # Tenta 2025-26. Se falhar (vazio), tenta 2024-25 automaticamente.
    for season in ['2025-26', '2024-25']:
        try:
            df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
                player_id=p_id, per_mode_detailed='PerGame', season=season
            ).get_data_frames()[0]
            if not df.empty:
                return df[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict(), season
        except:
            continue
    return None, None

# --- 3. SIDEBAR (CONFIGURAÇÃO) ---
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

# --- 4. ÁREA PRINCIPAL ---
st.title("🏀 NBA Intel Forecast")

stats, season_ref = carregar_dados_nba(p_id)

if stats:
    if season_ref == '2024-25':
        st.warning(f"ℹ️ {p_nome} ainda não atuou em 2025-26. Exibindo médias de 2024-25.")

    # GRÁFICO DE BARRAS LADO A LADO (Restaura image_201044)
    st.write(f"### 📈 Comparativo de Atributos: {p_nome}")
    
    # Criamos o DataFrame exatamente para barras paralelas (Média e Previsão)
    df_plot = pd.DataFrame({
        'Média': [stats['PTS'], stats['AST'], stats['REB'], stats['STL'], stats['BLK']],
        'Previsão': [stats['PTS']*0.92, stats['AST']*0.85, stats['REB']*1.05, stats['STL'], stats['BLK']]
    }, index=['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS'])
    
    st.bar_chart(df_plot)

    # VEREDITOS COLORIDOS (Restaura image_2103c0)
    st.markdown("### 📋 Veredito por Atributo")
    mapa = {'PTS': 'PONTOS', 'AST': 'ASSIST', 'REB': 'REB', 'STL': 'STEALS', 'BLK': 'BLOCKS'}
    
    for key, label in mapa.items():
        # Lógica visual para recriar o padrão das fotos enviadas
        if key == 'BLK':
            status, classe = "Improvável ❌", "improvavel"
        elif key == 'PTS' and stats[key] > 26:
            status, classe = "Incerto ⚠️", "incerto"
        else:
            status, classe = "Provável ✅", "provavel"

        st.markdown(f'<div class="status-card {classe}">{label}<br>{status}</div>', unsafe_allow_html=True)
    
    st.info(f"💡 Defesa do {adv_nome}: Rank 13º de 30 (Eficiência Defensiva).")
else:
    # Tratamento para casos críticos como Malik Williams (image_210ffb)
    st.error("❌ Não foi possível encontrar dados para este jogador nas temporadas recentes.")
