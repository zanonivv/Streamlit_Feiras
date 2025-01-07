import streamlit as st
import sqlite3
import pandas as pd
import json
import datetime
import os

DB_NAME = "eventos.db"
CIDADES_JSON = "cidades.json"

# =============================================================================
# FUNÇÕES DE BANCO DE DADOS E MANIPULAÇÃO
# =============================================================================

def init_db():
    """Inicializa o banco de dados, criando tabelas caso não existam."""
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
            segmento TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("PRAGMA table_info(events)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    if "segmento" not in colunas_existentes:
        cursor.execute("ALTER TABLE events ADD COLUMN segmento TEXT")

    conn.commit()
    conn.close()

@st.cache_data
def carregar_cidades():
    """Lê o arquivo JSON e retorna uma lista de strings no formato "Cidade (UF)"."""
    if not os.path.exists(CIDADES_JSON):
        return []

    with open(CIDADES_JSON, "r", encoding="utf-8") as f:
        raw = json.load(f)

    lista = raw["data"]
    cidades_filtradas = []
    for item in lista:
        cid_nome = item["Nome"]
        cid_uf = item["Uf"]
        cidades_filtradas.append(f"{cid_nome} ({cid_uf})")
    return sorted(cidades_filtradas)

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
        msg = "Usuário registrado com sucesso."
        return True, msg
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def login_user(username, password):
    """Tenta logar o usuário."""
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

def insert_event(user_id, nome_evento, local, cidade, estado,
                data_inicio, data_fim, qtd_pessoas, descricao, categoria, segmento):
    """Insere um novo evento no banco."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
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
    except Exception as e:
        raise e
    finally:
        conn.close()

def fetch_events(user_id):
    """Busca todos os eventos de um usuário específico."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT * FROM events WHERE user_id = ?",
        conn,
        params=[user_id]
    )
    conn.close()
    return df

def update_event(event_id, nome_evento, local, cidade, estado,
                data_inicio, data_fim, qtd_pessoas, descricao, categoria, segmento):
    """Atualiza dados de um evento existente."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
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
            nome_evento, local, cidade, estado,
            data_inicio, data_fim, qtd_pessoas, descricao,
            categoria, segmento, event_id
        ))
        conn.commit()
    except Exception as e:
        raise e
    finally:
        conn.close()

        # =============================================================================
# APLICAÇÃO STREAMLIT
# =============================================================================

def main():
    st.set_page_config(page_title="Eventos no Brasil", layout="wide")
    init_db()

    # Variáveis de sessão
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None

    if "edit_event_id" not in st.session_state:
        st.session_state.edit_event_id = None

    # ================ SE NÃO ESTIVER LOGADO ================
    if not st.session_state.logged_in:
        st.title("Login ou Registrar")

        tab1, tab2 = st.tabs(["Login", "Registrar"])
        with tab1:
            st.subheader("Fazer Login")
            login_username = st.text_input("Usuário", key="login_user")
            login_password = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Entrar", use_container_width=True):
                ok, user_id = login_user(login_username, login_password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = login_username
                    st.success(f"Bem-vindo(a), {login_username}!")
                    st.query_params.update({"logged": "true"})
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

        with tab2:
            st.subheader("Registrar Novo Usuário")
            reg_username = st.text_input("Novo Usuário", key="reg_user")
            reg_password = st.text_input("Nova Senha", type="password", key="reg_pass")
            if st.button("Registrar", use_container_width=True):
                if reg_username and reg_password:
                    success, msg = register_user(reg_username, reg_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(f"Erro ao registrar: {msg}")
                else:
                    st.warning("Preencha usuário e senha.")

    # ================ SE ESTIVER LOGADO ================
    else:
        # Linha de saudação e botão de sair
        top1, top2 = st.columns([6, 1])
        with top1:
            st.write(f"Olá, **{st.session_state.username}**!")
        with top2:
            if st.button("Sair", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.edit_event_id = None
                st.query_params.clear()
                st.rerun()

        st.title("MVP - Cadastro de Eventos e Feiras")

        # 1) FORMULÁRIO PARA CADASTRAR NOVO EVENTO
        st.header("Cadastrar Novo Evento")
        lista_cidades = carregar_cidades()

        with st.form("form_evento", clear_on_submit=True):
            nome_evento = st.text_input("Nome do Evento")
            local = st.text_input("Local (endereço, p.ex.)")

            cidade_selecionada = st.selectbox(
                "Cidade (digite para filtrar)",
                ["Selecione..."] + lista_cidades,
                index=0
            )
            data_inicio = st.date_input("Data de Início", value=None)
            data_fim = st.date_input("Data de Fim", value=None)
            qtd_pessoas = st.number_input("Quantidade Esperada de Pessoas", min_value=1, value=1)
            categoria = st.selectbox("Categoria", ["Selecione...", "Show", "Congresso", "Feira", "Workshop", "Outro"])
            segmento = st.text_input("Segmento do Evento (ex: Tecnologia, Saúde, etc.)")
            descricao = st.text_area("Descrição do Evento")

            submit_cadastro = st.form_submit_button("Cadastrar Evento", use_container_width=True)
            if submit_cadastro:
                if (not nome_evento.strip() or
                    not local.strip() or
                    cidade_selecionada == "Selecione..." or
                    categoria == "Selecione..." or
                    not segmento.strip() or
                    not descricao.strip()):
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    cid_nome, uf = "", ""
                    if "(" in cidade_selecionada and ")" in cidade_selecionada:
                        partes = cidade_selecionada.rsplit(" (", 1)
                        cid_nome = partes[0].strip()
                        uf = partes[1].replace(")", "").strip()
                    else:
                        cid_nome = cidade_selecionada.strip()

                    try:
                        insert_event(
                            user_id=st.session_state.user_id,
                            nome_evento=nome_evento.strip(),
                            local=local.strip(),
                            cidade=cid_nome,
                            estado=uf,
                            data_inicio=data_inicio,
                            data_fim=data_fim,
                            qtd_pessoas=int(qtd_pessoas),
                            descricao=descricao.strip(),
                            categoria=categoria.strip(),
                            segmento=segmento.strip()
                        )
                        st.success("Evento cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar evento: {e}")

        # Continua na próxima parte...
        # 2) LISTAGEM E EDIÇÃO
        st.header("Meus Eventos Cadastrados")

        # Carrega df de eventos do usuário
        events_df = fetch_events(st.session_state.user_id)
        if events_df.empty:
            st.info("Nenhum evento cadastrado ainda.")
            return

        # Se existe um evento em edição
        if st.session_state.edit_event_id is not None:
            edit_id = st.session_state.edit_event_id
            row_to_edit = events_df[events_df["id"] == edit_id]
            if row_to_edit.empty:
                st.error("Evento não encontrado.")
                st.session_state.edit_event_id = None
                st.rerun()
            else:
                row_to_edit = row_to_edit.iloc[0]

                st.subheader(f"Editar Evento #{edit_id}")
                with st.form("form_edicao_evento"):
                    edit_nome_evento = st.text_input("Nome do Evento", value=row_to_edit["nome_evento"] or "")
                    edit_local = st.text_input("Local", value=row_to_edit["local"] or "")

                    original_cidade = row_to_edit["cidade"]
                    original_uf = row_to_edit["estado"]
                    combo_cidade_uf = ""
                    if original_cidade and original_uf:
                        combo_cidade_uf = f"{original_cidade} ({original_uf})"
                    else:
                        combo_cidade_uf = original_cidade or ""

                    cidades_opcoes = ["Selecione..."] + lista_cidades
                    if combo_cidade_uf and combo_cidade_uf not in cidades_opcoes:
                        cidades_opcoes.append(combo_cidade_uf)
                    cidades_opcoes = sorted(set(cidades_opcoes) - {"Selecione..."})
                    cidades_opcoes = ["Selecione..."] + cidades_opcoes

                    try:
                        idx_cidade = cidades_opcoes.index(combo_cidade_uf)
                    except ValueError:
                        idx_cidade = 0

                    edit_cidade_uf = st.selectbox(
                        "Cidade (digite para filtrar)",
                        cidades_opcoes,
                        index=idx_cidade
                    )

                    def str_to_date(d):
                        if isinstance(d, datetime.date):
                            return d
                        if not d:
                            return None
                        return datetime.datetime.strptime(d, "%Y-%m-%d").date()

                    edit_data_inicio = st.date_input(
                        "Data de Início",
                        value=str_to_date(row_to_edit["data_inicio"])
                    )
                    edit_data_fim = st.date_input(
                        "Data de Fim",
                        value=str_to_date(row_to_edit["data_fim"])
                    )

                    edit_qtd_pessoas = st.number_input(
                        "Quantidade Esperada de Pessoas",
                        min_value=1,
                        value=int(row_to_edit["qtd_pessoas"] or 1)
                    )

                    cat_options = ["Selecione...", "Show", "Congresso", "Feira", "Workshop", "Outro"]
                    try:
                        idx_cat = cat_options.index(row_to_edit["categoria"])
                    except ValueError:
                        idx_cat = 0
                    edit_categoria = st.selectbox("Categoria", cat_options, index=idx_cat)

                    edit_segmento = st.text_input("Segmento", value=row_to_edit["segmento"] or "")
                    edit_descricao = st.text_area("Descrição do Evento", value=row_to_edit["descricao"] or "")

                    salvar_alt = st.form_submit_button("Salvar Alterações", use_container_width=True)
                    if salvar_alt:
                        if (not edit_nome_evento.strip() or
                            not edit_local.strip() or
                            edit_cidade_uf == "Selecione..." or
                            edit_categoria == "Selecione..." or
                            not edit_segmento.strip() or
                            not edit_descricao.strip()):
                            st.error("Preencha todos os campos obrigatórios.")
                        else:
                            new_cidade, new_uf = "", ""
                            if "(" in edit_cidade_uf and ")" in edit_cidade_uf:
                                parts = edit_cidade_uf.rsplit(" (", 1)
                                new_cidade = parts[0].strip()
                                new_uf = parts[1].replace(")", "").strip()
                            else:
                                new_cidade = edit_cidade_uf.strip()

                            try:
                                update_event(
                                    event_id=edit_id,
                                    nome_evento=edit_nome_evento.strip(),
                                    local=edit_local.strip(),
                                    cidade=new_cidade,
                                    estado=new_uf,
                                    data_inicio=edit_data_inicio,
                                    data_fim=edit_data_fim,
                                    qtd_pessoas=edit_qtd_pessoas,
                                    descricao=edit_descricao.strip(),
                                    categoria=edit_categoria.strip(),
                                    segmento=edit_segmento.strip()
                                )
                                st.success("Evento atualizado com sucesso!")
                                st.session_state.edit_event_id = None
                                st.query_params.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar evento: {e}")

                if st.button("Cancelar Edição", use_container_width=True):
                    st.session_state.edit_event_id = None
                    st.query_params.clear()
                    st.rerun()

        else:
            # Nenhum evento em edição -> Exibir a lista
            st.subheader("Lista de Eventos")

            if "id" in events_df.columns:
                events_df.rename(columns={"id": "N° Evento"}, inplace=True)
            if "user_id" in events_df.columns:
                events_df.drop("user_id", axis=1, inplace=True)

            cols_header = st.columns([1.3, 2.5, 2, 2, 1.2, 1.6, 1.6, 1.2, 2, 2, 3, 1])
            labels = [
                "N° Evento", "Nome", "Local", "Cidade", "UF",
                "Início", "Fim", "Qtd", "Categoria", "Segmento",
                "Descrição", "Editar"
            ]
            for c, lbl in zip(cols_header, labels):
                c.markdown(f"**{lbl}**")

            for index, row in events_df.iterrows():
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12 = st.columns(
                    [1.3, 2.5, 2, 2, 1.2, 1.6, 1.6, 1.2, 2, 2, 3, 1]
                )
                c1.write(row["N° Evento"])
                c2.write(row["nome_evento"])
                c3.write(row["local"])
                c4.write(row["cidade"])
                c5.write(row["estado"])
                c6.write(row["data_inicio"] if row["data_inicio"] else "")
                c7.write(row["data_fim"] if row["data_fim"] else "")
                c8.write(row["qtd_pessoas"] if row["qtd_pessoas"] else "")
                c9.write(row["categoria"])
                c10.write(row["segmento"])
                c11.write(row["descricao"])

                if c12.button("✏️", key=f"edit_{row['N° Evento']}", use_container_width=True):
                    st.session_state.edit_event_id = row["N° Evento"]
                    st.query_params.update({"edit": str(row["N° Evento"])})
                    st.rerun()


if __name__ == "__main__":
    main()
