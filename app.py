import streamlit as st
import sqlite3
import pandas as pd
import json
import datetime
import os

DB_NAME = "eventos.db"
CIDADES_JSON = "cidades.json"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nome_evento TEXT NOT NULL,
            local TEXT,
            cidade TEXT,
            estado TEXT,
            data_inicio DATE,
            data_fim DATE,
            qtd_pessoas INTEGER,
            descricao TEXT,
            categoria TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

def register_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        conn.close()
        return True, "Usuário registrado com sucesso."
    except Exception as e:
        conn.close()
        return False, str(e)

def login_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return True, user[0]
    return False, None

def insert_event(
    user_id, nome_evento, local, cidade, estado,
    data_inicio, data_fim, qtd_pessoas, descricao, categoria
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (
            user_id, nome_evento, local, cidade, estado,
            data_inicio, data_fim, qtd_pessoas, descricao, categoria
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, nome_evento, local, cidade, estado,
        data_inicio, data_fim, qtd_pessoas, descricao, categoria
    ))
    conn.commit()
    conn.close()

def fetch_events(user_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT * FROM events WHERE user_id = ?", conn, params=[user_id]
    )
    conn.close()
    return df

def carregar_cidades():
    if not os.path.exists(CIDADES_JSON):
        return []

    with open(CIDADES_JSON, "r", encoding="utf-8") as f:
        raw = json.load(f)

    lista = raw["data"]  # Se seu JSON tem a chave "data"
    cidades_filtradas = []
    for item in lista:
        cid_nome = item["Nome"]
        cid_uf = item["Uf"]
        # Monta string "Cidade (UF)" para exibir no selectbox
        cidades_filtradas.append(f"{cid_nome} ({cid_uf})")
    return sorted(cidades_filtradas)  # ordena opcionalmente

def main():
    st.set_page_config(page_title="Eventos no Brasil", layout="wide")
    st.title("MVP - Cadastro de Eventos e Feiras")

    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None

    if not st.session_state.logged_in:
        st.header("Login ou Registrar")
        tab1, tab2 = st.tabs(["Login", "Registrar"])

        with tab1:
            st.subheader("Fazer Login")
            login_username = st.text_input("Usuário")
            login_password = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                ok, user_id = login_user(login_username, login_password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = login_username
                    st.success(f"Bem-vindo(a), {login_username}!")
                    # Se sua versão do Streamlit suportar:
                    # st.experimental_rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

        with tab2:
            st.subheader("Registrar Novo Usuário")
            reg_username = st.text_input("Novo Usuário")
            reg_password = st.text_input("Nova Senha", type="password")
            if st.button("Registrar"):
                if reg_username and reg_password:
                    success, msg = register_user(reg_username, reg_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(f"Erro ao registrar: {msg}")
                else:
                    st.warning("Por favor, preencha usuário e senha.")
    else:
        st.sidebar.write(f"Olá, {st.session_state.username}!")
        if st.sidebar.button("Sair"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            # st.experimental_rerun()  # se disponível
            st.experimental_set_query_params()  # Força rerun
            st.stop()

        st.header("Cadastrar Novo Evento")

        lista_cidades = carregar_cidades()

        with st.form("form_evento"):
            nome_evento = st.text_input("Nome do Evento")
            local = st.text_input("Local (endereço, p.ex.)")

            # Apenas 1 selectbox que mostra "Cidade (UF)"
            cidade_select = st.selectbox("Cidade", lista_cidades)
            # Vamos extrair o nome e o UF
            # Ex: "São Paulo (SP)" -> cid_nome = "São Paulo", uf = "SP"
            partes = cidade_select.rsplit(" (", 1)
            cid_nome = partes[0]
            uf = partes[1].replace(")", "")

            # Aqui não mostramos "Cidade Selecionada" nem "Estado", pois você pediu para remover

            data_inicio = st.date_input("Data de Início", value=datetime.date.today())
            data_fim = st.date_input("Data de Fim", value=datetime.date.today())
            qtd_pessoas = st.number_input("Quantidade Esperada de Pessoas", min_value=1)
            descricao = st.text_area("Descrição do Evento")
            categoria = st.selectbox("Categoria", ["Show", "Congresso", "Feira", "Workshop", "Outro"])

            submit_event = st.form_submit_button("Cadastrar Evento")
            if submit_event:
                try:
                    insert_event(
                        user_id=st.session_state.user_id,
                        nome_evento=nome_evento,
                        local=local,
                        cidade=cid_nome,
                        estado=uf,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        qtd_pessoas=qtd_pessoas,
                        descricao=descricao,
                        categoria=categoria
                    )
                    st.success("Evento cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao cadastrar evento: {e}")

        st.header("Meus Eventos Cadastrados")
        try:
            events_df = fetch_events(st.session_state.user_id)
            if not events_df.empty:
                st.dataframe(events_df)
            else:
                st.info("Nenhum evento cadastrado ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")


if __name__ == "__main__":
    main()
