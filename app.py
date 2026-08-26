import pandas as pd
import plotly.express as px
import requests
import unicodedata
from database import carregar_dados_streamlit
import os
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import ChatDetails, OnDemandServingMode, CohereChatRequest
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# Configuração das credenciais OCI do .env
config_oci = {
    "user": os.getenv("OCI_USER"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY"),
    "region": os.getenv("OCI_REGION"),
    "key_file": os.getenv("OCI_KEY_FILE")
}


def perguntar_ao_nexus_ia(pergunta_usuario):
    try:
        endpoint = f"https://inference.generativeai.{config_oci['region']}.oci.oraclecloud.com"
        inference_client = GenerativeAiInferenceClient(config=config_oci, service_endpoint=endpoint)

        pergunta_lower = pergunta_usuario.lower()

        # Função auxiliar para carregar a tabela de internações (suporta CSV ou Excel)
        def carregar_internacoes():
            try:
                return pd.read_csv("INTERNACOES_DATA.csv")
            except:
                return pd.read_excel("INTERNACOES_DATA.xlsx")

        # Função auxiliar para carregar a tabela de leitos (suporta CSV ou Excel)
        def carregar_leitos():
            try:
                return pd.read_csv("LEITOS_MUNICIPIO.csv")
            except:
                return pd.read_excel("LEITOS_MUNICIPIO.xlsx")

        # 1. Panorama Geral
        if "panorama" in pergunta_lower or "geral" in pergunta_lower or "resumo" in pergunta_lower:
            df_inter = carregar_internacoes()
            total_internacoes = len(df_inter)
            data_min = pd.to_datetime(df_inter['DATA']).min().strftime('%d/%m/%Y')
            data_max = pd.to_datetime(df_inter['DATA']).max().strftime('%d/%m/%Y')
            tempo_medio = df_inter['TEMPO_PERMANENCIA'].mean()
            total_hosp = df_inter['NOME_ESTABELECIMENTO'].nunique()
            total_mun = df_inter['MUNICIPIO'].nunique()

            resumo_dados = f"""
            === PANORAMA GERAL DE INTERNAÇÕES ===
            - Total de Internações: {total_internacoes:,}
            - Período: de {data_min} a {data_max}
            - Tempo Médio de Permanência: {tempo_medio:.1f} dias
            - Municípios Atendidos: {total_mun}
            - Total de Hospitais/Estabelecimentos: {total_hosp}
            """

        # 2. Hospitais
        elif "hospital" in pergunta_lower or "hospitais" in pergunta_lower or "estabelecimento" in pergunta_lower:
            df_inter = carregar_internacoes()
            ranking = df_inter['NOME_ESTABELECIMENTO'].value_counts().head(10).reset_index()
            ranking.columns = ['Nome do Hospital', 'Qtd Internações']
            resumo_dados = f"=== RANKING DE HOSPITAIS ===\n" + ranking.to_string(index=False)

        # 3. Tipos de Internação
        elif "tipo" in pergunta_lower and "interna" in pergunta_lower:
            df_inter = carregar_internacoes()
            tipos = df_inter['TIPO_INTERNACAO'].value_counts().reset_index()
            tipos.columns = ['Tipo de Internação', 'Quantidade']
            resumo_dados = f"=== TIPOS DE INTERNAÇÃO ===\n" + tipos.to_string(index=False)

        # 4. CIDs (CORRIGIDO: A busca por prefixo (ex: E10.9) foi restaurada!)
        elif "cid" in pergunta_lower and "interna" in pergunta_lower:
            df_inter = carregar_internacoes()
            try:
                df_cid = pd.read_csv("TAB_CID.csv")
            except:
                df_cid = pd.read_excel("TAB_CID.xlsx")

            descricoes = []
            for cid in df_inter['CID']:
                desc = "Condição especializada"
                match = df_cid[df_cid['CID'] == str(cid)]
                if not match.empty:
                    desc = match.iloc[0]['Descrição']
                else:
                    prefix = str(cid).split('.')[0]
                    match_prefix = df_cid[df_cid['CID'].str.contains(prefix, na=False)]
                    if not match_prefix.empty:
                        desc = match_prefix.iloc[0]['Descrição']
                descricoes.append(desc)

            df_inter['DESC'] = descricoes
            ranking_cids = df_inter[['CID', 'DESC']].value_counts().head(10).reset_index()
            ranking_cids.columns = ['CID', 'Descrição', 'Qtd']
            resumo_dados = f"=== CIDs NAS INTERNAÇÕES ===\n" + ranking_cids.to_string(index=False)

        # 5. Período / Datas
        elif "período" in pergunta_lower or "periodo" in pergunta_lower or "data" in pergunta_lower or "quando" in pergunta_lower:
            df_inter = carregar_internacoes()
            data_min = pd.to_datetime(df_inter['DATA']).min().strftime('%d/%m/%Y')
            data_max = pd.to_datetime(df_inter['DATA']).max().strftime('%d/%m/%Y')
            resumo_dados = f"=== PERÍODO DAS INTERNAÇÕES ===\n- Data Inicial: {data_min}\n- Data Final: {data_max}"

        # 6. Regiões (Agrupamento Geral ou Filtro Específico)
        elif "região" in pergunta_lower or "regiao" in pergunta_lower or "regiões" in pergunta_lower or "regioes" in pergunta_lower:
            df_leitos = carregar_leitos()

            regioes_sp = ['SOROCABA', 'METROPOLITANA', 'CAMPINAS', 'BAURU', 'ARACATUBA', 'ARARAQUARA', 'RIBEIRAO PRETO',
                          'VALE DO PARAIBA', 'LITORAL']
            regiao_especifica = None

            for r in regioes_sp:
                if r.lower() in pergunta_lower or r.replace(" ", "").lower() in pergunta_lower:
                    regiao_especifica = r
                    break

            if regiao_especifica:
                df_filtrado = df_leitos[df_leitos['REGIAO'].str.upper() == regiao_especifica]
                mun_reg = df_filtrado['Município'].nunique()
                leitos_reg = df_filtrado['Total Leitos'].sum()
                resumo_dados = f"=== DADOS DA REGIÃO {regiao_especifica} ===\n- Municípios Atendidos: {mun_reg}\n- Soma Total de Leitos: {leitos_reg:,}"
            else:
                total_regioes = df_leitos['REGIAO'].nunique()
                total_mun_estado = df_leitos['Município'].nunique()
                mun_por_regiao = df_leitos.groupby('REGIAO')['Município'].nunique().reset_index()
                mun_por_regiao.columns = ['Região', 'Qtd de Municípios']

                resumo_dados = f"=== RESUMO DE REGIÕES ===\n- Total de Regiões no Estado: {total_regioes}\n- Total de Municípios no Estado: {total_mun_estado}\n\n=== DISTRIBUIÇÃO ===\n{mun_por_regiao.to_string(index=False)}"

        # 7. Municípios (Ranking de Internações)
        elif "município" in pergunta_lower or "municipio" in pergunta_lower or "cidade" in pergunta_lower:
            df_inter = carregar_internacoes()
            ranking = df_inter['MUNICIPIO'].value_counts().head(10).reset_index()
            ranking.columns = ['Município', 'Qtd Internações']
            resumo_dados = f"=== RANKING DE INTERNAÇÕES POR MUNICÍPIO ===\n" + ranking.to_string(index=False)

        # 8. Padrão (Fallback) - Totais do Estado
        else:
            df_leitos = carregar_leitos()
            total_leitos = df_leitos['Total Leitos'].sum()
            populacao = df_leitos['População'].sum()
            resumo_dados = f"=== DADOS GERAIS DO ESTADO ===\n- Total de Leitos: {total_leitos:,}\n- População Total: {populacao:,}"

        # Monta o prompt e envia para a Inteligência Artificial
        prompt_com_contexto = f"""
        Você é o Nexus AI, assistente inteligente de saúde pública do SUS. 
        Abaixo estão os dados oficiais calculados do sistema para responder à pergunta:

        {resumo_dados}

        Com base exclusivamente nesses dados, responda à pergunta do usuário de forma clara, objetiva e completa.
        Pergunta: {pergunta_usuario}
        """

        chat_request = CohereChatRequest(
            message=prompt_com_contexto,
            max_tokens=1500
        )

        chat_detail = ChatDetails()
        chat_detail.serving_mode = OnDemandServingMode(model_id="cohere.command-r-08-2024")
        chat_detail.compartment_id = config_oci["tenancy"]
        chat_detail.chat_request = chat_request

        response = inference_client.chat(chat_detail)
        return response.data.chat_response.text

    except Exception as e:
        return f"Erro ao processar com OCI GenAI: {e}"

# ==========================================
# 1. CONFIGURAÇÃO DO VISUAL
# ==========================================
st.set_page_config(page_title="Centro de Comando SUS", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #F4F7F9; }
    [data-testid="stSidebar"] { background-color: #0A192F; }
    [data-testid="stSidebar"] * { color: #E2E8F0 !important; }

    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        border-radius: 6px;
        border: 1px solid #CBD5E1 !important;
    }
    div[data-baseweb="select"] div { color: #1E293B !important; }
    div[data-baseweb="popover"] > div, ul[role="listbox"] { background-color: #FFFFFF !important; }
    ul[role="listbox"] li { color: #1E293B !important; background-color: #FFFFFF !important; }
    ul[role="listbox"] li:hover { background-color: #F1F5F9 !important; }

    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        padding: 15px 10px;
        border-radius: 8px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
        border-top: 4px solid #1D4ED8;
    }

    h1, h2, h3 { color: #0F172A !important; }
    p, label { color: #334155 !important; }

    /* Aumentar o tamanho do texto do menu lateral (radio buttons) */
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 22px !important;
        font-weight: 600 !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. FUNÇÕES DE ENGENHARIA DE DADOS
# ==========================================
def normalizar_texto(texto):
    if pd.isna(texto): return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()


@st.cache_data(ttl=600)
def load_oracle_data():
    df = carregar_dados_streamlit()
    df.columns = df.columns.str.upper()
    return df


@st.cache_data
def load_leitos():
    if os.path.exists("LEITOS_MUNICIPIO.xlsx"):
        xls = pd.ExcelFile("LEITOS_MUNICIPIO.xlsx")
        df = pd.read_excel("LEITOS_MUNICIPIO.xlsx", sheet_name=xls.sheet_names[0])
    elif os.path.exists("LEITOS_MUNICIPIO.csv"):
        try:
            df = pd.read_csv("LEITOS_MUNICIPIO.csv", encoding="utf-8")
        except:
            df = pd.read_csv("LEITOS_MUNICIPIO.csv", sep=";", encoding="latin1")
    else:
        st.error("⚠️ Arquivo de Leitos não encontrado!")
        return pd.DataFrame()

    df.columns = [normalizar_texto(c) for c in df.columns]
    return df


@st.cache_data(ttl=3600)
def load_geojson():
    url = "https://cdn.jsdelivr.net/gh/tbrugz/geodata-br@master/geojson/geojs-35-mun.json"
    return requests.get(url).json()


with st.spinner("Sincronizando Banco Oracle e Planilhas..."):
    df_fatos = load_oracle_data()
    df_dim = load_leitos()
    geojson_sp = load_geojson()

# ==========================================
# 3. MAPEAMENTO E CORREÇÃO DE NOMES DO GEOJSON
# ==========================================
if not df_dim.empty:
    COL_MUN = next((c for c in df_dim.columns if 'MUNICIPIO' in c or 'MUNICÍPIO' in c), 'MUNICÍPIO')
    COL_REG = next((c for c in df_dim.columns if 'REGIAO' in c or 'REGIÃO' in c), 'REGIÃO')
    COL_LEITOS = next((c for c in df_dim.columns if 'TOTAL LEITOS' in c), 'TOTAL LEITOS')
    COL_POP = next((c for c in df_dim.columns if 'POPULACAO' in c or 'POPULAÇÃO' in c), 'POPULAÇÃO')
    COL_ALERTA = next((c for c in df_dim.columns if 'NIVEL ALERTA' in c or 'NÍVEL ALERTA' in c), 'NÍVEL ALERTA')

    df_dim[COL_LEITOS] = pd.to_numeric(df_dim[COL_LEITOS], errors="coerce").fillna(0)
    df_dim[COL_POP] = pd.to_numeric(df_dim[COL_POP], errors="coerce").fillna(1)

    df_dim["MUNICIPIO_LIMPO"] = df_dim[COL_MUN].apply(normalizar_texto)
    df_dim[COL_REG] = df_dim[COL_REG].fillna("Região Não Informada")
    df_fatos["MUNICIPIO_LIMPO"] = df_fatos["MUNICIPIO"].apply(normalizar_texto)

    correcoes_mapa = {
        "BIRITIBA MIRIM": "BIRITIBA-MIRIM",
        "ESTIVA GERBI": "ESTIVA GERBI",
        "SANTO ANTONIO DE POSSE": "SANTO ANTONIO DE POSSE",
        "MOGI GUACU": "MOGI GUACU",
        "MOGI MIRIM": "MOGI-MIRIM",
        "ESPIRITO SANTO DO PINHAL": "ESPIRITO SANTO DO PINHAL",
        "SANTO ANTONIO DO JARDIM": "SANTO ANTONIO DO JARDIM",
        "AGUAS DE LINDOIA": "AGUAS DE LINDOIA"
    }
    df_dim["MUNICIPIO_LIMPO"] = df_dim["MUNICIPIO_LIMPO"].replace(correcoes_mapa)

    date_col = next((col for col in df_fatos.columns if 'DATA' in col or 'REG' in col), None)
    if date_col:
        df_fatos["DATA_REAL"] = pd.to_datetime(df_fatos[date_col], errors="coerce")
        df_fatos["AnoMes"] = df_fatos["DATA_REAL"].dt.strftime("%m/%Y")
    else:
        df_fatos["DATA_REAL"] = pd.NaT
        df_fatos["AnoMes"] = "01/2025"

    df_fatos = df_fatos.dropna(subset=["AnoMes"])

    # ==========================================
    # NOVO CÁLCULO GLOBAL DO NÍVEL DE ALERTA (4 CORES)
    # ==========================================
    df_regiao_global = df_dim.groupby(COL_REG).agg(
        Pop_Total=(COL_POP, 'sum'),
        Leitos_Total=(COL_LEITOS, 'sum')
    ).reset_index()

    df_regiao_global['Razao_Regional'] = (df_regiao_global['Leitos_Total'] / df_regiao_global['Pop_Total']) * 1000


    def classificar_alerta_global(razao):
        if razao < 20.0:
            return "VERMELHO (CRÍTICO)"
        elif razao < 24.0:
            return "LARANJA (ATENÇÃO)"
        elif razao < 28.0:
            return "AMARELO (ALERTA)"
        else:
            return "VERDE (BOM)"


    df_regiao_global['Alerta_Oficial_Novo'] = df_regiao_global['Razao_Regional'].apply(classificar_alerta_global)

    df_dim = df_dim.merge(df_regiao_global[[COL_REG, 'Alerta_Oficial_Novo']], on=COL_REG, how='left')
    df_dim["Alerta_Oficial"] = df_dim["Alerta_Oficial_Novo"]
    df_dim = df_dim.drop(columns=["Alerta_Oficial_Novo"])

    for feature in geojson_sp["features"]:
        feature["properties"]["name_clean"] = normalizar_texto(feature["properties"].get("name", ""))

        # ==========================================
        # 4. TELA: MENU E ABAS (VISÃO GERAL x INTERNAÇÕES)
        # ==========================================
    st.sidebar.image(r"C:\Users\judie\Desktop\nexus_health_projeto\logo.png", use_container_width=True)
    pagina_selecionada = st.sidebar.radio(label="", options=["Visão Geral", "Internações"])
    st.sidebar.markdown("---")

    # ==========================================
    # ABA 1: VISÃO GERAL (INTACTA E PERFEITA)
    # ==========================================
    if pagina_selecionada == "Visão Geral":
        st.title("Nexus Health - Centro de Comando")


        col_f1, col_f2, col_f3, col_f4 = st.columns(4)

        with col_f1:
            regioes_lista = ["Todas as Regiões"] + sorted(df_dim[COL_REG].unique().tolist())
            filtro_reg = st.selectbox(label="Região de Saúde", options=regioes_lista, key="reg_geral")

        with col_f2:
            cidades_disp = df_dim[df_dim[COL_REG] == filtro_reg][
                "MUNICIPIO_LIMPO"].unique() if filtro_reg != "Todas as Regiões" else df_dim["MUNICIPIO_LIMPO"].unique()
            filtro_mun = st.selectbox(label="Município",
                                      options=["Todos os Municípios"] + sorted(cidades_disp.tolist()), key="mun_geral")

        with col_f3:
            meses_reais = sorted(df_fatos["AnoMes"].unique().tolist())
            per_lista = ["Todo o Período"] + [m for m in meses_reais if m != "NaT"]
            filtro_per = st.selectbox(label="Período", options=per_lista, key="per_geral")

        with col_f4:
            opcoes_alerta = ["Todos"] + sorted(df_dim["Alerta_Oficial"].unique().tolist())
            filtro_alerta = st.selectbox(label="Nível de Alerta", options=opcoes_alerta, key="alerta_geral")

        st.markdown("---")

        # Aplicação dos Filtros - Visão Geral
        df_dim_filtrada = df_dim.copy()
        df_fatos_filtrada = df_fatos.copy()

        if filtro_reg != "Todas as Regiões":
            df_dim_filtrada = df_dim_filtrada[df_dim_filtrada[COL_REG] == filtro_reg]
            df_fatos_filtrada = df_fatos_filtrada[
                df_fatos_filtrada["MUNICIPIO_LIMPO"].isin(df_dim_filtrada["MUNICIPIO_LIMPO"])]
        if filtro_mun != "Todos os Municípios":
            df_dim_filtrada = df_dim_filtrada[df_dim_filtrada["MUNICIPIO_LIMPO"] == filtro_mun]
            df_fatos_filtrada = df_fatos_filtrada[df_fatos_filtrada["MUNICIPIO_LIMPO"] == filtro_mun]
        if filtro_per != "Todo o Período":
            df_fatos_filtrada = df_fatos_filtrada[df_fatos_filtrada["AnoMes"] == filtro_per]
        if filtro_alerta != "Todos":
            df_dim_filtrada = df_dim_filtrada[df_dim_filtrada["Alerta_Oficial"] == filtro_alerta]
            df_fatos_filtrada = df_fatos_filtrada[
                df_fatos_filtrada["MUNICIPIO_LIMPO"].isin(df_dim_filtrada["MUNICIPIO_LIMPO"])]

        # KPIs Superiores
        municipios_totais = df_dim_filtrada["MUNICIPIO_LIMPO"].nunique()
        leitos_totais = df_dim_filtrada[COL_LEITOS].sum()
        populacao_total = df_dim_filtrada[COL_POP].sum()
        razao_geral = (leitos_totais / populacao_total * 1000) if populacao_total > 0 else 0
        total_internacoes = df_fatos_filtrada.shape[0]

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.metric("Total Municípios", f"{municipios_totais}")
        with k2:
            st.metric("População Total", f"{populacao_total:,.0f}".replace(",", "."))
        with k3:
            st.metric("Total de Leitos", f"{leitos_totais:,.0f}")
        with k4:
            st.metric("Leitos por Mil Hab.", f"{razao_geral:.2f}")
        with k5:
            st.metric("Internações Realizadas", f"{total_internacoes:,}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Mapa de Alerta e Gráfico de Barras
        col_mapa, col_barras = st.columns([1.5, 1])

        with col_mapa:
            st.markdown("**Mapa de Alerta Geográfico (Visão Regional)**")
            if not df_dim_filtrada.empty:
                # 1. Calcula os totais de População e Leitos por Região
                df_regiao_calc = df_dim_filtrada.groupby(COL_REG).agg(
                    Pop_Total=(COL_POP, 'sum'),
                    Leitos_Total=(COL_LEITOS, 'sum')
                ).reset_index()

                # 2. Calcula a razão regional (Leitos por 1.000 habitantes)
                df_regiao_calc['Razao_Regional'] = (df_regiao_calc['Leitos_Total'] / df_regiao_calc['Pop_Total']) * 1000


                # 3. Classificação Sincronizada com o Gráfico de Barras
                def classificar_regiao(razao):
                    if razao < 20.0:
                        return "VERMELHO (CRÍTICO)"
                    elif razao < 24.0:
                        return "LARANJA (ATENÇÃO)"
                    elif razao < 28.0:
                        return "AMARELO (ALERTA)"
                    else:
                        return "VERDE (BOM)"


                df_regiao_calc['Alerta_Regional'] = df_regiao_calc['Razao_Regional'].apply(classificar_regiao)

                # 4. Junta esse status regional de volta na tabela dos municípios
                df_dim_filtrada = df_dim_filtrada.merge(df_regiao_calc[[COL_REG, 'Alerta_Regional', 'Razao_Regional']],
                                                        on=COL_REG, how='left')

                # 5. Prepara as colunas para exibir as informações ao passar o mouse
                df_dim_filtrada["Região de Saúde"] = df_dim_filtrada[COL_REG]
                df_dim_filtrada["Total Leitos Mun."] = df_dim_filtrada[COL_LEITOS]
                df_dim_filtrada["Nome Município"] = df_dim_filtrada[COL_MUN]
                df_dim_filtrada["Leitos/1k Hab (Região)"] = df_dim_filtrada["Razao_Regional"].round(2)

                # 6. Cores atualizadas para combinar perfeitamente com o gráfico de barras
                cores_alerta = {
                    "VERMELHO (CRÍTICO)": "#EF4444",
                    "LARANJA (ATENÇÃO)": "#F97316",
                    "AMARELO (ALERTA)": "#EAB308",
                    "VERDE (BOM)": "#22C55E"
                }

                # 7. Desenha o mapa
                mapa = px.choropleth_mapbox(
                    df_dim_filtrada,
                    geojson=geojson_sp,
                    locations="MUNICIPIO_LIMPO",
                    featureidkey="properties.name_clean",
                    color="Alerta_Regional",
                    color_discrete_map=cores_alerta,
                    hover_name="Nome Município",
                    hover_data={
                        "MUNICIPIO_LIMPO": False,
                        "Região de Saúde": True,
                        "Total Leitos Mun.": True,
                        "Leitos/1k Hab (Região)": True,
                        "Alerta_Regional": True,
                        "Razao_Regional": False
                    },
                    zoom=6.2,
                    center={"lat": -22.3, "lon": -48.5},
                    mapbox_style="carto-positron"
                )

                mapa.update_traces(marker_opacity=0.7, marker_line_width=0.3, marker_line_color="rgba(0,0,0,0.3)")
                mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, paper_bgcolor="rgba(0,0,0,0)",
                                   plot_bgcolor="rgba(0,0,0,0)", showlegend=True, mapbox=dict(uirevision='true'))

                st.plotly_chart(mapa, use_container_width=True, key="mapa_visao_geral")
            else:
                st.warning("Filtro vazio para o mapa.")

        with col_barras:
            st.markdown("**Regiões Leitos / Mil Hab.**")
            if not df_dim.empty:
                df_regiao_critica = df_dim.groupby(COL_REG).agg(
                    Populacao=(COL_POP, 'sum'),
                    Leitos=(COL_LEITOS, 'sum')
                ).reset_index()

                df_regiao_critica['Razao_Regiao'] = df_regiao_critica['Leitos'] / df_regiao_critica['Populacao'] * 1000


                def classificar_por_faixas_sp(razao):
                    if razao < 20.0:
                        return 'Vermelho (Crítico)'
                    elif razao < 24.0:
                        return 'Laranja (Atenção)'
                    elif razao < 28.0:
                        return 'Amarelo (Alerta)'
                    else:
                        return 'Verde (Bom)'


                df_regiao_critica['Status_Criticidade'] = df_regiao_critica['Razao_Regiao'].apply(
                    classificar_por_faixas_sp)
                df_regiao_critica = df_regiao_critica.sort_values(by="Razao_Regiao", ascending=False)

                cores_mapa_barra = {
                    'Vermelho (Crítico)': '#EF4444',
                    'Laranja (Atenção)': '#F97316',
                    'Amarelo (Alerta)': '#EAB308',
                    'Verde (Bom)': '#22C55E'
                }

                barras = px.bar(df_regiao_critica, x="Razao_Regiao", y=COL_REG, orientation='h',
                                color="Status_Criticidade", color_discrete_map=cores_mapa_barra,
                                labels={'Razao_Regiao': 'Leitos por Mil Habitantes', COL_REG: ''})

                barras.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400,
                                     paper_bgcolor="rgba(0,0,0,0)",
                                     plot_bgcolor="rgba(0,0,0,0)", legend_title_text="Nível de Alerta")
                st.plotly_chart(barras, use_container_width=True, key="barras_visao_geral")
            else:
                st.info("Dados indisponíveis para o gráfico regional.")

        st.markdown("---")

        # Tendência e Resumo Regional
        col_tendencia, col_tabela = st.columns([1.2, 1])

        with col_tendencia:
            st.markdown("**Volume Diário de Internações Observadas**")
            df_tempo_dados = df_fatos_filtrada[df_fatos_filtrada["DATA_REAL"].notna()]
            if not df_tempo_dados.empty:
                df_tempo = df_tempo_dados.groupby("DATA_REAL").size().reset_index(name="Internações")
                linha = px.line(df_tempo, x="DATA_REAL", y="Internações")
                linha.update_traces(line_color="#1D4ED8")
                linha.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                    legend_title_text="")
                st.plotly_chart(linha, use_container_width=True, key="linha_visao_geral")
            else:
                st.info("Sem histórico de datas para o filtro selecionado.")

        with col_tabela:
            st.markdown("**Resumo de Cobertura por Região de Saúde**")
            if not df_dim.empty:
                df_regiao_resumo = df_dim.groupby(COL_REG).agg(
                    População=(COL_POP, 'sum'),
                    Total_Leitos=(COL_LEITOS, 'sum'),
                    Municipios=(COL_MUN, 'nunique')
                ).reset_index()

                df_regiao_resumo['Leitos por Mil Hab.'] = (df_regiao_resumo['Total_Leitos'] / df_regiao_resumo[
                    'População']) * 1000

                tabela_final = df_regiao_resumo[
                    [COL_REG, 'Municipios', 'População', 'Total_Leitos', 'Leitos por Mil Hab.']].copy()
                tabela_final.rename(columns={
                    COL_REG: "Região de Saúde",
                    'Municipios': "Municípios",
                    'Total_Leitos': "Total de Leitos"
                }, inplace=True)

                tabela_final["Leitos por Mil Hab."] = tabela_final["Leitos por Mil Hab."].round(2)
                st.dataframe(tabela_final.sort_values(by="Leitos por Mil Hab.", ascending=False),
                             use_container_width=True, hide_index=True)


    # ==========================================
    # ABA 2: INTERNAÇÕES (APENAS FILTROS + MAPA DE CALOR)
    # ==========================================
    elif pagina_selecionada == "Internações":
        st.title("Nexus Health - Internações")


        col_f1, col_f2, col_f3, col_f4 = st.columns(4)

        with col_f1:
            regioes_lista_int = ["Todas as Regiões"] + sorted(df_dim[COL_REG].unique().tolist())
            filtro_reg_int = st.selectbox(label="Região de Saúde", options=regioes_lista_int, key="reg_int")

        with col_f2:
            cidades_disp_int = df_dim[df_dim[COL_REG] == filtro_reg_int][
                "MUNICIPIO_LIMPO"].unique() if filtro_reg_int != "Todas as Regiões" else df_dim[
                "MUNICIPIO_LIMPO"].unique()
            filtro_mun_int = st.selectbox(label="Município",
                                          options=["Todos os Municípios"] + sorted(cidades_disp_int.tolist()),
                                          key="mun_int")

        with col_f3:
            meses_reais_int = sorted(df_fatos["AnoMes"].unique().tolist())
            per_lista_int = ["Todo o Período"] + [m for m in meses_reais_int if m != "NaT"]
            filtro_per_int = st.selectbox(label="Período", options=per_lista_int, key="per_int")

        with col_f4:
            opcoes_alerta_int = ["Todos"] + sorted(df_dim["Alerta_Oficial"].unique().tolist())
            filtro_alerta_int = st.selectbox(label="Nível de Alerta (Tabela)", options=opcoes_alerta_int,
                                             key="alerta_int")

        st.markdown("---")

        # Aplicação dos Filtros - Internações
        df_dim_filtrada_int = df_dim.copy()
        df_fatos_filtrada_int = df_fatos.copy()

        if filtro_reg_int != "Todas as Regiões":
            df_dim_filtrada_int = df_dim_filtrada_int[df_dim_filtrada_int[COL_REG] == filtro_reg_int]
            df_fatos_filtrada_int = df_fatos_filtrada_int[
                df_fatos_filtrada_int["MUNICIPIO_LIMPO"].isin(df_dim_filtrada_int["MUNICIPIO_LIMPO"])]
        if filtro_mun_int != "Todos os Municípios":
            df_dim_filtrada_int = df_dim_filtrada_int[df_dim_filtrada_int["MUNICIPIO_LIMPO"] == filtro_mun_int]
            df_fatos_filtrada_int = df_fatos_filtrada_int[df_fatos_filtrada_int["MUNICIPIO_LIMPO"] == filtro_mun_int]
        if filtro_per_int != "Todo o Período":
            df_fatos_filtrada_int = df_fatos_filtrada_int[df_fatos_filtrada_int["AnoMes"] == filtro_per_int]
        if filtro_alerta_int != "Todos":
            df_dim_filtrada_int = df_dim_filtrada_int[df_dim_filtrada_int["Alerta_Oficial"] == filtro_alerta_int]
            df_fatos_filtrada_int = df_fatos_filtrada_int[
                df_fatos_filtrada_int["MUNICIPIO_LIMPO"].isin(df_dim_filtrada_int["MUNICIPIO_LIMPO"])]

        # ==========================================
        # KPI: TOTAL DE INTERNAÇÕES FILTRADAS
        # ==========================================
        total_internacoes_int = df_fatos_filtrada_int.shape[0]

        col_kpi1, col_kpi2, col_kpi3 = st.columns([1, 2, 2])
        with col_kpi1:
            st.metric("Total de Internações", f"{total_internacoes_int:,}".replace(",", "."))

        st.markdown("<br>", unsafe_allow_html=True)

        # Processamento de Dados para os Gráficos abaixo...
        df_contagem_internacoes = df_fatos_filtrada_int.groupby("MUNICIPIO_LIMPO").size().reset_index(
            name="Qtd_Internacoes")
        df_mapa_calor = df_dim_filtrada_int.merge(df_contagem_internacoes, on="MUNICIPIO_LIMPO", how="left")
        df_mapa_calor["Qtd_Internacoes"] = df_mapa_calor["Qtd_Internacoes"].fillna(0)

        df_regiao_internacoes = df_mapa_calor.groupby(COL_REG)["Qtd_Internacoes"].sum().reset_index()
        df_regiao_internacoes = df_regiao_internacoes.sort_values(by="Qtd_Internacoes", ascending=True)

        # ==========================================
        # DUAS COLUNAS MESTRAS DA PÁGINA DE INTERNAÇÕES
        # ==========================================
        col_esq, col_dir = st.columns([1.4, 1])

        # ------------------------------------------
        # COLUNA ESQUERDA: MAPA DE CALOR + TABELA DE CID
        # ------------------------------------------
        with col_esq:
            st.markdown("### Densidade de Internações por Município")
            fig_calor = px.choropleth(
                df_mapa_calor,
                geojson=geojson_sp,
                locations="MUNICIPIO_LIMPO",
                featureidkey="properties.name_clean",
                color="Qtd_Internacoes",
                color_continuous_scale=["#ffeda0", "#feb24c", "#f03b20"],
                hover_name="MUNICIPIO",
                hover_data={"MUNICIPIO_LIMPO": False, "Qtd_Internacoes": True, "REGIAO": True}
            )
            fig_calor.update_geos(fitbounds="locations", visible=False)
            fig_calor.update_traces(marker_line_width=0.3, marker_line_color="rgba(0,0,0,0.3)")
            fig_calor.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_colorbar=dict(title="Nº Internações", thickness=15, len=0.8)
            )
            st.plotly_chart(fig_calor, use_container_width=True, key="mapa_calor_internacoes")

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("### 📋 CIDs Mais Frequentes nas Internações")
            if not df_fatos_filtrada_int.empty and "CID" in df_fatos_filtrada_int.columns:
                def carregar_tabela_cid():
                    try:
                        return pd.read_csv("TAB_CID.csv")
                    except:
                        try:
                            return pd.read_excel("TAB_CID.xlsx")
                        except:
                            return pd.DataFrame(columns=["CID", "Descrição"])


                df_cid_tab = carregar_tabela_cid()
                cid_counts = df_fatos_filtrada_int["CID"].value_counts().reset_index()
                cid_counts.columns = ["CID", "Quantidade"]

                descricoes = []
                for cid in cid_counts["CID"]:
                    desc = "Condição especializada"
                    if not df_cid_tab.empty:
                        df_cid_tab.columns = [str(c).strip() for c in df_cid_tab.columns]
                        col_cid_ref = next((c for c in df_cid_tab.columns if 'CID' in c.upper()), df_cid_tab.columns[0])
                        col_desc_ref = next((c for c in df_cid_tab.columns if 'DESC' in c.upper()),
                                            df_cid_tab.columns[-1])

                        match = df_cid_tab[df_cid_tab[col_cid_ref].astype(str).str.upper() == str(cid).upper()]
                        if not match.empty:
                            desc = str(match.iloc[0][col_desc_ref])
                        else:
                            prefix = str(cid).split('.')[0]
                            match_prefix = df_cid_tab[
                                df_cid_tab[col_cid_ref].astype(str).str.contains(prefix, na=False)]
                            if not match_prefix.empty:
                                desc = str(match_prefix.iloc[0][col_desc_ref])
                    descricoes.append(desc)

                cid_counts["Descrição"] = descricoes
                tabela_cid_final = cid_counts[["CID", "Descrição", "Quantidade"]]

                # 1. Converte a coluna para texto (dribla a teimosia do Streamlit com números)
                tabela_cid_final["Quantidade"] = tabela_cid_final["Quantidade"].astype(str)

                # 2. Aplica o estilo com a sintaxe correta do Pandas
                tabela_formatada = tabela_cid_final.head(10).style.set_properties(
                    subset=["Quantidade"],
                    **{"text-align": "center"}
                )

                st.dataframe(
                    tabela_formatada,
                    use_container_width=True,
                    hide_index=True,
                    height=380
                )
            else:
                st.info("Nenhum dado de CID disponível para o filtro atual.")

        # ------------------------------------------
        # COLUNA DIREITA: BARRAS REGIONAIS + EVOLUÇÃO TEMPORAL
        # ------------------------------------------
        with col_dir:
            st.markdown("### Internações por Região de Saúde")
            fig_barras_regiao = px.bar(
                df_regiao_internacoes,
                x="Qtd_Internacoes",
                y=COL_REG,
                orientation='h',
                color="Qtd_Internacoes",
                color_continuous_scale=["#ffeda0", "#feb24c", "#f03b20"],
                labels={"Qtd_Internacoes": "Total de Internações", COL_REG: "Região de Saúde"}
            )
            fig_barras_regiao.update_layout(
                margin={"r": 0, "t": 20, "l": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=430,
                xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
                yaxis=dict(showgrid=False),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_barras_regiao, use_container_width=True, key="barras_internacoes_regiao")

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("### Evolução Diária por Tipo de Internação")
            if not df_fatos_filtrada_int.empty and "DATA_REAL" in df_fatos_filtrada_int.columns and "TIPO_INTERNACAO" in df_fatos_filtrada_int.columns:
                df_tipo_tempo = (
                    df_fatos_filtrada_int.groupby(["DATA_REAL", "TIPO_INTERNACAO"])
                    .size()
                    .reset_index(name="Quantidade")
                )
                fig_linha_tipo = px.line(
                    df_tipo_tempo,
                    x="DATA_REAL",
                    y="Quantidade",
                    color="TIPO_INTERNACAO",
                    labels={"DATA_REAL": "Data", "Quantidade": "Quantidade de Internações",
                            "TIPO_INTERNACAO": "Tipo de Internação"}
                )
                fig_linha_tipo.update_layout(
                    margin={"r": 0, "t": 20, "l": 0, "b": 0},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=380,
                    xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
                    legend_title_text="Tipo de Internação"
                )
                st.plotly_chart(fig_linha_tipo, use_container_width=True, key="linha_tipo_internacao_int")
            else:
                st.info("Dados de data ou tipo de internação indisponíveis para o filtro selecionado.")
# ==========================================
# SEÇÃO DO CHAT COM A IA (GLOBAL)
# ==========================================
st.markdown("---")
st.subheader("💬 Nexus AI - Assistente Inteligente de Saúde Pública")
st.write("Tire dúvidas ou analise os indicadores de internações de forma conversacional.")

pergunta_usuario = st.text_input("Faça sua pergunta sobre os dados de saúde:",
                                 placeholder="Ex: Qual o panorama geral?")

if st.button("Perguntar ao Nexus AI"):
    if pergunta_usuario.strip():
        with st.spinner("O Nexus AI está analisando os dados..."):
            resposta = perguntar_ao_nexus_ia(pergunta_usuario)
            st.success("**Resposta do Assistente:**")
            st.write(resposta)
    else:
        st.warning("Por favor, digite uma pergunta válida antes de consultar.")