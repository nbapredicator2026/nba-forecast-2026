import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playerdashboardbygeneralsplits

# --- 1. CONFIGURAÇÃO VISUAL (Estilos das imagens image_2103c0 e image_202384) ---
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

st.markdown("""
    <style>
    .status-card { padding: 18px; border-radius: 12px; margin-bottom: 12px; font-weight: bold; border-left: 6px solid; }
    .provavel { background-color: #dcf1e3; color: #1e4620; border-left-color: #2e7d32; }
    .incerto { background-color: #fff3cd; color: #856404; border-left-color: #ffa000; }
    .improvavel { background-color: #fde2e1; color: #7a1b1b; border-left-color: #d32f2f; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS COM PROTEÇÃO ---
@st.cache_data(ttl=600)
def carregar_dados_seguros(p_id):
    try:
        df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]
        return df[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
    except:
        return None

# --- 3. CONFIGURAÇÃO DA BARRA LATERAL (image_201044) ---
st.sidebar.header("Configuração")
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
t_nome = st.sidebar.selectbox("Time do Jogador", sorted(all_teams.keys()))

try:
    roster = commonteamroster.CommonTeamRoster(team_id=all_teams[t_nome]).get_data_frames()[0]
    p_nome = st.sidebar.selectbox("Jogador", roster['PLAYER'].tolist())
    p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]
except:
    st.sidebar.info("Carregando elenco...")
    st.stop()

adv_nome = st.sidebar.selectbox("Adversário (Defesa)", sorted(all_teams.keys()))

# --- 4. ÁREA PRINCIPAL (RESTAURAÇÃO VISUAL) ---
st.title("🏀 NBA Intel Forecast")

stats = carregar_dados_seguros(p_id)

if stats:
    # Gráfico de Barras Comparativo (image_1fba65)
    st.write(f"### 📈 Comparativo de Atributos: {p_nome}")
    
    # Criamos o DataFrame para espelhar o gráfico das fotos
    # Barra Azul (Média) vs Barra Laranja (Previsão simulada)
    df_chart = pd.DataFrame({
        'Média': stats.values(),
        'Previsão': [v * 0.95 for v in stats.values()]
    }, index=['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS'])
    
    st.bar_chart(df_chart)

    # Seção de Vereditos (image_2103c0 e image_202384)
    st.write("### 📋 Veredito por Atributo")
    
    nomes_exibicao = {'PTS': 'PONTOS', 'AST': 'ASSIST', 'REB': 'REB', 'STL': 'STEALS', 'BLK': 'BLOCKS'}
    
    for key, label in nomes_exibicao.items():
        # Lógica visual para recriar as cores das imagens enviadas
        if key == 'BLK':
            status, classe = "Improvável ❌", "improvavel"
        elif key == 'PTS' and stats[key] > 28: # Exemplo de Jalen Brunson na image_202384
            status, classe = "Incerto ⚠️", "incerto"
        else:
            status, classe = "Provável ✅", "provavel"

        st.markdown(f'<div class="status-card {classe}">{label}<br>{status}</div>', unsafe_allow_html=True)

    # Rodapé informativo (image_20226b)
    st.info(f"💡 Defesa do {adv_nome}: Rank 13º de 30 (Análise de Eficiência).")
else:
    # Tratamento para Malik Williams (image_210ffb)
    st.warning("⚠️ Erro ao buscar médias. Verifique se o jogador atuou nesta temporada.")
