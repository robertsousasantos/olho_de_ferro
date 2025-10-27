# src/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

# Carrega variáveis do arquivo .env para o ambiente
load_dotenv()

# --- CONFIGURAÇÕES GERAIS ---

# Chave de API carregada de forma segura do arquivo .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- ESTRUTURA DE DIRETÓRIOS ---

# Define o caminho base do projeto (a pasta "Olho_de_ferro")
BASE_DIR = Path(__file__).resolve().parent.parent

# Define as pastas principais
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SRC_DIR = BASE_DIR / "src"

# Define as subpastas de dados
INPUT_DIR = DATA_DIR / "input"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# Define os caminhos específicos para cada etapa do pipeline
STEP1_EXTRACTED_JSONS_DIR = PROCESSED_DIR / "step1_extracted_jsons"
STEP2_CLASSIFIED_REPORTS_DIR = PROCESSED_DIR / "step2_classified_reports"
STEP3_FINAL_CONTACTS_DIR = OUTPUT_DIR / "final_contacts"
EMAIL_SEARCH_LOGS_DIR = LOGS_DIR / "email_search_logs"

# Garante que todas as pastas de saída e logs existam ao iniciar
STEP1_EXTRACTED_JSONS_DIR.mkdir(parents=True, exist_ok=True)
STEP2_CLASSIFIED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
STEP3_FINAL_CONTACTS_DIR.mkdir(parents=True, exist_ok=True)
EMAIL_SEARCH_LOGS_DIR.mkdir(parents=True, exist_ok=True)


# --- CONFIGURAÇÃO DOS MODELOS GEMINI ---

# Dicionário centralizado de modelos para evitar duplicação
MODELOS_GEMINI = {
    # Modelos para Extração e Busca de Email (Steps 1 e 3)
    'extraction': {
        '1': {'name': 'gemini-1.5-flash', 'display': 'Gemini 1.5 Flash (Recomendado)', 'temperature': 0.1},
        '2': {'name': 'gemini-1.5-pro', 'display': 'Gemini 1.5 Pro (Mais inteligente)', 'temperature': 0.1},
    },
    # Modelos para Classificação (Step 2)
    'classification': {
        "1": ("gemini-2.5-pro", "🔥 Gemini 2.5 Pro - Máxima inteligência com thinking"),
        "2": ("gemini-2.5-flash", "⚡ Gemini 2.5 Flash - Melhor custo-benefício com thinking (RECOMENDADO)"),
        "3": ("gemini-1.5-flash", "⚡ Gemini 1.5 Flash - Rápido e versátil")
    },
    # Modelos para Busca com browser-use (Step 3)
    'browser': {
        "1": {"name": "gemini-2.5-pro", "display": "🚀 Gemini 2.5 Pro", "temperature": 0.1, "max_steps": 40},
        "2": {"name": "gemini-2.5-flash", "display": "⚡ Gemini 2.5 Flash (Recomendado)", "temperature": 0.1, "max_steps": 35},
    }
}

# --- CONFIGURAÇÕES DO PIPELINE ---
DELAY_ENTRE_BUSCAS = 5  # segundos
