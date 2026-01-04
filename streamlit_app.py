import streamlit as st
import pandas as pd
import numpy as np
import time

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="NBA Intel Forecast (Modo Offline)", layout="centered")

st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; border-radius: 10px; padding: 10px; }
    .status-card { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; color: white; }
    .provavel { background-color: #28a745; }
    .improvavel { background-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# SIMULAÇÃO DE DADOS (Substitui a API travada)
# ==============================================================================
def gerar_dados_ficticios(jogador):
    """Gera dados falsos apenas para testar a interface"""
    # Simula um tempo de carregamento para parecer real
    time.sleep(0.5) 
    
    # Cria números aleatórios baseados no nome para serem sempre iguais para o mesmo jogador
    np.random.seed(len(jogador)) 
    
    pts_media = np.random.randint(15, 30) + np.random.random()
    pts_fase = pts_media + np.random.randint(-5, 6) # Fase varia um pouco da média
    
    return {
        'stats': {
            'PTS': pts_media,
            'AST': np.random.randint(4, 10),
            'REB': np.random.randint(2, 8)
        },
        'fase': pts_fase
    }

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("🏀 NBA Intel Forecast")
st.warning("⚠️ MODO DE TESTE: Usando dados simulados (API Desligada)")

# --- SIDEBAR ---
st.sidebar.header("Configuração")
# Listas fixas para não depender da internet
times = ["Lakers", "Warriors", "Celtics", "Bulls", "Heat"]
jogadores = {
    "Lakers": ["LeBron James", "Anthony Davis"],
    "Warriors": ["Stephen Curry", "Klay Thompson"],
    "Celtics": ["Jayson Tatum", "Jaylen Brown"],
    "Bulls": ["DeMar DeRozan", "Zach LaVine"],
    "Heat": ["Jimmy Butler", "Bam Adebayo"]
}

t_nome = st.sidebar.selectbox("Time", times)
p_nome = st.sidebar.selectbox("Jogador", jogadores[t_nome])
adv_nome = st.sidebar.selectbox("Adversário", [t for t in times if t != t_nome])

# --- DASHBOARD ---
st.subheader(f"Análise: {p_nome}")

# Gerar dados
data = gerar_dados_ficticios(p_nome)

# Exibir Métricas
diff = data['fase'] - data['stats']['PTS']
col1, col2, col3 = st.columns(3)
col1.metric("Média Pontos", f"{data['stats']['PTS']:.1f}", delta=f"{diff:+.1f} Fase Recente")
col2.metric("Assistências", f"{data['stats']['AST']}")
col3.metric("Rebotes", f"{data['stats']['REB']}")

st.divider()

# Área de Aposta
previsao = st.number_input("Sua Linha (Pontos)", value=float(int(data['stats']['PTS'])))

if st.button("ANALISAR AGORA", use_container_width=True):
    
    # 1. Gráfico
    st.write("#### Comparativo de Performance")
    df_viz = pd.DataFrame({
        'Métrica': ['Média Temp.', 'Sua Linha', 'Fase (L5)'],
        'Pontos': [data['stats']['PTS'], previsao, data['fase']]
    }).set_index('Métrica')
    
    st.bar_chart(df_viz, color=["#FF4B4B"])

    # 2. Veredito
    margem = data['stats']['PTS'] * 1.1
    is_prov = previsao <= margem
    
    classe = "provavel" if is_prov else "improvavel"
    txt = "Provável (OVER) ✅" if is_prov else "Arriscado (UNDER) ❌"
    msg = "Tendência favorável baseada nos últimos jogos." if is_prov else "Linha muito alta para a fase atual."
    
    st.markdown(f"""
        <div class="status-card {classe}">
            {txt}<br>
            <span style='font-weight:normal; font-size:14px'>{msg}</span>
        </div>
    """, unsafe_allow_html=True)
