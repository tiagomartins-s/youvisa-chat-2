# Plataforma Inteligente de Atendimento Multicanal - YOUVISA (Sprint 2)

Entrega da Sprint 2 do Challenge YOUVISA, evoluindo o planejamento inicial para um protótipo funcional que conecta chatbot Telegram, automação de documentos, classificação assistida por IA generativa/visão computacional e um painel administrativo em Streamlit. O foco é validar o pipeline ponta a ponta: recepção de arquivos, triagem inteligente, organização das tarefas e visibilidade operacional para atendentes humanos.

---

## 🧠 1. Descrição do Projeto

O ecossistema YOUVISA permite que usuários iniciem o atendimento via chatbot, enviem documentos obrigatórios e acompanhem o progresso do pedido. A cada upload, o pipeline executa:

- Identificação do solicitante e criação automática de tarefas por país;
- Classificação do documento com modelos GPT-4o (visão + NLP);
- Persistência dos metadados no SQLite, armazenando os arquivos em disco;
- Atualização do painel administrativo para revisão humana, liberações e downloads.

Além do fluxo já implementado, esta sprint detalha como as próximas automações (validação reforçada, disparo de e-mails e integrações RPA) se plugam ao pipeline.

---

## 🧱 2. Tecnologias Utilizadas

| Camada | Tecnologias | Finalidade |
| --- | --- | --- |
| Chatbot multicanal | `python-telegram-bot`, `asyncio` | Coletar dados do usuário, guiar uploads e manter contexto das tarefas |
| Orquestração e serviços | `services.py`, `asyncio` | Encapsular chamadas de IA, salvar arquivos e responder ao chatbot |
| IA Generativa e Visão | `OpenAI GPT-4o` | Classificar imagens/documentos e responder às interações com contexto |
| Persistência | `SQLite`, `pandas` | Armazenar usuários, países, tarefas e documentos com consultas simples |
| Painel humano | `Streamlit`, `pandas` | Exibir usuários, filas de solicitações, documentos enviados e cadastros de países |
| Infraestrutura | `.env`, `python-dotenv`, `venv` | Gestão de segredos e isolamento do ambiente |

---

## 🚀 3. Pipeline da Solução

1. **Entrada multicanal** – O usuário inicia o fluxo pelo Telegram (`/start`), informa nome e CPF e escolhe o país alvo. Outros canais (WhatsApp/Web) podem ser adicionados reutilizando o backend.
2. **Cadastro e requisitos** – O bot consulta `countries` no SQLite, exibe requisitos e cria uma tarefa (`tasks`) vinculada ao usuário.
3. **Upload e armazenamento** – Cada documento enviado é salvo em `storage/<telegram_id>` e vinculado ao task_id.
4. **Classificação com IA** – `services.classify_document` envia a imagem ao GPT-4o Vision para identificar o tipo e valida se coincide com os requisitos.
5. **Atualização de status** – Ao completar todos os documentos, o status muda para `READY`, abrindo espaço para automações (e-mail de confirmação, abertura de ticket, etc.).
6. **Painel administrativo** – `src/admin_app.py` lista usuários, solicitações e países, permitindo download dos arquivos e cadastro de novos destinos.
7. **Próximas automações** – Workers assíncronos podem observar mudanças de status para disparar RPA (envio de e-mail, integração consular, análise avançada com OpenCV).

---

## 🔁 4. Fluxograma do Pipeline

```
    U[Usuário (Telegram/Web)] -->|/start| B[Chatbot Telegram]
    B -->|nome/CPF| DB[(SQLite)]
    B -->|seleção país| CT[Catálogo de Países]
    B -->|upload documento| ST[Storage Local]
    ST --> IA[Serviço de IA GPT-4o]
    IA -->|tipo validado| DB
    DB --> PA[Painel Streamlit]
    DB -->|status READY| RP[Automações & RPA]
    RP -->|confirmação / e-mail| U
    RP -->|abertura de tarefa humana| PA
```

---

## 🛠️ 5. Instruções de Execução

1. **Pré-requisitos**
   - Python 3.11+
   - Conta Telegram para criar o bot e token via BotFather
   - Chave da API OpenAI com acesso ao modelo GPT-4o

2. **Configuração do ambiente**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate          # Windows PowerShell
   pip install -r requirements.txt
   ```

3. **Variáveis de ambiente (.env)**
   ```
   TELEGRAM_TOKEN=seu_token
   OPENAI_API_KEY=sua_chave
   ```

4. **Inicialização do banco**
   ```bash
   python -c "import database; database.init_db()"
   ```

5. **Execução do chatbot**
   ```bash
   python src/bot.py
   ```

6. **Execução do painel administrativo**
   ```bash
   streamlit run src/admin_app.py
   ```

7. **Testes de fluxo**
   - Use o Telegram para conversar com o bot, enviar documentos (foto/PDF) e validar o status.
   - Abra o painel para ver solicitações, baixar arquivos e cadastrar novos países.
---

## 🗂️ 6. Estrutura de Arquivos do Projeto

```text
youvisa/
├── README.md
├── requirements.txt
├── database/
│   ├── __init__.py         # Conexão SQLite, schema e operações CRUD
│   └── youvisa.db          # Banco local (SQLite) com usuários, países, tasks, documentos
├── src/
│   ├── __init__.py
│   ├── admin_app.py        # Painel Streamlit para visualização e gestão das solicitações
│   ├── bot.py              # Chatbot Telegram com estados, upload e validação de documentos
│   └── services.py         # Serviços auxiliares (OpenAI, storage local, chat contextual)
├── storage/
│   └── <telegram_id>/      # Diretórios por usuário contendo os arquivos enviados
└── database/__pycache__/   # Artefatos gerados automaticamente (podem ser ignorados)
```

---

Entrega pronta para revisão da Sprint 2, mostrando o pipeline funcional de coleta, classificação e administração de documentos com IA aplicada ao atendimento consular.

