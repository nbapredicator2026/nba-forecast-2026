import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (commonteamroster, leaguedashteamstats, 
                                     playerdashboardbygeneralsplits, playergamelog)

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILOS CSS
# ==============================================================================
st.set_page_config(page_title="NBA Intel Forecast", layout="centered")

# CSS personalizado para melhorar a aparência das métricas e cards de status
st.markdown("""
    <style>
    /* Estilo para as caixas de métricas (st.metric) */
    .stMetric { 
        background-color: #ffffff; 
        border: 1px solid #e1e4e8; 
        padding: 15px; 
        border-radius: 12px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Classe base para cards de veredito */
    .status-card { 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        font-weight: bold; 
        border-left: 5px solid; 
    }
    /* Variação para resultado provável (Verde) */
    .provavel { 
        background-color: #d4edda; 
        color: #155724; 
        border-left-color: #28a745; 
    }
    /* Variação para resultado improvável (Vermelho) */
    .improvavel { 
        background-color: #f8d7da; 
        color: #721c24; 
        border-left-color: #dc3545; 
    }
    </style>
    """, unsafe_allow_html=True)

# Definição da temporada atual para evitar erros de "dados não encontrados"
TEMPORADA_ATUAL = '2024-25' 

# ==============================================================================
# CAMADA DE DADOS (COM CACHE E TRATAMENTO DE ERROS)
# ==============================================================================
@st.cache_data(ttl=3600)
def get_nba_data(p_id):
    """
    Busca dados do jogador na API da NBA.
    
    Args:
        p_id (int): ID do jogador na NBA.
        
    Returns:
        dict: Dicionário contendo estatísticas base e média recente, ou None se falhar.
    """
    try:
        # 1. Busca Médias Gerais da Temporada
        # Utiliza o endpoint de splits gerais para pegar médias 'PerGame'
        base = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=p_id, 
            per_mode_detailed='PerGame', 
            season=TEMPORADA_ATUAL
        ).get_data_frames()[0]
        
        # Verificação de segurança: Se o jogador não jogou, retorna None
        if base.empty:
            return None

        # 2. Busca o Histórico de Jogos (Game Log) para calcular a "Fase"
        log = playergamelog.PlayerGameLog(
            player_id=p_id, 
            season=TEMPORADA_ATUAL
        ).get_data_frames()[0]
        
        # Calcula a média dos últimos 5 jogos (ou menos, se tiver jogado pouco)
        if not log.empty:
            media_recente = log['PTS'].head(5).mean()
        else:
            media_recente = 0.0
        
        # Retorna estrutura de dados limpa
        return {
            'stats': base[['PTS', 'AST', 'REB']].iloc[0].to_dict(),
            'fase': media_recente
        }
        
    except Exception as e:
        st.error(f"Erro ao conectar com a API da NBA: {e}")
        return None

# ==============================================================================
# INTERFACE DO USUÁRIO (FRONTEND STREAMLIT)
# ==============================================================================
st.title("🏀 NBA Intel Forecast")
st.caption("Sistema de Análise de Desempenho e Previsão Estatística")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("Filtros de Pesquisa")

# Carrega lista de times estática (rápido)
all_teams = {t['full_name']: t['id'] for t in teams.get_teams()}
t_nome = st.sidebar.selectbox("Selecione o Time", sorted(all_teams.keys()))

# Busca elenco do time selecionado
try:
    roster = commonteamroster.CommonTeamRoster(
        team_id=all_teams[t_nome], 
        season=TEMPORADA_ATUAL
    ).get_data_frames()[0]
    
    p_nome = st.sidebar.selectbox("Selecione o Jogador", roster['PLAYER'].tolist())
    
    # Obtém o ID do jogador selecionado para a próxima chamada
    p_id = roster[roster['PLAYER'] == p_nome]['PLAYER_ID'].values[0]
    
except Exception:
    st.sidebar.error("Não foi possível carregar o elenco. Verifique a temporada.")
    st.stop() # Para a execução se não tiver jogador

adv_nome = st.sidebar.selectbox("Adversário", sorted(all_teams.keys()))

# --- PROCESSAMENTO PRINCIPAL ---
data = get_nba_data(p_id)

if data:
    # 1. Exibição de KPIs com Delta (Tendência)
    # O delta compara a média dos últimos 5 jogos com a média da temporada
    diff = data['fase'] - data['stats']['PTS']
    
    st.subheader(f"📊 Estatísticas Reais: {p_nome}")
    
    col1, col2, col3 = st.columns(3)
    
    # Métrica de Pontos com indicador visual de tendência (verde/vermelho)
    col1.metric(
        label="PTS (Média)", 
        value=f"{data['stats']['PTS']:.1f}", 
        delta=f"{diff:+.1f} vs Fase Recente",
        delta_color="normal" # Verde se a fase recente for melhor que a média
    )
    
    col2.metric("AST (Assistências)", f"{data['stats']['AST']:.1f}")
    col3.metric("REB (Rebotes)", f"{data['stats']['REB']:.1f}")

    # 2. Área de Previsão e Análise
    st.divider()
    st.markdown("### 🔮 Simulador de Aposta")
    
    # Input do usuário para definir a linha da casa de apostas
    previsao = st.number_input(
        "Insira a Linha de Pontos (Over/Under)", 
        value=float(data['stats']['PTS']),
        step=0.5
    )

    if st.button("ANALISAR AGORA", use_container_width=True):
        
        # --- VISUALIZAÇÃO GRÁFICA ---
        st.markdown("#### Comparativo de Performance")
        
        # Criação do DataFrame para o gráfico de barras
        # Compara: Média da Temporada vs Linha do Usuário vs Fase Atual (L5)
        df_viz = pd.DataFrame({
            'Métrica': ['Média Anual', 'Sua Linha', 'Fase (Últimos 5)'],
            'Pontos': [data['stats']['PTS'], previsao, data['fase']]
        }).set_index('Métrica')
        
        # Renderiza gráfico de barras (mais estável que linhas para dados discretos)
        st.bar_chart(df_viz, color=["#FF4B4B"]) # Cor padrão Streamlit ou personalizada

        # --- LÓGICA DO VEREDITO ---
        # Regra simples: Se a linha do usuário for menor que a média + 10%, é provável bater o Over
        # (Nota: Em um app real, essa lógica seria mais complexa, considerando defesa adversária)
        margem_seguranca = data['stats']['PTS'] * 1.1
        is_provavel = previsao <= margem_seguranca
        
        estilo_css = "provavel" if is_provavel else "improvavel"
        texto_veredito = "Provável (OVER) ✅" if is_provavel else "Improvável / Arriscado ❌"
        mensagem_detalhe = "Jogador está com médias consistentes para superar essa linha." if is_provavel else "Linha muito alta considerando a média atual."

        # Renderiza o card colorido usando HTML/CSS injetado
        st.markdown(f"""
            <div class="status-card {estilo_css}">
                VEREDITO PONTOS: {texto_veredito}<br>
                <span style="font-weight:normal; font-size:0.9em;">{mensagem_detalhe}</span>
            </div>
            """, unsafe_allow_html=True)

elif data is None:
    st.warning(f"Dados indisponíveis para {p_nome} na temporada {TEMPORADA_ATUAL}. O jogador pode estar lesionado ou sem minutos.")
