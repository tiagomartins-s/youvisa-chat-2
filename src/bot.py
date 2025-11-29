import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import database as db

try:
    from . import services  # Prefer package-relative import
except (ImportError, ValueError):
    import services  # Fallback for running as a script

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
NAME, CPF, SELECT_COUNTRY, UPLOAD_DOCS = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the user's name."""
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    
    # Check if user already exists
    existing_user = db.get_user(user.id)
    if existing_user:
        await update.message.reply_text(
            f"Bem-vindo de volta, {existing_user['name']}! O que você gostaria de fazer?",
            reply_markup=ReplyKeyboardMarkup([["Solicitar Visto", "Meu Status"]], one_time_keyboard=True),
        )
        return SELECT_COUNTRY # Simplified flow for returning users
    
    await update.message.reply_text(
        "Bem-vindo à YOUVISA! Sou seu assistente inteligente.\n"
        "Para começar, por favor me diga seu nome completo."
    )
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the name and asks for CPF."""
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Prazer em te conhecer! Agora, por favor digite seu CPF (apenas números).")
    return CPF

async def cpf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the CPF and registers the user."""
    context.user_data["cpf"] = update.message.text
    user = update.message.from_user
    
    # Register user in DB
    db.add_user(user.id, context.user_data["name"], context.user_data["cpf"])
    
    await update.message.reply_text(
        "Cadastro concluído! Agora, vamos iniciar sua solicitação de visto."
    )
    return await list_countries(update, context)

async def list_countries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    countries = db.get_countries()
    if not countries:
        await update.message.reply_text("Desculpe, não temos países configurados ainda. Por favor contate o administrador.")
        return ConversationHandler.END
    
    context.user_data['countries_cache'] = countries
    buttons = [[c['name']] for c in countries]
    country_list_text = "\n".join([f"- {c['name']}" for c in countries])
    await update.message.reply_text(
        "Por favor selecione o país para o qual deseja o visto:\n\n"
        "Países disponíveis:\n"
        f"{country_list_text}",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True),
    )
    return SELECT_COUNTRY

async def select_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    
    # Handle "My Status" or other commands if mixed
    if text == "meu status":
        # Implement status check
        return ConversationHandler.END

    countries = context.user_data.get('countries_cache') or db.get_countries()
    if countries:
        context.user_data['countries_cache'] = countries
    
    country = None
    if countries:
        for c in countries:
            name_lower = c['name'].lower()
            if text == name_lower:
                country = c
                break
            if name_lower in text or text in name_lower:
                country = c
                break
    if not country:
        # Fallback to DB exact lookup
        country = db.get_country_by_name(update.message.text.strip())
    
    if not country:
        countries = context.user_data.get('countries_cache') or db.get_countries()
        if countries:
            country_list_text = "\n".join([f"- {c['name']}" for c in countries])
            await update.message.reply_text(
                "Ainda não trabalhamos com esse país. Por favor escolha um da lista abaixo:\n\n"
                f"{country_list_text}"
            )
        else:
            await update.message.reply_text("Ainda não temos países configurados. Por favor contacte o administrador.")
        return await list_countries(update, context)
    
    user = update.message.from_user
    db_user = db.get_user(user.id)
    
    # Create Task
    task_id = db.create_task(db_user['id'], country['id'])
    context.user_data['task_id'] = task_id
    context.user_data['required_docs'] = country['required_docs']
    
    await update.message.reply_text(
        f"Ótimo! Você está solicitando para {country['name']}.\n"
        f"Você precisa enviar os seguintes documentos: {country['required_docs']}.\n"
        "Por favor envie uma foto ou PDF de um dos documentos."
    )
    return UPLOAD_DOCS

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    task_id = context.user_data.get('task_id')
    
    if not task_id:
        # Try to recover active task
        db_user = db.get_user(user.id)
        task = db.get_user_active_task(db_user['id'])
        if task:
            task_id = task['id']
            context.user_data['task_id'] = task_id
            context.user_data['required_docs'] = task['required_docs']
        else:
            await update.message.reply_text("Você não tem uma solicitação ativa. Digite /start para começar.")
            return ConversationHandler.END

    file = await update.message.effective_attachment[-1].get_file() if update.message.photo else await update.message.document.get_file()
    
    file_name = f"{task_id}_{file.file_unique_id}.jpg" # Simplified extension handling
    file_bytes = await file.download_as_bytearray()
    
    # Save locally
    saved_path = services.save_file(file_bytes, file_name, user.id)
    
    await update.message.reply_text("Analisando seu documento... Por favor aguarde.")
    
    # Classify
    doc_type = services.classify_document(saved_path, context.user_data['required_docs'])
    
    if doc_type == "UNKNOWN" or doc_type == "ERROR":
        await update.message.reply_text(
            "Não consegui identificar este documento como um dos necessários. "
            f"Por favor certifique-se que é um de: {context.user_data['required_docs']} e tente novamente."
        )
        # Optionally delete the file if rejected
    else:
        db.add_document(task_id, doc_type, saved_path)
        await update.message.reply_text(f"Recebido: {doc_type}!")
        
        # Check if all docs are received
        uploaded_docs = db.get_task_documents(task_id)
        uploaded_types = set([d['doc_type'] for d in uploaded_docs])
        required_list = set([d.strip() for d in context.user_data['required_docs'].split(',')])
        
        missing = required_list - uploaded_types
        
        if not missing:
            db.update_task_status(task_id, "READY")
            await update.message.reply_text(
                "Parabéns! Recebemos todos os seus documentos. "
                "Sua solicitação está pronta para análise."
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(f"Ainda falta: {', '.join(missing)}")

    return UPLOAD_DOCS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general chat messages, focusing on helping user provide required information."""
    user = update.message.from_user
    db_user = db.get_user(user.id)
    
    # Build user context
    user_context = None
    if db_user:
        task = db.get_user_active_task(db_user['id'])
        if task:
            uploaded_docs = db.get_task_documents(task['id'])
            user_context = {
                'active_task': {
                    'country_name': task.get('country_name'),
                    'required_docs': task.get('required_docs')
                },
                'uploaded_docs': uploaded_docs
            }
    
    response = services.chat_with_bot(update.message.text, user_context)
    await update.message.reply_text(response)

def main() -> None:
    """Run the bot."""
    # Get token from env
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        return

    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            CPF: [MessageHandler(filters.TEXT & ~filters.COMMAND, cpf)],
            SELECT_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_country)],
            UPLOAD_DOCS: [
                MessageHandler(filters.PHOTO | filters.Document.PDF | filters.Document.IMAGE, handle_document)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
