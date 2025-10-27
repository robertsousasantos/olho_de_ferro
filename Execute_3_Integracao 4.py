#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BUSCADOR DE EMAILS FAPESP - VERSÃO COMPLETA E FINAL
=============================================================================
Integração Browser-use + Google Gemini para busca automatizada de emails
Lê CSV de pesquisadores, encontra JSONs correspondentes e busca emails específicos

Autor: Assistente Claude
Versão: 3.0 Final
Data: 2025
=============================================================================
"""

import asyncio
import os
import json
import time
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# =============================================================================
# CONFIGURAÇÃO API GOOGLE GEMINI
# =============================================================================
GOOGLE_API_KEY = ''
os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY

# =============================================================================
# IMPORTS E VERIFICAÇÃO DE DEPENDÊNCIAS
# =============================================================================
try:
    from browser_use import Agent
    from browser_use.llm.google import ChatGoogle
    print("✅ Browser-use e Gemini carregados com sucesso!")
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("\n🔧 INSTALE AS DEPENDÊNCIAS:")
    print("pip install browser-use google-generativeai pandas")
    print("playwright install chromium")
    exit(1)

# =============================================================================
# CONFIGURAÇÃO DE PASTAS
# =============================================================================
BASE_PATH = Path("/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro")

PASTA_CSV = BASE_PATH / "Passo_4_lista_email"
PASTA_JSONS_INPUT = BASE_PATH / "Passo_2_json_extraido"  
PASTA_JSONS_OUTPUT = BASE_PATH / "Passo_5_json_final"
PASTA_LOGS = BASE_PATH / "Logs_busca_email"

DELAY_ENTRE_BUSCAS = 5  # segundos

# =============================================================================
# MODELOS GEMINI DISPONÍVEIS
# =============================================================================
MODELOS_GEMINI = {
    "1": {
        "name": "gemini-2.5-pro",
        "display": "🚀 Gemini 2.5 Pro (Mais Avançado)",
        "temperature": 0.1,
        "max_steps": 40,
        "description": "Modelo mais poderoso, melhor para tarefas complexas"
    },
    "2": {
        "name": "gemini-2.5-flash", 
        "display": "⚡ Gemini 2.5 Flash (Recomendado)",
        "temperature": 0.1,
        "max_steps": 35,
        "description": "Equilibrio perfeito entre velocidade e qualidade"
    },
    "3": {
        "name": "gemini-2.5-flash-lite",
        "display": "🏃 Gemini 2.5 Flash Lite",
        "temperature": 0.1,
        "max_steps": 30,
        "description": "Versão mais rápida e econômica"
    },
    "4": {
        "name": "gemini-2.0-flash",
        "display": "🔥 Gemini 2.0 Flash",
        "temperature": 0.1,
        "max_steps": 35,
        "description": "Versão estável anterior"
    },
    "5": {
        "name": "gemini-2.0-flash-lite",
        "display": "💨 Gemini 2.0 Flash Lite", 
        "temperature": 0.1,
        "max_steps": 30,
        "description": "Versão lite da 2.0"
    },
    "6": {
        "name": "gemini-2.0-flash-exp",
        "display": "🧪 Gemini 2.0 Flash Experimental",
        "temperature": 0.1,
        "max_steps": 35,
        "description": "Recursos experimentais"
    },
    "7": {
        "name": "gemini-2.0-flash-lite-preview-02-05",
        "display": "👀 Gemini 2.0 Flash Lite Preview",
        "temperature": 0.1,
        "max_steps": 30,
        "description": "Preview da versão lite"
    },
    "8": {
        "name": "Gemini-2.0-exp",
        "display": "🔬 Gemini 2.0 Experimental",
        "temperature": 0.1,
        "max_steps": 35,
        "description": "Versão experimental completa"
    },
    "9": {
        "name": "gemma-3-27b-it",
        "display": "🤖 Gemma 3 27B IT",
        "temperature": 0.2,
        "max_steps": 30,
        "description": "Modelo Gemma especializado"
    }
}

# =============================================================================
# CLASSE PRINCIPAL - BUSCADOR DE EMAILS
# =============================================================================
class BuscadorEmailFAPESP:
    """
    Classe principal para busca automatizada de emails de pesquisadores FAPESP
    """
    
    def __init__(self, modelo_config: Dict, headless: bool = True, use_vision: bool = True):
        """
        Inicializa o buscador de emails
        
        Args:
            modelo_config: Configuração do modelo Gemini
            headless: Se True, browser executa invisível  
            use_vision: Se True, usa capacidades visuais do modelo
        """
        self.pasta_csv = PASTA_CSV
        self.pasta_input = PASTA_JSONS_INPUT
        self.pasta_output = PASTA_JSONS_OUTPUT
        self.pasta_logs = PASTA_LOGS
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Configurações
        self.modelo_config = modelo_config
        self.headless = headless
        self.use_vision = use_vision
        self.llm = None
        
        # Estatísticas
        self.stats = {
            "total_processados": 0,
            "emails_encontrados": 0, 
            "emails_nao_encontrados": 0,
            "emails_ja_existiam": 0,
            "erros": 0
        }
        
        self._criar_pastas()
        self._inicializar_gemini()

    def _criar_pastas(self):
        """Cria as pastas necessárias se não existirem"""
        for pasta in [self.pasta_output, self.pasta_logs]:
            pasta.mkdir(parents=True, exist_ok=True)
            
    def _inicializar_gemini(self):
        """Inicializa o modelo Gemini"""
        try:
            self.llm = ChatGoogle(
                model=self.modelo_config['name'],
                temperature=self.modelo_config['temperature'],
                api_key=GOOGLE_API_KEY
            )
            
            print(f"✅ Gemini inicializado: {self.modelo_config['display']}")
            print(f"🖥️  Browser: {'Headless (invisível)' if self.headless else 'Visível'}")
            print(f"👁️  Visão: {'Ativada' if self.use_vision else 'Desativada'}")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar Gemini: {e}")
            raise

    # =========================================================================
    # MÉTODOS DE CARREGAMENTO DE DADOS
    # =========================================================================
    
    def carregar_csv_pesquisadores(self) -> Optional[pd.DataFrame]:
        """Carrega o CSV com lista de pesquisadores"""
        try:
            arquivos_csv = list(self.pasta_csv.glob("*.csv"))
            if not arquivos_csv:
                print(f"❌ Nenhum CSV encontrado em {self.pasta_csv}")
                return None
                
            csv_path = arquivos_csv[0]
            print(f"📊 Carregando: {csv_path.name}")
            
            df = pd.read_csv(csv_path, encoding='utf-8')
            print(f"📋 Pesquisadores encontrados: {len(df)}")
            
            if 'nome' not in df.columns:
                print(f"❌ Coluna 'nome' não encontrada!")
                print(f"Colunas disponíveis: {list(df.columns)}")
                return None
                
            return df
            
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            return None

    def encontrar_json_pesquisador(self, nome_pesquisador: str) -> Optional[Path]:
        """Encontra o arquivo JSON correspondente ao pesquisador"""
        try:
            arquivos_json = list(self.pasta_input.glob("*.json"))
            
            # Limpar nome para comparação
            nome_limpo = re.sub(r'[^\w\s]', '', nome_pesquisador).lower()
            palavras_nome = [p for p in nome_limpo.split() if len(p) > 2]
            
            for arquivo in arquivos_json:
                try:
                    with open(arquivo, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'dados' in data and 'nome_completo' in data['dados']:
                        nome_json = data['dados']['nome_completo'].lower()
                        
                        # Verificar correspondência de palavras
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

    # =========================================================================
    # MÉTODOS DE BUSCA DE EMAIL
    # =========================================================================
    
    def criar_prompt_busca_email(self, nome: str, instituicao: str = "") -> str:
        """Cria o prompt otimizado para busca de email"""
        return f"""
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
"""

    async def buscar_email_pesquisador(self, nome: str, instituicao: str = "") -> str:
        """Executa a busca de email usando Gemini + Browser-use"""
        print(f"  🔍 Buscando email: {nome}")
        
        try:
            prompt = self.criar_prompt_busca_email(nome, instituicao)
            
            # Criar agente com configurações corretas
            agent = Agent(
                task=prompt,
                llm=self.llm,
                use_vision=self.use_vision,
                headless=self.headless  # Configuração crítica para headless
            )
            
            print(f"    🚀 Executando busca com Gemini...")
            resultado = await agent.run(max_steps=self.modelo_config['max_steps'])
            
            # Processar e validar resultado
            email = self._extrair_email_do_resultado(str(resultado), nome)
            
            # Salvar log da busca
            self._salvar_log_busca(nome, email, str(resultado))
            
            return email
            
        except Exception as e:
            print(f"    ❌ ERRO na busca: {e}")
            return "Não encontrado"

    def _extrair_email_do_resultado(self, resultado: str, nome_pesquisador: str) -> str:
        """Extrai e valida o email do resultado da busca"""
        try:
            # Lista de emails genéricos para rejeitar
            emails_genericos = [
                'secretaria@', 'diretoria@', 'contato@', 'info@', 'admin@',
                'atendimento@', 'administracao@', 'departamento@', 'depto@',
                'webmaster@', 'suporte@', 'geral@', 'coordenacao@',
                'pos-graduacao@', 'posgrad@', 'secretaria.@'
            ]
            
            linhas = resultado.split('\n')
            email_validado = False
            email_encontrado = None
            
            # Verificar validação
            for linha in linhas:
                if 'VALIDAÇÃO:' in linha and 'Sim' in linha:
                    email_validado = True
                    break
                    
            # Extrair email
            for linha in linhas:
                linha = linha.strip()
                
                if '📧 EMAIL:' in linha:
                    email = linha.split('📧 EMAIL:')[1].strip()
                    
                    if email and email != "Não encontrado" and '@' in email:
                        # Verificar se não é genérico
                        email_valido = True
                        for generico in emails_genericos:
                            if generico in email.lower():
                                email_valido = False
                                print(f"    ❌ Email rejeitado (genérico): {email}")
                                break
                                
                        if email_valido and email_validado:
                            print(f"    ✅ Email encontrado: {email}")
                            return email
                            
            # Busca alternativa por padrões de email
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_encontrados = re.findall(email_pattern, resultado)
            
            for email in emails_encontrados:
                email_valido = True
                for generico in emails_genericos:
                    if generico in email.lower():
                        email_valido = False
                        break
                        
                if email_valido:
                    print(f"    ✅ Email extraído: {email}")
                    return email
                    
            print(f"    ⚠️ Nenhum email específico encontrado")
            return "Não encontrado"
            
        except Exception as e:
            print(f"    ❌ Erro ao processar resultado: {e}")
            return "Não encontrado"

    # =========================================================================
    # MÉTODOS DE PROCESSAMENTO E SALVAMENTO
    # =========================================================================
    
    async def processar_pesquisador(self, nome: str, json_path: Path) -> bool:
        """Processa um pesquisador completo: busca email e salva resultado"""
        try:
            # Carregar dados do pesquisador
            with open(json_path, 'r', encoding='utf-8') as f:
                dados_pesquisador = json.load(f)
                
            instituicao = dados_pesquisador.get('dados', {}).get('instituicao_vinculo', '')
            
            print(f"\n📋 Processando: {nome}")
            print(f"🏢 Instituição: {instituicao}")
            print(f"📄 Arquivo: {json_path.name}")
            
            # Verificar se já tem email
            email_atual = dados_pesquisador.get('dados', {}).get('email_contato', 'Não encontrado')
            
            if email_atual != 'Não encontrado' and '@' in email_atual:
                print(f"  ✅ Email já existe: {email_atual}")
                self.stats["emails_ja_existiam"] += 1
                return self._salvar_json_com_email(dados_pesquisador, nome, email_atual)
            
            # Buscar novo email
            email_encontrado = await self.buscar_email_pesquisador(nome, instituicao)
            
            # Atualizar estatísticas
            if email_encontrado != "Não encontrado":
                self.stats["emails_encontrados"] += 1
            else:
                self.stats["emails_nao_encontrados"] += 1
                
            return self._salvar_json_com_email(dados_pesquisador, nome, email_encontrado)
            
        except Exception as e:
            print(f"  ❌ Erro ao processar: {e}")
            self.stats["erros"] += 1
            return False

    def _salvar_json_com_email(self, dados_originais: Dict, nome: str, email: str) -> bool:
        """Salva o JSON com o email adicionado/atualizado"""
        try:
            # Preparar dados atualizados
            dados_atualizados = dados_originais.copy()
            
            if 'dados' not in dados_atualizados:
                dados_atualizados['dados'] = {}
                
            dados_atualizados['dados']['email_contato'] = email
            
            # Atualizar metadados
            if 'metadados' not in dados_atualizados:
                dados_atualizados['metadados'] = {}
                
            dados_atualizados['metadados'].update({
                'email_processado_em': datetime.now().isoformat(),
                'email_processado_por': f"Gemini {self.modelo_config['name']}",
                'email_encontrado_com_sucesso': email != "Não encontrado",
                'versao_buscador': "3.0"
            })
            
            # Criar nome do arquivo
            nome_arquivo = self._criar_nome_arquivo_seguro(nome)
            arquivo_saida = self.pasta_output / f"{nome_arquivo}_email_{self.timestamp}.json"
            
            # Salvar arquivo
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                json.dump(dados_atualizados, f, ensure_ascii=False, indent=2)
                
            status_icon = "✅" if email != "Não encontrado" else "⚠️"
            print(f"    {status_icon} Salvo: {arquivo_saida.name}")
            print(f"    📧 Email: {email}")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Erro ao salvar: {e}")
            return False

    def _salvar_log_busca(self, nome: str, email: str, resultado_completo: str):
        """Salva log detalhado da busca"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "pesquisador": nome,
                "modelo_usado": self.modelo_config['name'],
                "configuracoes": {
                    "headless": self.headless,
                    "use_vision": self.use_vision,
                    "temperatura": self.modelo_config['temperature'],
                    "max_steps": self.modelo_config['max_steps']
                },
                "resultado": {
                    "email_encontrado": email,
                    "sucesso": email != "Não encontrado"
                },
                "log_completo": resultado_completo
            }
            
            nome_arquivo = self._criar_nome_arquivo_seguro(nome)
            arquivo_log = self.pasta_logs / f"busca_{nome_arquivo}_{self.timestamp}.json"
            
            with open(arquivo_log, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"    ⚠️ Erro ao salvar log: {e}")

    def _criar_nome_arquivo_seguro(self, nome: str) -> str:
        """Cria nome de arquivo seguro removendo caracteres especiais"""
        nome_limpo = re.sub(r'[^\w\s-]', '', nome)
        nome_seguro = re.sub(r'\s+', '_', nome_limpo.strip())
        return nome_seguro[:50]  # Limitar tamanho

    # =========================================================================
    # MÉTODO PRINCIPAL DE EXECUÇÃO
    # =========================================================================
    
    async def executar_busca_completa(self):
        """Executa o processo completo de busca de emails"""
        print("\n" + "="*70)
        print("🔍 BUSCADOR DE EMAILS FAPESP - INICIANDO")
        print("🤖 Powered by Google Gemini + Browser-use")
        print("="*70)
        
        # Carregar dados
        df_pesquisadores = self.carregar_csv_pesquisadores()
        if df_pesquisadores is None:
            return False
            
        pesquisadores = df_pesquisadores['nome'].tolist()
        total_pesquisadores = len(pesquisadores)
        
        # Mostrar configuração
        print(f"\n⚙️ CONFIGURAÇÃO ATIVA:")
        print(f"   🤖 Modelo: {self.modelo_config['display']}")
        print(f"   🖥️ Browser: {'Headless (invisível)' if self.headless else 'Visível'}")
        print(f"   👁️ Visão: {'Ativada' if self.use_vision else 'Desativada'}")
        print(f"   📊 Total de pesquisadores: {total_pesquisadores}")
        
        # Confirmação
        if not self._confirmar_execucao(total_pesquisadores):
            return False
            
        # Processar pesquisadores
        print(f"\n🚀 INICIANDO PROCESSAMENTO...")
        tempo_inicio = time.time()
        
        for indice, nome in enumerate(pesquisadores, 1):
            print(f"\n[{indice}/{total_pesquisadores}] {nome}")
            self.stats["total_processados"] += 1
            
            try:
                # Encontrar JSON correspondente
                json_path = self.encontrar_json_pesquisador(nome)
                if not json_path:
                    print(f"  ❌ Pulando - JSON não encontrado")
                    self.stats["erros"] += 1
                    continue
                    
                # Processar pesquisador
                await self.processar_pesquisador(nome, json_path)
                
            except Exception as e:
                print(f"  ❌ ERRO CRÍTICO: {e}")
                self.stats["erros"] += 1
                
            # Pausa entre buscas
            if indice < total_pesquisadores:
                print(f"  ⏳ Pausando {DELAY_ENTRE_BUSCAS}s...")
                await asyncio.sleep(DELAY_ENTRE_BUSCAS)
                
        # Relatório final
        self._mostrar_relatorio_final(time.time() - tempo_inicio)
        return True

    def _confirmar_execucao(self, total: int) -> bool:
        """Solicita confirmação do usuário para iniciar"""
        resposta = input(f"\n🚀 Processar {total} pesquisadores? (s/N): ").lower()
        if resposta in ['s', 'sim', 'y', 'yes']:
            return True
        print("❌ Operação cancelada pelo usuário")
        return False

    def _mostrar_relatorio_final(self, tempo_total: float):
        """Mostra relatório final da execução"""
        print(f"\n" + "="*70)
        print("🎉 PROCESSAMENTO CONCLUÍDO!")
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
            
        print(f"\n📁 RESULTADOS SALVOS EM:")
        print(f"   • JSONs: {self.pasta_output}")
        print(f"   • Logs: {self.pasta_logs}")

# =============================================================================
# FUNÇÕES DE INTERFACE DO USUÁRIO
# =============================================================================

def mostrar_banner():
    """Exibe banner inicial"""
    print("\n" + "="*70)
    print("🚀 BUSCADOR DE EMAILS FAPESP - VERSÃO 3.0")
    print("🔥 Powered by Google Gemini + Browser-use")
    print("⚡ Busca automatizada de emails de pesquisadores")
    print("="*70)

def selecionar_modelo_gemini() -> Dict:
    """Interface para seleção do modelo Gemini"""
    print("\n🤖 MODELOS GEMINI DISPONÍVEIS:")
    print("-" * 50)
    
    for chave, modelo in MODELOS_GEMINI.items():
        print(f"{chave}. {modelo['display']}")
        print(f"   {modelo['description']}")
        print()
        
    while True:
        escolha = input("Escolha o modelo (1-9) [2 - Recomendado]: ").strip()
        if not escolha:
            escolha = "2"
            
        if escolha in MODELOS_GEMINI:
            return MODELOS_GEMINI[escolha]
        print("❌ Opção inválida! Tente novamente.")

def selecionar_modo_browser() -> bool:
    """Interface para seleção do modo do browser"""
    print("\n🖥️ MODO DO BROWSER:")
    print("1. 👻 Headless (invisível) - Mais rápido")
    print("2. 👀 Visível - Para acompanhar o processo")
    
    while True:
        escolha = input("\nEscolha (1-2) [1]: ").strip()
        if not escolha:
            escolha = "1"
            
        if escolha == "1":
            return True  # Headless
        elif escolha == "2":
            return False  # Visível
        print("❌ Opção inválida!")

def selecionar_capacidade_visual() -> bool:
    """Interface para seleção da capacidade visual"""
    print("\n👁️ CAPACIDADE VISUAL DO MODELO:")
    print("1. 🔥 Ativada (recomendado) - Melhor precisão")
    print("2. 📝 Desativada - Apenas texto")
    
    while True:
        escolha = input("\nEscolha (1-2) [1]: ").strip()
        if not escolha:
            escolha = "1"
            
        if escolha == "1":
            return True
        elif escolha == "2":
            return False
        print("❌ Opção inválida!")

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

async def main():
    """Função principal do programa"""
    try:
        # Mostrar banner
        mostrar_banner()
        
        # Configurações do usuário
        print("🔧 CONFIGURAÇÃO DO SISTEMA")
        modelo = selecionar_modelo_gemini()
        headless = selecionar_modo_browser()
        visao = selecionar_capacidade_visual()
        
        # Resumo das configurações
        print(f"\n✅ CONFIGURAÇÕES SELECIONADAS:")
        print(f"   🤖 {modelo['display']}")
        print(f"   🖥️ {'Headless (invisível)' if headless else 'Visível'}")
        print(f"   👁️ {'Visão ativada' if visao else 'Apenas texto'}")
        
        confirmacao = input(f"\n🚀 Continuar com essas configurações? (s/N): ").lower()
        if confirmacao not in ['s', 'sim', 'y', 'yes']:
            print("❌ Operação cancelada")
            return
            
        # Inicializar e executar buscador
        print("\n🔄 Inicializando sistema...")
        buscador = BuscadorEmailFAPESP(modelo, headless, visao)
        
        await buscador.executar_busca_completa()
        
    except KeyboardInterrupt:
        print("\n⛔ Operação interrompida pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        print("\n🔧 Verifique se as dependências estão instaladas:")
        print("pip install browser-use google-generativeai pandas")
        print("playwright install chromium")

# =============================================================================
# PONTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Programa encerrado")
    finally:
        input("\n📚 Pressione Enter para sair...")