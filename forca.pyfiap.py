import streamlit as st


def main():
    init()
    st.title("Jogo da Forca (Streamlit)")
    if render_setup():
        process_guess_action()
        if not render_end_game():
            render_game_status()
            render_guess_form()


def init():
    defaults = {
        "remaining_attempts": 6,
        "guessed_letters": set(),
        "tried_letters": set(),
        "game_started": False,
        "secret_word": "",
        "hint": "",
        "end_game": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_setup() -> bool:
    """
    Renderiza a etapa de configuração do jogo (palavra secreta + dica)
    Retorna:
        True  -> configuração concluída (jogo iniciado)
        False -> ainda na tela de configuração
    """
    if st.session_state.game_started:
        return True

    st.session_state.remaining_attempts = 6
    st.session_state.guessed_letters = set()
    st.session_state.tried_letters = set()
    st.session_state.game_started = False
    st.session_state.secret_word = ""
    st.session_state.hint = ""
    st.session_state.letter = ""
    st.session_state.word = ""
    st.session_state.ui_feedback = ""

    st.header("Configuração do jogo")
    with st.form("setup_form", clear_on_submit=False):
        secret_word = st.text_input(
            "Palavra secreta",
            type="password",
            placeholder="Digite a palavra secreta (apenas letras)"
        )
        hint = st.text_area(
            "Dica",
            placeholder="Digite uma dica curta para ajudar os jogadores"
        )
        submitted = st.form_submit_button("Iniciar jogo")

    if submitted:
        sw = secret_word.strip().lower()
        if not sw:
            st.error("A palavra secreta não pode estar vazia.")
            return False
        if not all(ch.isalpha() or ch.isspace() for ch in sw):
            st.error("A palavra secreta deve conter apenas letras e espaços.")
            return False
        st.session_state.secret_word = sw
        st.session_state.hint = hint.strip()
        st.session_state.game_started = True
        st.success("Configuração concluída! O jogo pode começar.")
        st.rerun()
    return False


def render_game_status() -> None:
    """
    Renderiza o estado atual do jogo:
    - lacunas/letras descobertas da palavra secreta
    - tentativas restantes
    - letras já tentadas (corretas e incorretas)
    """
    guessed_letters: set = st.session_state.guessed_letters
    masked_chars = []
    for ch in st.session_state.secret_word:
        if ch.isspace():
            masked_chars.append(" ")
        else:
            masked_chars.append(ch if ch.lower() in guessed_letters else "_")
    masked_word = " ".join(masked_chars)

    st.subheader("Status do jogo")
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.write("**Palavra:**")
        st.markdown(
            f"<div style='font-size: 28px; letter-spacing: 2px; font-family: monospace;'>{masked_word}</div>",
            unsafe_allow_html=True
        )
    with col_right:
        st.write("**Tentativas restantes:**")
        st.info(f"{st.session_state.remaining_attempts}")
        if st.session_state.remaining_attempts <= 1:
            st.info(f"Dica: {st.session_state.hint}")

    tried_letters: set = st.session_state.tried_letters
    st.write("**Letras tentadas:**", " ".join(sorted(tried_letters)))

    correct_tried = sorted([c for c in tried_letters if c in guessed_letters])
    wrong_tried = sorted([c for c in tried_letters if c not in guessed_letters])
    cols = st.columns(2)
    with cols[0]:
        st.write("**Corretas:**", " ".join(correct_tried) if correct_tried else "-")
    with cols[1]:
        st.write("**Incorretas:**", " ".join(wrong_tried) if wrong_tried else "-")


def render_guess_form():
    st.subheader("Faça sua tentativa")
    if len(st.session_state.ui_feedback):
        st.success(st.session_state.ui_feedback)
    with st.form("guess_form", clear_on_submit=True):
        st.text_input("Tentar uma letra", max_chars=1, placeholder="Ex: a", key='letter')
        st.form_submit_button("Enviar tentativa")


def process_guess_action() -> None:
    """
    Processa a tentativa do usuário e atualiza o estado do jogo.
    """
    if "letter" in st.session_state and len(st.session_state.letter):
        if len(st.session_state.letter) != 1 or not st.session_state.letter.isalpha():
            st.session_state.ui_feedback = "Digite apenas UMA letra (a–z)."
            return
        letter = st.session_state.letter.lower()
        st.session_state.letter = ''
        if letter in st.session_state.tried_letters:
            st.session_state.ui_feedback = f"Você já tentou a letra '{letter}'."
            return
        st.session_state.tried_letters.add(letter)
        if letter in st.session_state.secret_word:
            st.session_state.guessed_letters.add(letter)
            st.session_state.ui_feedback = f"Boa! A letra '{letter}' existe na palavra."
        else:
            st.session_state.remaining_attempts -= 1
            st.session_state.ui_feedback = f"A letra '{letter}' não existe. Você perdeu 1 tentativa."

    secret_letters = {ch.lower() for ch in st.session_state.secret_word if ch.isalpha()}
    if secret_letters.issubset(st.session_state.guessed_letters):
        st.session_state.end_game = "win"
    if st.session_state.remaining_attempts <= 0:
        st.session_state.end_game = "loss"


def render_end_game() -> bool:
    if st.session_state.end_game == "win":
        st.balloons()
        st.success(f"Parabéns! Você venceu! A palavra era: {st.session_state.secret_word}")
        if st.button("Jogar novamente"):
            st.session_state.clear()
            st.rerun()
        return True
    elif st.session_state.end_game == "loss":
        st.error(f"Fim de jogo! Você perdeu. A palavra era: {st.session_state.secret_word}")
        if st.button("Tentar novamente"):
            st.session_state.clear()
            st.rerun()
        return True
    return False


if __name__ == "__main__":
    main()