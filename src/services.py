import os
import base64
from dotenv import load_dotenv
from openai import OpenAI
import shutil

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client lazily
# Assumes OPENAI_API_KEY is set in environment variables
client = None

def get_client():
    """Get or initialize the OpenAI client."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it before using OpenAI services."
            )
        client = OpenAI(api_key=api_key)
    return client

STORAGE_DIR = "storage"

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def save_file(file_bytes, file_name, user_id):
    """Saves a file to the local storage directory organized by user_id."""
    user_dir = os.path.join(STORAGE_DIR, str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    file_path = os.path.join(user_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    
    return file_path

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def classify_document(file_path, required_docs):
    """
    Uses OpenAI Vision to classify the document against the list of required documents.
    Returns the matching document type or None if not found.
    """
    base64_image = encode_image(file_path)
    
    prompt = f"""
    Você é um classificador de documentos para um sistema de vistos.
    Os documentos necessários são: {required_docs}.
    
    Analise a imagem fornecida. Ela se parece com um dos documentos necessários?
    
    Se sim, retorne APENAS o nome exato do tipo de documento da lista.
    Se não, ou se não estiver claro, retorne "UNKNOWN".
    """

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        result = response.choices[0].message.content.strip()
        
        # Simple validation to ensure the result is one of the required docs
        required_list = [d.strip() for d in required_docs.split(',')]
        if result in required_list:
            return result
        else:
            return "UNKNOWN"
            
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return "ERROR"

def chat_with_bot(user_message, user_context=None):
    """
    Chat interface focado em auxiliar o usuário a fornecer informações necessárias.
    Não fornece informações genéricas sobre processos de visto.
    """
    try:
        # Construir o prompt do sistema baseado no contexto
        if user_context and user_context.get('active_task'):
            task = user_context['active_task']
            country_name = task.get('country_name', 'o país selecionado')
            required_docs = task.get('required_docs', '')
            uploaded_docs = user_context.get('uploaded_docs', [])
            uploaded_types = [d.get('doc_type', '') for d in uploaded_docs]
            required_list = [d.strip() for d in required_docs.split(',')]
            missing_docs = [doc for doc in required_list if doc not in uploaded_types]
            
            system_prompt = f"""Você é um assistente da YOUVISA, uma plataforma de solicitação de vistos.

IMPORTANTE: Sua função é APENAS auxiliar o usuário a fornecer as informações necessárias para preencher o processo de solicitação de visto. NÃO forneça informações genéricas sobre processos de visto, formulários, taxas ou procedimentos externos.

Contexto atual:
- O usuário está solicitando visto para: {country_name}
- Documentos necessários: {required_docs}
- Documentos já enviados: {', '.join(uploaded_types) if uploaded_types else 'Nenhum'}
- Documentos ainda faltando: {', '.join(missing_docs) if missing_docs else 'Nenhum'}

Sua função:
1. Orientar o usuário a enviar os documentos que ainda faltam
2. Responder dúvidas sobre como enviar documentos (foto ou PDF)
3. Confirmar o status do processo
4. NÃO dar informações sobre formulários DS-160, taxas, agendamentos ou outros procedimentos externos
5. Se o usuário perguntar sobre processos genéricos de visto, redirecione-o a focar em enviar os documentos necessários

Seja educado, conciso e sempre em Português."""
        else:
            system_prompt = """Você é um assistente da YOUVISA, uma plataforma de solicitação de vistos.

IMPORTANTE: Sua função é APENAS auxiliar o usuário a iniciar o processo de solicitação de visto na plataforma. NÃO forneça informações genéricas sobre processos de visto, formulários, taxas ou procedimentos externos.

Sua função:
1. Orientar o usuário a começar o processo digitando /start
2. Explicar que você ajudará a coletar os documentos necessários
3. NÃO dar informações sobre formulários, taxas, agendamentos ou outros procedimentos externos
4. Se o usuário perguntar sobre processos genéricos de visto, redirecione-o a iniciar o processo na plataforma com /start

Seja educado, conciso e sempre em Português."""
        
        response = get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300  # Limitar resposta para ser mais concisa
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Desculpe, estou tendo problemas técnicos no momento. Por favor, tente novamente ou use /start para reiniciar."
