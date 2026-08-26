import io
from datetime import date
import pandas as pd
import streamlit as st

COLS = ["ticker", "operacao", "preco", "quantidade", "data"]


def main():
    st.set_page_config(page_title="Registro de Operações", page_icon="📈", layout="wide")
    st.title("📈 Registro de Operações de Compra/Venda")

    init_state()
    render_sidebar_import_export()

    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        render_form_nova_operacao()
    with col_right:
        render_posicao_carteira()

    st.divider()
    render_tabela_e_filtros()


def init_state() -> None:
    if "ops" not in st.session_state:
        st.session_state.ops = new_empty_df()
    if "msg" not in st.session_state:
        st.session_state.msg = ""


def new_empty_df() -> pd.DataFrame:
    return ensure_schema(pd.DataFrame(columns=COLS))


def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas e tipos básicos; converte data para datetime"""
    for c in COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[COLS].copy()

    df["ticker"] = df["ticker"].astype("string").str.upper()
    df["operacao"] = df["operacao"].astype("string").str.lower()
    df["preco"] = pd.to_numeric(df["preco"], errors="coerce")
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").astype("Int64")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    return df


def render_sidebar_import_export() -> None:
    st.sidebar.header("🗃️ Dados")

    uploaded = st.sidebar.file_uploader("Importar CSV", type=["csv"])
    if uploaded is not None:
        try:
            imported = pd.read_csv(uploaded)
            imported = ensure_schema(imported)
            st.session_state.ops = pd.concat([st.session_state.ops, imported], ignore_index=True)
            st.sidebar.success(f"Importado: {len(imported)} registro(s).")
        except Exception as e:
            st.sidebar.error(f"Falha ao importar CSV: {e}")

    if not st.session_state.ops.empty:
        st.sidebar.download_button(
            "Baixar operações (CSV)",
            data=df_to_csv_bytes(st.session_state.ops),
            file_name="operacoes.csv",
            mime="text/csv",
        )
    st.sidebar.caption("Colunas esperadas: ticker, operacao, preco, quantidade, data")


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Exporta o DF como CSV (data em YYYY-MM-DD)."""
    buf = io.StringIO()
    out = df.copy()
    out["data"] = out["data"].dt.date.astype("string")
    out.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue().encode("utf-8")


def render_form_nova_operacao() -> None:
    st.subheader("➕ Nova operação")

    if st.session_state.msg:
        st.success(st.session_state.msg)
        st.session_state.msg = ""  # Limpa a mensagem após exibir

    with st.form("form_op", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ticker = st.text_input("Ticker", placeholder="Ex: PETR4").strip().upper()
        with c2:
            operacao = st.selectbox("Operação", ["compra", "venda"])

        c3, c4, c5 = st.columns(3)
        with c3:
            preco = st.number_input("Preço (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        with c4:
            quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
        with c5:
            data_op = st.date_input("Data", value=date.today())

        submitted = st.form_submit_button("Registrar Operação")

    if submitted:
        if not ticker:
            st.error("O Ticker é obrigatório.")
            return

        row = pd.DataFrame([{
            "ticker": ticker,
            "operacao": operacao,
            "preco": float(preco),
            "quantidade": int(quantidade),
            "data": pd.to_datetime(data_op),
        }])

        st.session_state.ops = pd.concat([st.session_state.ops, ensure_schema(row)], ignore_index=True)
        st.session_state.msg = f"Operação registrada: {quantidade}x {ticker} ({operacao.capitalize()})."
        st.rerun()


def render_posicao_carteira() -> None:
    st.subheader("🧾 Posição da Carteira")

    pos = compute_posicao_carteira(st.session_state.ops)

    if pos.empty or pos["quantidade"].sum() == 0:
        st.info("Sua carteira está vazia no momento.")
        return

    # Exibe métricas rápidas
    total_tickers = len(pos[pos["quantidade"] > 0])
    total_qtd = int(pos["quantidade"].sum())

    c1, c2 = st.columns(2)
    c1.metric("Ativos na carteira", total_tickers)
    c2.metric("Ações totais", total_qtd)

    # Configuração visual da tabela
    st.dataframe(
        pos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ticker": "Ticker",
            "quantidade": st.column_config.NumberColumn("Quantidade Atual")
        }
    )


def compute_posicao_carteira(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a posição líquida consolidada por ticker."""
    if df.empty:
        return pd.DataFrame(columns=["ticker", "quantidade"])

    clean = df.dropna(subset=["ticker", "operacao", "quantidade"]).copy()

    # Atribui sinal matemático baseado na operação
    clean["sinal"] = clean["operacao"].map({"compra": 1, "venda": -1})
    clean = clean.dropna(subset=["sinal"])

    clean["quantidade_signed"] = clean["quantidade"] * clean["sinal"]

    pos = (
        clean.groupby("ticker", as_index=False)["quantidade_signed"]
        .sum()
        .rename(columns={"quantidade_signed": "quantidade"})
    )

    # Remove ativos que foram totalmente vendidos (posição = 0)
    pos = pos[pos["quantidade"] > 0].sort_values("ticker", kind="stable").reset_index(drop=True)
    return pos


def render_tabela_e_filtros() -> None:
    st.subheader("🗂️ Histórico de Operações")
    df = st.session_state.ops.copy()

    if df.empty:
        st.write("Nenhuma operação registrada ainda.")
        return

    # Filtros
    f1, f2 = st.columns(2)
    with f1:
        tickers = sorted(df["ticker"].dropna().unique().tolist())
        ticker_sel = st.multiselect("Filtrar por Ticker", tickers, default=[])
    with f2:
        op_sel = st.multiselect("Filtrar por Operação", ["compra", "venda"], default=[])

    # Aplicando filtros
    filtered = df.copy()
    if ticker_sel:
        filtered = filtered[filtered["ticker"].isin(ticker_sel)]
    if op_sel:
        filtered = filtered[filtered["operacao"].isin(op_sel)]

    # Renderização da tabela formatada
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ticker": "Ticker",
            "operacao": "Operação",
            "preco": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
            "quantidade": st.column_config.NumberColumn("Quantidade"),
            "data": st.column_config.DateColumn("Data da Operação", format="DD/MM/YYYY")
        }
    )


if __name__ == "__main__":
    main()