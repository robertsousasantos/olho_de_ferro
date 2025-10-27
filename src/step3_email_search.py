#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# ETAPA 3: BUSCADOR DE EMAILS FAPESP
# =============================================================================
# Integração Browser-use + Google Gemini para busca automatizada de emails.
# Lê CSV de pesquisadores, encontra JSONs correspondentes e busca emails.

import asyncio
import os
import json
import time
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Adiciona o hack de caminho para execução standalone
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa as configurações centralizadas
from src.config import (
    GOOGLE_API_KEY,
    STEP1_EXTRACTED_JSONS_DIR, 
    STEP2_CLASSIFIED_REPORTS_DIR,
    STEP3_FINAL_CONTACTS_DIR,
    EMAIL_SEARCH_LOGS_DIR,
    MODELOS_GEMINI,
    DELAY_ENTRE_BUSCAS
)

# Configura a API Key do Gemini a partir do config.py
if not GOOGLE_API_KEY:
    print("❌ Chave GOOGLE_API_KEY não encontrada no arquivo .env")
    exit(1)

# IMPORTS E VERIFICAÇÃO DE DEPENDÊNCIAS
try:
    from browser_use import Agent
    from browser_use.llm.google import ChatGoogle
except ImportError as e:
    print(f"❌ Erro de importação: {e}. Execute 'pip install -r requirements.txt'")
    exit(1)

class BuscadorEmailFAPESP:
    """Classe principal para busca automatizada de emails de pesquisadores FAPESP"""
    
    def __init__(self, modelo_config: Dict, headless: bool = True, use_vision: bool = True):
        self.pasta_csv_input = STEP2_CLASSIFIED_REPORTS_DIR
        self.pasta_json_input = STEP1_EXTRACTED_JSONS_DIR
        self.pasta_output = STEP3_FINAL_CONTACTS_DIR
        self.pasta_logs = EMAIL_SEARCH_LOGS_DIR
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.modelo_config = modelo_config
        self.headless = headless
        self.use_vision = use_vision
        self.llm = None
        
        self.stats = {
            "total_processados": 0,
            "emails_encontrados": 0, 
            "emails_nao_encontrados": 0,
            "emails_ja_existiam": 0,
            "erros": 0
        }
        
        self._inicializar_gemini()

    def _inicializar_gemini(self):
        try:
            self.llm = ChatGoogle(
                model=self.modelo_config['name'],
                temperature=self.modelo_config['temperature'],
                api_key=GOOGLE_API_KEY
            )
            print(f"✅ Gemini inicializado: {self.modelo_config['display']}")
        except Exception as e:
            print(f"❌ Erro ao inicializar Gemini: {e}")
            raise

    def carregar_csv_pesquisadores(self) -> Optional[pd.DataFrame]:
        try:
            arquivos_csv = sorted(
                self.pasta_csv_input.glob("lista_clientes_viaveis_*.csv"), 
                key=os.path.getmtime,
                reverse=True
            )
            if not arquivos_csv:
                print(f"❌ Nenhum CSV 'lista_clientes_viaveis' encontrado em {self.pasta_csv_input}")
                return None
                
            csv_path = arquivos_csv[0]
            print(f"📊 Carregando lista de pesquisadores de: {csv_path.name}")
            
            df = pd.read_csv(csv_path, encoding='utf-8')
            print(f"📋 Pesquisadores a processar: {len(df)}")
            
            if 'nome' not in df.columns:
                print("❌ Coluna 'nome' não encontrada no CSV!")
                return None
                
            return df
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            return None

    def encontrar_json_pesquisador(self, nome_pesquisador: str) -> Optional[Path]:
        try:
            arquivos_json = list(self.pasta_json_input.glob("FAPESP_*.json"))
            nome_limpo = re.sub(r'[^\w\s-]', '', nome_pesquisador).lower()
            palavras_nome = [p for p in nome_limpo.split() if len(p) > 2]
            
            for arquivo in arquivos_json:
                try:
                    with open(arquivo, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'dados' in data and 'nome_completo' in data['dados']:
                        nome_json = data['dados']['nome_completo'].lower()
                        if all(palavra in nome_json for palavra in palavras_nome):
                            print(f"  📄 JSON encontrado: {arquivo.name}")
                            return arquivo
                except Exception:
                    continue
            print(f"  ❌ JSON não encontrado para: {nome_pesquisador}")
            return None
        except Exception as e:
            print(f"  ❌ Erro na busca do JSON: {e}")
            return None

    def criar_prompt_busca_email(self, nome: str, instituicao: str = "") -> str:
        return f'''
🎯 MISSÃO: Encontrar o EMAIL ESPECÍFICO do pesquisador

👤 PESQUISADOR: {nome}
🏢 INSTITUIÇÃO: {instituicao if instituicao else "Não informada"}

📍 ESTRATÉGIA DE BUSCA:
1. Busque no Google: "{nome}" email
2. Busque no Google: "{nome}" contato
3. Busque no Google: "{nome}" @ (símbolo arroba)
4. Verifique site da instituição se conhecida
5. Procure em perfis acadêmicos (Lattes, Google Scholar, ResearchGate)
6. Tente variações do nome

⚠️ REGRAS RÍGIDAS:
❌ REJEITAR emails genéricos: secretaria@, diretoria@, contato@, info@, admin@
❌ REJEITAR emails de departamentos: depto@, coordenacao@, pos-graduacao@
✅ ACEITAR apenas emails ESPECÍFICOS do pesquisador individual
✅ Formatos válidos: nome@universidade.br, nome.sobrenome@email.com

📋 FORMATO DE RESPOSTA OBRIGATÓRIO:
**RESULTADO DA BUSCA**
📧 EMAIL: [email específico encontrado OU "Não encontrado"]
✅ VALIDAÇÃO: [Sim - é específico do pesquisador / Não - não encontrado]
🔍 FONTE: [onde encontrou o email]

⚡ IMPORTANTE: Se não encontrar email específico do pesquisador, responda exatamente "Não encontrado"
'''

    async def buscar_email_pesquisador(self, nome: str, instituicao: str = "") -> str:
        print(f"  🔍 Buscando email: {nome}")
        try:
            prompt = self.criar_prompt_busca_email(nome, instituicao)
            agent = Agent(task=prompt, llm=self.llm, use_vision=self.use_vision, headless=self.headless)
            print(f"    🚀 Executando busca com Gemini...")
            resultado = await agent.run(max_steps=self.modelo_config['max_steps'])
            email = self._extrair_email_do_resultado(str(resultado), nome)
            self._salvar_log_busca(nome, email, str(resultado))
            return email
        except Exception as e:
            print(f"    ❌ ERRO na busca: {e}")
            return "Não encontrado"

    def _extrair_email_do_resultado(self, resultado: str, nome_pesquisador: str) -> str:
        try:
            emails_genericos = ['secretaria@', 'diretoria@', 'contato@', 'info@', 'admin@', 'atendimento@', 'administracao@', 'departamento@', 'depto@', 'webmaster@', 'suporte@', 'geral@', 'coordenacao@', 'pos-graduacao@', 'posgrad@', 'secretaria.@']
            linhas = resultado.split('\n')
            email_validado = False
            
            for linha in linhas:
                if 'VALIDAÇÃO:' in linha and 'Sim' in linha:
                    email_validado = True
                    break
            
            for linha in linhas:
                if '📧 EMAIL:' in linha:
                    email = linha.split('📧 EMAIL:')[1].strip()
                    if email and email != "Não encontrado" and '@' in email:
                        if not any(generico in email.lower() for generico in emails_genericos):
                            if email_validado:
                                print(f"    ✅ Email encontrado e validado: {email}")
                                return email
            
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_encontrados = re.findall(email_pattern, resultado)
            for email in emails_encontrados:
                if not any(generico in email.lower() for generico in emails_genericos):
                    print(f"    ✅ Email extraído por padrão regex: {email}")
                    return email
            
            print(f"    ⚠️ Nenhum email específico encontrado")
            return "Não encontrado"
        except Exception as e:
            print(f"    ❌ Erro ao processar resultado da busca: {e}")
            return "Não encontrado"

    async def processar_pesquisador(self, nome: str, json_path: Path) -> bool:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                dados_pesquisador = json.load(f)
            instituicao = dados_pesquisador.get('dados', {}).get('instituicao_vinculo', '')
            print(f"\n📋 Processando: {nome} | Instituição: {instituicao}")
            
            email_atual = dados_pesquisador.get('dados', {}).get('email_contato', 'Não encontrado')
            if email_atual != 'Não encontrado' and '@' in email_atual:
                print(f"  ✅ Email já existe: {email_atual}")
                self.stats["emails_ja_existiam"] += 1
                return self._salvar_json_com_email(dados_pesquisador, nome, email_atual)
            
            email_encontrado = await self.buscar_email_pesquisador(nome, instituicao)
            
            if email_encontrado != "Não encontrado":
                self.stats["emails_encontrados"] += 1
            else:
                self.stats["emails_nao_encontrados"] += 1
            return self._salvar_json_com_email(dados_pesquisador, nome, email_encontrado)
        except Exception as e:
            print(f"  ❌ Erro ao processar pesquisador {nome}: {e}")
            self.stats["erros"] += 1
            return False

    def _salvar_json_com_email(self, dados_originais: Dict, nome: str, email: str) -> bool:
        try:
            dados_atualizados = dados_originais.copy()
            if 'dados' not in dados_atualizados: dados_atualizados['dados'] = {}
            dados_atualizados['dados']['email_contato'] = email
            
            if 'metadados' not in dados_atualizados: dados_atualizados['metadados'] = {}
            dados_atualizados['metadados'].update({
                'email_processado_em': datetime.now().isoformat(),
                'email_processado_por': f"Gemini {self.modelo_config['name']}",
                'email_encontrado_com_sucesso': email != "Não encontrado",
                'versao_buscador': "3.0"
            })
            
            nome_arquivo = self._criar_nome_arquivo_seguro(nome)
            arquivo_saida = self.pasta_output / f"{nome_arquivo}_email_{self.timestamp}.json"
            
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                json.dump(dados_atualizados, f, ensure_ascii=False, indent=2)
                
            status_icon = "✅" if email != "Não encontrado" else "⚠️"
            print(f"    {status_icon} Salvo: {arquivo_saida.name} | Email: {email}")
            return True
        except Exception as e:
            print(f"    ❌ Erro ao salvar JSON para {nome}: {e}")
            return False

    def _salvar_log_busca(self, nome: str, email: str, resultado_completo: str):
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(), "pesquisador": nome,
                "modelo_usado": self.modelo_config['name'],
                "resultado": {"email_encontrado": email, "sucesso": email != "Não encontrado"},
                "log_completo": resultado_completo
            }
            nome_arquivo = self._criar_nome_arquivo_seguro(nome)
            arquivo_log = self.pasta_logs / f"busca_{nome_arquivo}_{self.timestamp}.json"
            with open(arquivo_log, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"    ⚠️ Erro ao salvar log para {nome}: {e}")

    def _criar_nome_arquivo_seguro(self, nome: str) -> str:
        nome_limpo = re.sub(r'[^\w\s-]', '', nome)
        return re.sub(r'\s+', '_', nome_limpo.strip())[:50]

    async def executar_busca_completa(self):
        print("\n" + "="*70)
        print("🔍 ETAPA 3: BUSCADOR DE EMAILS FAPESP")
        print("="*70)
        
        df_pesquisadores = self.carregar_csv_pesquisadores()
        if df_pesquisadores is None:
            return False
            
        pesquisadores = df_pesquisadores['nome'].tolist()
        total_pesquisadores = len(pesquisadores)
        
        print(f"\n⚙️ CONFIGURAÇÃO ATIVA:")
        print(f"   🤖 Modelo: {self.modelo_config['display']}")
        print(f"   🖥️ Browser: {"Headless (invisível)" if self.headless else "Visível"}")
        print(f"   👁️ Visão: {"Ativada" if self.use_vision else "Desativada"}")
        print(f"   📊 Total de pesquisadores: {total_pesquisadores}")
        
        resposta = input(f"\n🚀 Processar {total_pesquisadores} pesquisadores? (s/N): ").lower()
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("❌ Operação cancelada pelo usuário")
            return False
            
        print(f"\n🚀 INICIANDO PROCESSAMENTO...")
        tempo_inicio = time.time()
        
        for indice, nome in enumerate(pesquisadores, 1):
            print(f"\n[{indice}/{total_pesquisadores}]--------------------------------------------------")
            self.stats["total_processados"] += 1
            try:
                json_path = self.encontrar_json_pesquisador(nome)
                if not json_path:
                    print(f"  ❌ Pulando - JSON não encontrado para {nome}")
                    self.stats["erros"] += 1
                    continue
                await self.processar_pesquisador(nome, json_path)
            except Exception as e:
                print(f"  ❌ ERRO CRÍTICO no processamento de {nome}: {e}")
                self.stats["erros"] += 1
            
            if indice < total_pesquisadores:
                print(f"  ⏳ Pausando {DELAY_ENTRE_BUSCAS}s...")
                await asyncio.sleep(DELAY_ENTRE_BUSCAS)
                
        self._mostrar_relatorio_final(time.time() - tempo_inicio)
        return True

    def _mostrar_relatorio_final(self, tempo_total: float):
        print(f"\n" + "="*70)
        print("🎉 PROCESSAMENTO DA ETAPA 3 CONCLUÍDO!")
        print("="*70)
        print(f"⏱️  Tempo total: {tempo_total/60:.1f} minutos")
        print(f"📊 ESTATÍSTICAS:")
        print(f"   • Total processados: {self.stats['total_processados']}")
        print(f"   • Emails encontrados: {self.stats['emails_encontrados']}")
        print(f"   • Emails não encontrados: {self.stats['emails_nao_encontrados']}")
        print(f"   • Emails já existiam: {self.stats['emails_ja_existiam']}")
        print(f"   • Erros: {self.stats['erros']}")
        if self.stats["total_processados"] > 0:
            sucesso_pct = ((self.stats["emails_encontrados"] + self.stats["emails_ja_existiam"]) / self.stats["total_processados"]) * 100
            print(f"   📈 Taxa de sucesso: {sucesso_pct:.1f}%")
        print(f"\n📁 Resultados salvos em: {self.pasta_output}")
        print(f"   Logs salvos em: {self.pasta_logs}")

async def main():
    """Função principal para execução standalone da Etapa 3."""
    try:
        # O menu de seleção de modelo pode ser adicionado aqui
        modelo_config = MODELOS_GEMINI['browser']['2']
        buscador = BuscadorEmailFAPESP(modelo_config, headless=True, use_vision=True)
        await buscador.executar_busca_completa()
    except KeyboardInterrupt:
        print("\n⛔ Operação interrompida pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NA ETAPA 3: {e}")

if __name__ == "__main__":
    # Este bloco permite que o script seja executado de forma independente
    # para testes ou execução focada apenas nesta etapa.
    main_loop = asyncio.get_event_loop()
    try:
        main_loop.run_until_complete(main())
    finally:
        main_loop.close()
