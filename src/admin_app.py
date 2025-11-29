import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import database as db

st.set_page_config(page_title="Admin YOUVISA", layout="wide")

st.title("Painel Administrativo YOUVISA")

tab1, tab2, tab3 = st.tabs(["Usuários", "Solicitações", "Configuração"])

with tab1:
    st.header("Usuários Cadastrados")
    conn = db.get_connection()
    users = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    st.dataframe(users)

with tab2:
    st.header("Solicitações de Visto (Tasks)")
    
    # Fetch tasks with details
    tasks_df = db.get_all_tasks_details()
    
    if not tasks_df.empty:
        for index, row in tasks_df.iterrows():
            with st.expander(f"{row['user_name']} - {row['country']} ({row['status']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**CPF:** {row['user_cpf']}")
                    st.write(f"**Criado em:** {row['created_at']}")
                    st.write(f"**Documentos Necessários:** {row['required_docs']}")
                
                with col2:
                    # Show uploaded documents
                    docs = db.get_task_documents(row['task_id'])
                    if docs:
                        st.write("**Documentos Enviados:**")
                        for doc in docs:
                            st.write(f"- {doc['doc_type']}")
                            if os.path.exists(doc['file_path']):
                                with open(doc['file_path'], "rb") as f:
                                    btn = st.download_button(
                                        label=f"Baixar {doc['doc_type']}",
                                        data=f,
                                        file_name=os.path.basename(doc['file_path']),
                                        mime="application/octet-stream",
                                        key=f"dl_{doc['id']}"
                                    )
                    else:
                        st.warning("Nenhum documento enviado ainda.")
    else:
        st.info("Nenhuma solicitação ativa encontrada.")

with tab3:
    st.header("Configuração")
    
    st.subheader("Adicionar Novo País")
    with st.form("add_country_form"):
        country_name = st.text_input("Nome do País")
        required_docs = st.text_area("Documentos Necessários (separados por vírgula)", help="Ex: Passaporte, Foto, Extrato Bancário")
        submitted = st.form_submit_button("Adicionar País")
        
        if submitted:
            if country_name and required_docs:
                if db.add_country(country_name, required_docs):
                    st.success(f"{country_name} adicionado com sucesso!")
                else:
                    st.error(f"O país {country_name} já existe.")
            else:
                st.error("Por favor, preencha todos os campos.")
    
    st.subheader("Países Existentes")
    countries = db.get_countries()
    if countries:
        for c in countries:
            st.text(f"{c['name']}: {c['required_docs']}")
