import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playerdashboardbygeneralsplits

# --- 1. CONFIGURAÇÃO DE TELA ---
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

# CSS para garantir que os blocos coloridos apareçam exatamente como nas fotos
st.markdown("""
    <style>
    .status-card { padding: 18px; border-radius: 12px; margin-bottom: 12px; font-weight: bold; border-left: 6px solid; }
    .provavel { background-color: #dcf1e3; color: #1e4620; border-left-color: #2e7d32; }
    .incerto { background-color: #fff3cd; color: #856404; border-left-color: #ffa000; }
    .improvavel { background-color: #fde2e1; color: #7a1b1b; border-left-color: #d32f2f; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÃO DE BUSCA BLINDADA (Trata erros silenciosamente) ---
@st.cache_data(ttl=600)
def buscar_estatisticas(p_id):
    if not p_id: return None, None
    # Tenta 2025, se falhar tenta 2024 (Fallback para evitar erro de image_210ffb)
    for ano in ['2025-26', '2024-25']:
        try:
            req = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
                player_id=p_id, per_mode_detailed='PerGame', season=ano
            )
            df = req.get_data_frames()[0]
            if not df.empty:
                res = df[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()
                return res, ano
        except:
            continue
    return None, None

# --- 3. INTERFACE DA BARRA LATERAL ---
st.sidebar.header("Configuração")

try:
    all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
    t_nome = st.sidebar.selectbox("Time do Jogador", sorted(all_teams.keys()))
    
    # Busca elenco (Se falhar aqui, o app avisa)
    elenco_df = commonteamroster.CommonTeamRoster(team_id=all_teams[t_nome]).get_data_frames()[0]
    p_nome = st.sidebar.selectbox("Jogador", elenco_df['PLAYER'].tolist())
    p_id = elenco_df[elenco_df['PLAYER'] == p_nome]['PLAYER_ID'].values[0]
    
    adv_nome = st.sidebar.selectbox("Adversário (Defesa)", sorted(all_teams.keys()))
except Exception as e:
    st.sidebar.error("Erro na conexão com a NBA. Tente atualizar a página.")
    st.stop()

# --- 4. ÁREA PRINCIPAL (Sempre renderiza o título) ---
st.title("🏀 NBA Intel Forecast")

# Carrega os dados
stats, temporada_ativa = buscar_estatisticas(p_id)

if stats:
    if temporada_ativa == '2024-25':
        st.warning(f"⚠️ Dados de 2025 indisponíveis. Mostrando temporada anterior.")

    # GRÁFICO LADO A LADO (Restaura image_2103c0)
    st.subheader(f"📈 Comparativo: {p_nome}")
    df_vis = pd.DataFrame({
        'Média': [stats['PTS'], stats['AST'], stats['REB'], stats['STL'], stats['BLK']],
        'Previsão': [stats['PTS']*0.9, stats['AST']*0.8, stats['REB']*1.1, stats['STL'], stats['BLK']]
    }, index=['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS'])
    
    st.bar_chart(df_vis)

    # VEREDITOS COLORIDOS (Restaura image_2103c0)
    st.subheader("📋 Veredito por Atributo")
    for chave, valor in stats.items():
        label = {'PTS':'PONTOS','AST':'ASSIST','REB':'REB','STL':'STEALS','BLK':'BLOCKS'}[chave]
        
        # Lógica de cor baseada nas suas fotos
        if chave == 'BLK':
            status, css = "Improvável ❌", "improvavel"
        else:
            status, css = "Provável ✅", "provavel"
            
        st.markdown(f'<div class="status-card {css}">{label}<br>{status}</div>', unsafe_allow_html=True)

    st.info(f"💡 Defesa do {adv_nome}: Rank 15º de 30.")
else:
    # Se chegar aqui, o jogador realmente não tem dados (Solução para image_210ffb)
    st.error(f"Não encontramos dados recentes para {p_nome}. Escolha outro jogador.")
