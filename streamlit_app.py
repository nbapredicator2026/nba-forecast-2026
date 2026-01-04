import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits)

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

# CSS para os Cards de Veredito (Verde, Amarelo, Vermelho)
st.markdown("""
    <style>
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid; }
    .provavel { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .incerto { background-color: #fff3cd; color: #856404; border-left-color: #ffc107; }
    .improvavel { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE DADOS ---
@st.cache_data(ttl=3600)
def carregar_elenco(team_id):
    df = commonteamroster.CommonTeamRoster(team_id=team_id).get_data_frames()[0]
    return df[['PLAYER', 'PLAYER_ID']]

@st.cache_data(ttl=3600)
def obter_medias(player_id):
    try:
        df = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=player_id, per_mode_detailed='PerGame', season='2025-26'
        ).get_data_frames()[0]
        return df[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
    except: return None

@st.cache_data(ttl=86400)
def obter_rank_defensivo():
    df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]
    df = df[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
    df['RANK'] = range(1, 31)
    return df

# --- 3. BARRA LATERAL (CONFIGURAÇÃO) ---
st.sidebar.header("Configuração")
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
t_nome = st.sidebar.selectbox("Time do Jogador", sorted(all_teams.keys()))

roster = carregar_elenco(all_teams[t_nome])
p_nome = st.sidebar.selectbox("Jogador", roster['PLAYER'].tolist())
p_id = roster[roster['PLAYER'] == p_name]['PLAYER_ID'].values[0]

adv_nome = st.sidebar.selectbox("Adversário (Defesa)", sorted(all_teams.keys()))

# --- 4. ÁREA PRINCIPAL ---
stats = obter_medias(p_id)
db_defesa = obter_rank_defensivo()
rank_adv = db_defesa[db_defesa['TEAM_NAME'] == adv_nome]['RANK'].values[0]

if stats:
    # Gráfico de Barras (Média vs Previsão)
    # Simulamos uma previsão do usuário para renderizar o gráfico igual às imagens
    previsao_exemplo = {k: v * 0.9 for k, v in stats.items()} 
    
    df_grafico = pd.DataFrame({
        'Média': stats.values(),
        'Previsão': previsao_exemplo.values()
    }, index=['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS'])
    
    st.bar_chart(df_grafico)

    st.subheader("📈 Veredito por Atributo")
    
    # Lógica de renderização dos cards (Igual image_2103c0.png)
    for attr, val in stats.items():
        # Exemplo de lógica: se rank da defesa é bom, fica mais difícil
        status = "Provável ✅" if rank_adv > 15 else "Improvável ❌"
        classe = "provavel" if rank_adv > 15 else "improvavel"
        
        # Caso especial para o "Incerto" (image_202384.png)
        if 10 <= rank_adv <= 15:
            status = "Incerto ⚠️"
            classe = "incerto"

        st.markdown(f"""<div class="status-card {classe}">{attr}<br>{status}</div>""", unsafe_allow_html=True)

    # Rodapé informativo (image_1e5908.png)
    st.info(f"💡 Defesa do {adv_nome}: Rank {rank_adv}º de 30.")
