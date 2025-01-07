import streamlit as st
import sqlite3
import pandas as pd
import json
import datetime
import os

DB_NAME = "eventos.db"
CIDADES_JSON = "cidades.json"

def init_db():
    """Inicializa (ou atualiza) o banco de dados."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Tabela de eventos (já incluindo a nova coluna segmento)
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
            segmento TEXT,   -- Adicionamos a coluna segmento
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Se a tabela já existia antes, mas não tinha o campo 'segmento', 
    # podemos garantir com um ALTER TABLE (seguro apenas para SQLite):
    cursor.execute("PRAGMA table_info(events)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    if "segmento" not in colunas_existentes:
        cursor.execute("ALTER TABLE events ADD COLUMN segmento TEXT")

    conn.commit()
    conn.close()

def register_user(username, password):
    """Registra um novo usuário no banco."""
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
    """Faz login do usuário, retornando (True, user_id) em caso de sucesso."""
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
    data_inicio, data_fim, qtd_pessoas, descricao, categoria, segmento
):
    """Insere um novo evento no banco."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (
            user_id, nome_evento, local, cidade, estado,
            data_inicio, data_fim, qtd_pessoas, descricao, categoria, segmento
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, nome_evento, local, cidade, estado,
        data_inicio, data_fim, qtd_pessoas, descricao, categoria, segmento
    ))
    conn.commit()
    conn.close()

def fetch_events(user_id):
    """Busca todos os eventos de um determinado usuário."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT * FROM events WHERE user_id = ?",
        conn,
        params=[user_id]
    )
    conn.close()
    return df

def update_event(
    event_id, nome_evento, local, cidade, estado,
    data_inicio, data_fim, qtd_pessoas, descricao,
    categoria, segmento
):
    """Atualiza os dados de um evento já cadastrado."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE events
        SET
            nome_evento = ?,
            local = ?,
            cidade = ?,
            estado = ?,
            data_inicio = ?,
            data_fim = ?,
            qtd_pessoas = ?,
            descricao = ?,
            categoria = ?,
            segmento = ?
        WHERE id = ?
    """, (
        nome_evento, local, cidade, estado, data_inicio,
        data_fim, qtd_pessoas, descricao, categoria, segmento, event_id
    ))
    conn.commit()
    conn.close()

def carregar_cidades():
    """Carrega a lista de cidades do arquivo JSON."""
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

    # Sessão de login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None

    # Se não está logado, mostra tela de Login/Registro
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
                    st.experimental_rerun()
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
        # Menu lateral com opção de Sair
        st.sidebar.write(f"Olá, {st.session_state.username}!")
        if st.sidebar.button("Sair"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.experimental_set_query_params()  # Força a recarregar sem parâmetros
            st.stop()

        # =====================================
        # 1) FORMULÁRIO PARA CADASTRAR NOVO EVENTO
        # =====================================
        st.header("Cadastrar Novo Evento")
        lista_cidades = carregar_cidades()

        with st.form("form_evento", clear_on_submit=True):
            # clear_on_submit=True já limpa automaticamente quando o form é enviado
            nome_evento = st.text_input("Nome do Evento")
            local = st.text_input("Local (endereço, p.ex.)")

            # Selectbox de cidades
            cidade_select = st.selectbox("Cidade", lista_cidades)
            # Exemplo: "São Paulo (SP)" -> partes[0] = São Paulo, partes[1] = SP)
            partes = cidade_select.rsplit(" (", 1)
            cid_nome = partes[0]
            uf = partes[1].replace(")", "")

            data_inicio = st.date_input("Data de Início", value=datetime.date.today())
            data_fim = st.date_input("Data de Fim", value=datetime.date.today())
            qtd_pessoas = st.number_input("Quantidade Esperada de Pessoas", min_value=1)
            descricao = st.text_area("Descrição do Evento")
            categoria = st.selectbox(
                "Categoria",
                ["Show", "Congresso", "Feira", "Workshop", "Outro"]
            )

            # Novo campo "Segmento"
            segmento = st.text_input("Segmento do Evento (ex: Tecnologia, Saúde, etc.)")

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
                        categoria=categoria,
                        segmento=segmento
                    )
                    st.success("Evento cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao cadastrar evento: {e}")

        # =====================================
        # 2) MOSTRAR LISTA DE EVENTOS E EDITAR
        # =====================================
        st.header("Meus Eventos Cadastrados")

        try:
            events_df = fetch_events(st.session_state.user_id)
            if not events_df.empty:
                # Ocultamos a coluna user_id e deixamos só o ID (número do evento)
                # e demais colunas relevantes
                # Renomeando a coluna 'id' para "N° Evento"
                df_display = events_df.copy()
                # Remove a coluna user_id da visualização
                if "user_id" in df_display.columns:
                    df_display.drop("user_id", axis=1, inplace=True)

                # Renomeia a coluna id -> N° Evento
                if "id" in df_display.columns:
                    df_display.rename(columns={"id": "N° Evento"}, inplace=True)

                st.dataframe(df_display)

                # Formulário para editar um evento existente
                st.subheader("Editar Evento Existente")

                # Primeiro, o usuário seleciona o ID do evento (N° Evento)
                # Precisamos do original 'id' no DataFrame original (events_df).
                lista_ids = events_df["id"].tolist()
                selected_id = st.selectbox("Selecione o ID do evento para editar:", lista_ids)

                if selected_id:
                    # Obtemos a linha correspondente no DF original
                    row = events_df[events_df["id"] == selected_id].iloc[0]

                    with st.form("form_editar_evento", clear_on_submit=False):
                        edit_nome_evento = st.text_input("Nome do Evento", value=row["nome_evento"])
                        edit_local = st.text_input("Local", value=row["local"])
                        
                        # Ajustar cidade e estado novamente em selectbox
                        edit_cidade_estado = f"{row['cidade']} ({row['estado']})"
                        if edit_cidade_estado not in lista_cidades:
                            lista_cidades.append(edit_cidade_estado)
                            lista_cidades = sorted(set(lista_cidades))  # remove duplicatas e ordena
                        edit_cidade_select = st.selectbox("Cidade", lista_cidades, index=lista_cidades.index(edit_cidade_estado))
                        partes = edit_cidade_select.rsplit(" (", 1)
                        edit_cid_nome = partes[0]
                        edit_uf = partes[1].replace(")", "")

                        # Datas
                        if isinstance(row["data_inicio"], str):
                            # Converter string para datetime.date
                            row_data_inicio = datetime.datetime.strptime(row["data_inicio"], "%Y-%m-%d").date()
                        else:
                            row_data_inicio = row["data_inicio"]
                        if isinstance(row["data_fim"], str):
                            row_data_fim = datetime.datetime.strptime(row["data_fim"], "%Y-%m-%d").date()
                        else:
                            row_data_fim = row["data_fim"]

                        edit_data_inicio = st.date_input("Data de Início", value=row_data_inicio)
                        edit_data_fim = st.date_input("Data de Fim", value=row_data_fim)
                        edit_qtd_pessoas = st.number_input(
                            "Quantidade Esperada de Pessoas",
                            min_value=1,
                            value=int(row["qtd_pessoas"]) if row["qtd_pessoas"] else 1
                        )
                        edit_descricao = st.text_area("Descrição do Evento", value=row["descricao"])
                        edit_categoria = st.selectbox(
                            "Categoria",
                            ["Show", "Congresso", "Feira", "Workshop", "Outro"],
                            index=["Show", "Congresso", "Feira", "Workshop", "Outro"].index(row["categoria"])
                            if row["categoria"] in ["Show","Congresso","Feira","Workshop","Outro"] else 0
                        )
                        # Segmento
                        edit_segmento = st.text_input(
                            "Segmento do Evento",
                            value=row["segmento"] if row["segmento"] else ""
                        )

                        submitted_edicao = st.form_submit_button("Salvar Alterações")
                        if submitted_edicao:
                            try:
                                update_event(
                                    event_id=selected_id,
                                    nome_evento=edit_nome_evento,
                                    local=edit_local,
                                    cidade=edit_cid_nome,
                                    estado=edit_uf,
                                    data_inicio=edit_data_inicio,
                                    data_fim=edit_data_fim,
                                    qtd_pessoas=edit_qtd_pessoas,
                                    descricao=edit_descricao,
                                    categoria=edit_categoria,
                                    segmento=edit_segmento
                                )
                                st.success("Evento atualizado com sucesso!")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar evento: {e}")

            else:
                st.info("Nenhum evento cadastrado ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

if __name__ == "__main__":
    main()
