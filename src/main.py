#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
ORQUESTRADOR DO PIPELINE - OLHO DE FERRO
=============================================================================
Este script executa o pipeline completo de ponta a ponta:
1. Extração de dados de pesquisadores da FAPESP.
2. Classificação de viabilidade dos pesquisadores extraídos.
3. Busca de emails para os pesquisadores classificados como viáveis.

Para executar, rode: python src/main.py
"""

import sys
import os
import asyncio

# Adiciona a pasta raiz do projeto ao path do Python para resolver o ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa as classes e configurações de cada etapa
from src.config import (
    INPUT_DIR, 
    STEP1_EXTRACTED_JSONS_DIR, 
    STEP2_CLASSIFIED_REPORTS_DIR,
    STEP3_FINAL_CONTACTS_DIR,
    MODELOS_GEMINI
)
from src.step1_extraction import ExtratorFAPESP
from src.step2_classification import ClientClassifierRAGGemini
from src.step3_email_search import BuscadorEmailFAPESP

def run_step1():
    """Executa a Etapa 1: Extração de Dados."""
    print("="*70)
    print("🚀 INICIANDO ETAPA 1: EXTRAÇÃO DE DADOS DA FAPESP")
    print("="*70)
    try:
        extrator = ExtratorFAPESP(input_dir=INPUT_DIR, output_dir=STEP1_EXTRACTED_JSONS_DIR)
        sucesso = extrator.executar()
        if not sucesso:
            print("\n💥 ETAPA 1 FINALIZADA COM PROBLEMAS. O pipeline será interrompido.")
            return False
        print("\n🎉 ETAPA 1 CONCLUÍDA COM SUCESSO!")
        return True
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NA ETAPA 1: {e}")
        return False

def run_step2():
    """Executa a Etapa 2: Classificação de Viabilidade."""
    print("\n" + "="*70)
    print("🚀 INICIANDO ETAPA 2: CLASSIFICAÇÃO DE VIABILIDADE")
    print("="*70)
    try:
        # Usando configurações padrão recomendadas
        classifier = ClientClassifierRAGGemini(model_name="gemini-2.5-flash", batch_size=4)
        classifier.processar_pasta(
            pasta_entrada=STEP1_EXTRACTED_JSONS_DIR, 
            pasta_saida=STEP2_CLASSIFIED_REPORTS_DIR
        )
        print("\n🎉 ETAPA 2 CONCLUÍDA COM SUCESSO!")
        return True
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NA ETAPA 2: {e}")
        return False

async def run_step3():
    """Executa a Etapa 3: Busca de Emails."""
    print("\n" + "="*70)
    print("🚀 INICIANDO ETAPA 3: BUSCA DE EMAILS")
    print("="*70)
    try:
        # Usando configurações padrão recomendadas
        modelo_config = MODELOS_GEMINI['browser']['2']
        buscador = BuscadorEmailFAPESP(modelo_config, headless=True, use_vision=True)
        await buscador.executar_busca_completa()
        print("\n🎉 ETAPA 3 CONCLUÍDA COM SUCESSO!")
        return True
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NA ETAPA 3: {e}")
        return False

async def main_pipeline():
    """Função principal que orquestra o pipeline completo."""
    if not run_step1():
        return
    if not run_step2():
        return
    await run_step3()
    print("\n" + "="*70)
    print("✅ PIPELINE 'OLHO DE FERRO' FINALIZADO COM SUCESSO!")
    print("="*70)

if __name__ == "__main__":
    # Bloco principal que oferece um menu interativo para usuários de IDE.
    def display_menu():
        print("\n" + "="*50)
        print("      MENU DE EXECUÇÃO - OLHO DE FERRO")
        print("="*50)
        print("  1. Executar Etapa 1 (Extração de Dados)")
        print("  2. Executar Etapa 2 (Classificação de Viabilidade)")
        print("  3. Executar Etapa 3 (Busca de Emails)")
        print("  4. Executar Pipeline Completo (Todas as Etapas)")
        print("  0. Sair")
        print("="*50)

    while True:
        display_menu()
        choice = input("  Escolha uma opção (0-4): ").strip()

        try:
            if choice == '1':
                run_step1()
            elif choice == '2':
                run_step2()
            elif choice == '3':
                print("\nIniciando Etapa 3 (assíncrona)...")
                asyncio.run(run_step3())
            elif choice == '4':
                print("\nIniciando Pipeline Completo (assíncrono)...")
                asyncio.run(main_pipeline())
            elif choice == '0':
                print("\nEncerrando o programa.")
                break
            else:
                print("\n❌ Opção inválida. Por favor, tente novamente.")
        
        except KeyboardInterrupt:
            print("\n⏹️ Operação interrompida pelo usuário.")
            break
