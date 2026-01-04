import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, leaguedashteamstats, playerdashboardbygeneralsplits
import plotly.graph_objects as go
import time

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="NBA Forecast v3.2", page_icon="🏀", layout="wide")

# --- FUNÇÕES DE DADOS ---
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

# --- INTERFACE PRINCIPAL ---
st.title("🏀 NBA Intelligence Forecast v3.2")
st.markdown("Análise multi-atributo com cruzamento de dados defensivos e comparação visual.")

# Sidebar
st.sidebar.header("Configuração do Confronto")
dict_times = carregar_lista_times()
time_nome = st.sidebar.selectbox("Selecione o Time do Jogador", sorted(dict_times.keys()))
df_elenco = buscar_elenco(dict_times[time_nome])
jogador_nome = st.sidebar.selectbox("Selecione o Jogador", df_elenco['PLAYER'].tolist())
player_id = df_elenco[df_elenco['PLAYER'] == jogador_nome]['PLAYER_ID'].values[0]
adversario_nome = st.sidebar.selectbox("Adversário (Time Defensor)", sorted(dict_times.keys()))

try:
    stats = buscar_estatisticas_jogador(player_id)
    df_def = obter_ranking_defensivo()
    rank_def_adv = df_def[df_def['TEAM_NAME'] == adversario_nome]['RANK'].values[0]

    # Painel de Médias Reais
    st.subheader(f"📊 Desempenho Real: {jogador_nome}")
    m_cols = st.columns(5)
    categorias = ['PTS', 'AST', 'REB', 'STL', 'BLK']
    labels = ['PONTOS', 'ASSIST', 'REB', 'STEALS', 'BLOCKS']
    
    for i, cat in enumerate(categorias):
        m_cols[i].metric(labels[i], f"{stats[cat]:.1f}")

    st.markdown("---")

    # Área de Previsão Manual (TODOS OS CAMPOS RESTAURADOS)
    st.subheader(f"🔮 Sua Previsão contra {adversario_nome}")
    c_in = st.columns(5)
    u_vals = {}
    u_vals['PTS'] = c_in[0].number_input("PONTOS", value=float(stats['PTS']), step=0.5)
    u_vals['AST'] = c_in[1].number_input("ASSIST", value=float(stats['AST']), step=0.5)
    u_vals['REB'] = c_in[2].number_input("REB", value=float(stats['REB']), step=0.5)
    u_vals['STL'] = c_in[3].number_input("STEALS", value=float(stats['STL']), step=0.5)
    u_vals['BLK'] = c_in[4].number_input("BLOCKS", value=float(stats['BLK']), step=0.5)

    if st.button("EXECUTAR ANÁLISE E GERAR GRÁFICO"):
        with st.spinner('Analisando todos os atributos...'):
            time.sleep(0.8)
            
            # 1. Lógica de Probabilidade Independente por Atributo
            def analisar_prob(v_user, v_real, r_def):
                # Ajuste defensivo: defesas fortes reduzem a expectativa
                expectativa = v_real * (1 - (15 - r_def) * 0.012)
                diff = (v_user - expectativa) / expectativa
                if diff <= 0.05: return "Muito Provável ✅"
                elif diff <= 0.20: return "Incerto ⚠️"
                else: return "Improvável ❌"

            # 2. Gráfico de Barras Agrupadas
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Média Real', x=labels, y=[stats[c] for c in categorias], marker_color='#1f77b4'))
            fig.add_trace(go.Bar(name='Sua Previsão', x=labels, y=[u_vals[c] for c in categorias], marker_color='#ff7f0e'))
            fig.update_layout(barmode='group', title=f"Comparação Real vs Previsão: {jogador_nome}", yaxis_title="Valores")
            st.plotly_chart(fig, use_container_width=True)

            # 3. Veredito Individual (Item 1 corrigido)
            st.markdown("### 📈 Veredito por Atributo:")
            res_cols = st.columns(5)
            for i, cat in enumerate(categorias):
                veredito = analisar_prob(u_vals[cat], stats[cat], rank_def_adv)
                res_cols[i].markdown(f"**{labels[i]}**\n\n{veredito}")

            # 4. Insight do Especialista (Item 2 corrigido)
            st.markdown("---")
            st.subheader("💡 Insight do Especialista")
            if rank_def_adv <= 5:
                st.error(f"**Dificuldade Máxima:** O {adversario_nome} possui uma defesa de ELITE (Rank {rank_def_adv}º). Marcar pontos ou distribuir assistências acima da média será um desafio físico e tático extremo para {jogador_nome}.")
            elif rank_def_adv >= 25:
                st.success(f"**Cenário Favorável:** A defesa do {adversario_nome} é uma das mais permissivas (Rank {rank_def_adv}º). Há uma alta probabilidade de {jogador_nome} superar suas médias habituais em volume de jogo.")
            else:
                st.info(f"**Confronto Equilibrado:** O {adversario_nome} mantém uma defesa média (Rank {rank_def_adv}º). O desempenho deve orbitar as estatísticas da temporada, dependendo mais do ritmo individual do jogador.")

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
