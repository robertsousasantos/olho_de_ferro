#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Robusto para Conversão CSV → Excel - Projeto FAPES
Auto-detecção de arquivos
"""

import pandas as pd
import os
import glob
from datetime import datetime

def encontrar_arquivos(input_dir):
    """Encontra automaticamente os arquivos CSV necessários"""
    
    print(f"🔍 Procurando arquivos em: {input_dir}")
    
    if not os.path.exists(input_dir):
        print(f"❌ Diretório não existe: {input_dir}")
        return None, None
    
    # Padrões para buscar os arquivos
    padroes_viaveis = [
        "*clientes*viáveis*.csv",
        "*clientes*viaveis*.csv", 
        "*lista_clientes_viaveis*.csv",
        "*viaveis*.csv"
    ]
    
    padroes_negativos = [
        "*fatores*negativos*.csv",
        "*lista_N*fatores*.csv",
        "*N_fatores*.csv",
        "*negativos*.csv"
    ]
    
    arquivo_viaveis = None
    arquivo_negativos = None
    
    # Buscar arquivo de clientes viáveis
    print("\n📁 Procurando arquivo de clientes viáveis...")
    for padrao in padroes_viaveis:
        arquivos = glob.glob(os.path.join(input_dir, padrao))
        if arquivos:
            arquivo_viaveis = arquivos[0]  # Pega o primeiro encontrado
            print(f"   ✓ Encontrado: {os.path.basename(arquivo_viaveis)}")
            break
    
    if not arquivo_viaveis:
        print("   ❌ Arquivo de clientes viáveis não encontrado")
    
    # Buscar arquivo de fatores negativos  
    print("\n📁 Procurando arquivo de fatores negativos...")
    for padrao in padroes_negativos:
        arquivos = glob.glob(os.path.join(input_dir, padrao))
        if arquivos:
            arquivo_negativos = arquivos[0]  # Pega o primeiro encontrado
            print(f"   ✓ Encontrado: {os.path.basename(arquivo_negativos)}")
            break
    
    if not arquivo_negativos:
        print("   ❌ Arquivo de fatores negativos não encontrado")
    
    # Listar todos os CSVs disponíveis se não encontrou
    if not arquivo_viaveis or not arquivo_negativos:
        print(f"\n📋 Todos os arquivos CSV disponíveis em {input_dir}:")
        todos_csvs = glob.glob(os.path.join(input_dir, "*.csv"))
        if todos_csvs:
            for i, csv_file in enumerate(sorted(todos_csvs), 1):
                print(f"   {i:2d}. {os.path.basename(csv_file)}")
        else:
            print("   ❌ Nenhum arquivo CSV encontrado!")
    
    return arquivo_viaveis, arquivo_negativos

def carregar_e_processar(arquivo_viaveis, arquivo_negativos):
    """Carrega e processa os arquivos CSV"""
    
    try:
        # Carregar dados
        print(f"\n📊 Carregando dados...")
        df_viaveis = pd.read_csv(arquivo_viaveis, encoding='utf-8')
        print(f"   ✓ Clientes viáveis: {len(df_viaveis)} registros")
        
        df_negativos = pd.read_csv(arquivo_negativos, encoding='utf-8')
        print(f"   ✓ Fatores negativos: {len(df_negativos)} registros")
        
        # Adicionar identificação
        df_viaveis['origem_dataset'] = 'Clientes Viáveis'
        df_negativos['origem_dataset'] = 'Fatores Negativos'
        
        # Combinar
        df_completo = pd.concat([df_viaveis, df_negativos], ignore_index=True)
        print(f"   ✓ Total combinado: {len(df_completo)} registros")
        
        return df_completo, df_viaveis, df_negativos
        
    except Exception as e:
        print(f"❌ Erro ao processar arquivos: {e}")
        return None, None, None

def salvar_excel(df_completo, df_viaveis, df_negativos, output_dir):
    """Salva os dados em Excel"""
    
    # Criar diretório se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    # Nome do arquivo com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f"analise_fapes_{timestamp}.xlsx"
    caminho_saida = os.path.join(output_dir, nome_arquivo)
    
    try:
        print(f"\n💾 Salvando arquivo Excel...")
        
        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            # Aba principal
            df_completo.to_excel(writer, sheet_name='Análise Completa', index=False)
            
            # Abas separadas
            df_viaveis.to_excel(writer, sheet_name='Clientes Viáveis', index=False)
            df_negativos.to_excel(writer, sheet_name='Fatores Negativos', index=False)
            
            # Estatísticas básicas
            stats_data = {
                'Métrica': [
                    'Total de Registros',
                    'Clientes Viáveis', 
                    'Fatores Negativos',
                    'Data de Processamento'
                ],
                'Valor': [
                    len(df_completo),
                    len(df_viaveis),
                    len(df_negativos),
                    datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                ]
            }
            pd.DataFrame(stats_data).to_excel(writer, sheet_name='Estatísticas', index=False)
        
        print(f"   ✅ Sucesso! Arquivo salvo: {nome_arquivo}")
        print(f"   📁 Local: {caminho_saida}")
        return caminho_saida
        
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return None

def main():
    """Função principal"""
    print("=" * 80)
    print("CONVERSOR CSV → EXCEL - PROJETO FAPES")
    print("Auto-detecção de arquivos")
    print("=" * 80)
    
    # Caminhos
    input_dir = "/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_3_analise_viabailidade"
    output_dir = "/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_3_5"
    
    # Encontrar arquivos
    arquivo_viaveis, arquivo_negativos = encontrar_arquivos(input_dir)
    
    if not arquivo_viaveis or not arquivo_negativos:
        print(f"\n❌ Não foi possível encontrar ambos os arquivos necessários.")
        print(f"💡 Verifique se os arquivos CSV estão na pasta correta:")
        print(f"   {input_dir}")
        return
    
    # Processar dados
    df_completo, df_viaveis, df_negativos = carregar_e_processar(arquivo_viaveis, arquivo_negativos)
    
    if df_completo is None:
        print(f"❌ Falha no processamento dos dados.")
        return
    
    # Salvar Excel
    arquivo_final = salvar_excel(df_completo, df_viaveis, df_negativos, output_dir)
    
    if arquivo_final:
        print(f"\n🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
        print(f"📊 Resumo:")
        print(f"   • Total de registros: {len(df_completo)}")
        print(f"   • Clientes viáveis: {len(df_viaveis)}")
        print(f"   • Fatores negativos: {len(df_negativos)}")
        print(f"   • Arquivo gerado: {os.path.basename(arquivo_final)}")
    else:
        print(f"❌ Falha ao gerar arquivo final.")

if __name__ == "__main__":
    main()