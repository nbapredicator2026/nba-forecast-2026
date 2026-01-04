import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits
import plotly.graph_objects as go
import time

# --- CONFIGURAÇÃO MOBILE-FIRST ---
st.set_page_config(page_title="NBA Intel 2026", page_icon="🏀", layout="centered")

# CSS para remover margens excessivas e estilizar métricas no celular
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    [data-testid="stMetric"] { background: #f0f2f6; padding: 10px; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def carregar_lista_times():
    return {t['full_name']: t['id'] for t in teams.get_teams()}

@st.cache_data(ttl=3600)
def obter_ranking_defensivo():
    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Defense', season='2025-26').get_data_frames()[0]
        df_def = team_stats[['TEAM_NAME', 'DEF_RATING']].sort_values('DEF_RATING')
        df_def['RANK'] = range(1, 31)
        return df_def
    except:
        return pd.DataFrame({'TEAM_NAME': [t['full_name'] for t in teams.get_teams()], 'RANK': [15]*30})

@st.cache_data(ttl=7200)
def buscar_elenco(team_id):
    roster = commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26').get_data_frames()[0]
    return roster[['PLAYER', 'PLAYER_ID']].sort_values('PLAYER')

@st.cache_data(ttl=3600)
def buscar_estatisticas_jogador(player_id):
    stats = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(player_id=player_id, per_mode_detailed='PerGame').get_data_frames()[0]
    return stats[['PTS', 'AST', 'REB', 'STL', 'BLK']].iloc[0].to_dict()

# --- INTERFACE ---
st.title("🏀 NBA Intel Forecast")

# Sidebar para configurações (fica escondida no iPhone)
with st.sidebar:
    st.header("Configuração")
    dict_times = carregar_lista_times()
    time_nome = st.selectbox("Time do Jogador", sorted(dict_times.keys()))
    df_elenco = buscar_elenco(dict_times[time_nome])
    jogador_nome = st.selectbox("Jogador", df_elenco['PLAYER'].tolist())
    player_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
    adversario_nome = st.selectbox("Adversário (Defesa)", sorted(dict_times.keys()))

try:
    stats = buscar_estatisticas_jogador(player_id)
    df_def = obter_ranking_defensivo()
    rank_def_adv = df_def[df_def['TEAM_NAME'] == adversario_nome]['RANK'].values[0]

    # Resumo Real (Horizontal no PC, Vertical no Celular)
    st.subheader(f"📊 Real: {jogador_nome}")
    m_cols = st.columns(3) # No celular vira coluna única automaticamente
    cats = ['PTS', 'AST', 'REB', 'STL', 'BLK']
    labels = ['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS']
    
    m_cols[0].metric("PTS", f"{stats['PTS']:.1f}")
    m_cols[1].metric("AST", f"{stats['AST']:.1f}")
    m_cols[2].metric("REB", f"{stats['REB']:.1f}")

    st.markdown("---")
    st.subheader(f"🔮 Previsão vs {adversario_nome}")
    
    # Inputs condensados
    u_vals = {}
    for i, cat in enumerate(cats):
        u_vals[cat] = st.number_input(labels[i], value=float(stats[cat]), step=0.5, key=cat)

    if st.button("ANALISAR AGORA"):
        # 1. Gráfico Otimizado para Celular
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Média', x=labels, y=[stats[c] for c in cats], marker_color='#1f77b4'))
        fig.add_trace(go.Bar(name='Previsão', x=labels, y=[u_vals[c] for c in cats], marker_color='#ff7f0e'))
        
        fig.update_layout(
            barmode='group', 
            height=300, 
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # 2. Veredito em Cards de Cores (Melhor para iPhone)
        st.markdown("### 📈 Veredito por Atributo")
        for i, cat in enumerate(cats):
            exp = stats[cat] * (1 - (15 - rank_def_adv) * 0.012)
            diff = (u_vals[cat] - exp) / (exp if exp != 0 else 1)
            
            if diff <= 0.05:
                cor, emoji, txt = "#D4EDDA", "✅", "Provável"
                txt_color = "#155724"
            elif diff <= 0.20:
                cor, emoji, txt = "#FFF3CD", "⚠️", "Incerto"
                txt_color = "#856404"
            else:
                cor, emoji, txt = "#F8D7DA", "❌", "Improvável"
                txt_color = "#721C24"
            
            st.markdown(f"""
                <div style="background-color:{cor}; color:{txt_color}; padding:15px; border-radius:12px; margin-bottom:10px; border-left: 5px solid {txt_color}">
                    <div style="font-size:0.8rem; text-transform:uppercase; font-weight:bold;">{labels[i]}</div>
                    <div style="font-size:1.1rem;">{txt} {emoji}</div>
                </div>
            """, unsafe_allow_html=True)

        # 3. Insight
        st.info(f"💡 **Defesa do {adversario_nome}:** Rank {rank_def_adv}º de 30.")

except Exception as e:
    st.error(f"Selecione os times no menu lateral para começar!")
