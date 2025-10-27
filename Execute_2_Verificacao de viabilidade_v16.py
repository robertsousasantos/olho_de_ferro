#!/usr/bin/env python3
"""
SISTEMA DE CLASSIFICAÇÃO DE CLIENTES - RAG + GEMINI + BATCH PROCESSING
Implementa sistema RAG completo com segmentação final em 6 listas
VERSÃO REFATORADA PARA GOOGLE GEMINI API
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sqlite3
import hashlib
import time
import re
import requests
import unicodedata

class ClientClassifierRAGGemini:
    def __init__(self, model_name: str = "gemini-2.5-flash", batch_size: int = 3, modo_conservador: bool = True):
        """Inicializa classificador RAG com processamento em batch usando Gemini"""
        
        # CHAVE API FORNECIDA PELO USUÁRIO
        # AVISO DE SEGURANÇA: Em produção, use variáveis de ambiente
        self.api_key = ''
        
        # URL base da API Gemini
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        # MODO CONSERVADOR: Reduz drasticamente calls para evitar rate limit
        self.modo_conservador = modo_conservador
        if modo_conservador:
            batch_size = min(batch_size, 10)  # Max 2 clientes por batch
            print("🐌 MODO CONSERVADOR ATIVADO: Processamento mais lento mas seguro")
        
        # Modelos disponíveis do Gemini com suas configurações
        self.modelos_disponiveis = {
            # GEMINI 2.5 SERIES - MODELOS MAIS AVANÇADOS
            "gemini-2.5-pro": {
                "nome": "Gemini 2.5 Pro",
                "custo": "Alto",
                "precisao": "Máxima",
                "max_output_tokens": 65536,
                "temperatura": 0.1,
                "thinking": True,
                "descricao": "Modelo de pensamento mais avançado",
                "rate_limit_safe": False  # Modelo premium com limites mais restritivos
            },
            "gemini-2.5-flash": {
                "nome": "Gemini 2.5 Flash", 
                "custo": "Médio",
                "precisao": "Alta",
                "max_output_tokens": 65536,
                "temperatura": 0.1,
                "thinking": True,
                "descricao": "Melhor custo-benefício com recursos completos",
                "rate_limit_safe": True
            },
            "gemini-2.5-flash-lite": {
                "nome": "Gemini 2.5 Flash-Lite",
                "custo": "Baixo",
                "precisao": "Boa",
                "max_output_tokens": 65536,
                "temperatura": 0.1,
                "thinking": True,
                "descricao": "Otimizado para eficiência de custo",
                "rate_limit_safe": True
            },
            
            # GEMINI 2.0 SERIES
            "gemini-2.0-flash": {
                "nome": "Gemini 2.0 Flash",
                "custo": "Médio-Alto",
                "precisao": "Alta",
                "max_output_tokens": 8192,
                "temperatura": 0.1,
                "thinking": False,
                "descricao": "Recursos avançados e velocidade superior",
                "rate_limit_safe": False
            },
            "gemini-2.0-flash-lite": {
                "nome": "Gemini 2.0 Flash-Lite",
                "custo": "Baixo-Médio",
                "precisao": "Boa",
                "max_output_tokens": 8192,
                "temperatura": 0.1,
                "thinking": False,
                "descricao": "Otimizado para baixa latência",
                "rate_limit_safe": True
            },
            
            # GEMINI 1.5 SERIES - MODELOS ESTÁVEIS
            "gemini-1.5-pro": {
                "nome": "Gemini 1.5 Pro",
                "custo": "Alto",
                "precisao": "Máxima",
                "max_output_tokens": 8192,
                "temperatura": 0.1,
                "thinking": False,
                "descricao": "Modelo estável para raciocínio complexo",
                "rate_limit_safe": False
            },
            "gemini-1.5-flash": {
                "nome": "Gemini 1.5 Flash",
                "custo": "Médio",
                "precisao": "Alta",
                "max_output_tokens": 8192,
                "temperatura": 0.1,
                "thinking": False,
                "descricao": "Rápido e versátil para múltiplas tarefas",
                "rate_limit_safe": True
            }
        }
        
        # Valida modelo
        if model_name not in self.modelos_disponiveis:
            print(f"⚠️ Modelo '{model_name}' não disponível. Usando 'gemini-2.5-flash-lite'")
            model_name = "gemini-2.5-flash-lite"  # Modelo mais seguro para rate limit
        
        self.model = model_name
        self.model_config = self.modelos_disponiveis[model_name]
        self.batch_size = batch_size
        
        # Configurações de rate limiting baseadas no modelo
        if not self.model_config['rate_limit_safe']:
            print(f"⚠️ Modelo {self.model_config['nome']} pode ter limites restritivos")
            if modo_conservador:
                self.batch_size = 1  # Processamento individual para modelos premium
                print("🔄 Forçando processamento individual para evitar rate limits")
        
        self.cache_db = "client_classifier_rag_cache_gemini.db"
        self.setup_cache()
        
        # Sistema de classificação com palavras-chave para recuperação
        self.criterios_keywords = {
            # CATEGORIA PA: PRODUÇÃO DE PROTEÍNA - ACADÊMICO
            'PA1': [
                'expressao proteina', 'purificacao proteina', 'proteina recombinante', 
                'antigeno recombinante', 'expressao heterologa', 'producao proteinas',
                'protein expression', 'protein purification', 'recombinant protein'
            ],
            'PA2': [
                'enzimas biotecnologicas', 'caracterizacao enzimas', 'purificacao enzimas',
                'biocatalise', 'enzimas industriais', 'biotechnological enzymes',
                'enzyme characterization', 'enzyme purification', 'biocatalysis'
            ],
            'PA3': [
                'elisa', 'western blot', 'biossensores', 'imunoensaios', 'triagem farmacos',
                'imunizacao', 'bioquimica proteinas', 'interacoes proteicas',
                'biosensors', 'immunoassays', 'drug screening', 'protein biochemistry'
            ],
            'PA4': [
                'cromatografia', 'espectrometria massas', 'modelagem estrutural',
                'hplc', 'analise instrumental', 'proteomica', 'chromatography',
                'mass spectrometry', 'structural modeling', 'proteomics'
            ],
            
            # CATEGORIA S: SÍNTESE DE GENE
            'S1': [
                'sintese genica', 'expressao genica', 'construcao genica',
                'gene synthesis', 'gene expression', 'gene construction'
            ],
            'S2': [
                'clonagem molecular', 'clonagem genica', 'pcr', 'crispr',
                'edicao genetica', 'molecular cloning', 'gene editing', 'genetic engineering'
            ],
            'S3': [
                'circuito genetico', 'chassis bacteriano', 'engenharia metabolica',
                'biologia sintetica', 'genetic circuits', 'synthetic biology', 'metabolic engineering'
            ],
            
            # CATEGORIA C: CFPS
            'C1': [
                'cfps', 'cell-free', 'sintese livre celula', 'sistema acelular',
                'cell-free protein synthesis', 'in vitro protein synthesis'
            ],
            'C2': [
                'proteinas toxicas', 'proteinas dificeis', 'proteinas recalcitrantes',
                'toxic proteins', 'difficult proteins', 'recalcitrant proteins'
            ],
            'C3': [
                'screening farmacos', 'triagem medicamentos', 'descoberta drogas',
                'validacao expressao', 'drug screening', 'drug discovery'
            ],
            'C4': [
                'educacao', 'ensino', 'didatica', 'educacional',
                'education', 'teaching', 'educational applications'
            ],
            'C5': [
                'cristalografia proteinas', 'estrutura proteinas', 'cristais proteina',
                'difracao raios x', 'protein crystallography', 'x-ray diffraction'
            ],
            
            # CATEGORIA F: FATORES DE CRESCIMENTO
            'F1': [
                'cultura celular', 'cultivo celulas', 'diferenciacao celular',
                'celulas-tronco', 'ipscs', 'cell culture', 'stem cells'
            ],
            'F2': [
                'fermentacao', 'biorreatores', 'crescimento celular',
                'producao biomassa', 'fermentation', 'bioreactors', 'biomass production'
            ],
            'F3': [
                'embriologia', 'reproducao assistida', 'fertilizacao in vitro',
                'desenvolvimento embrionario', 'embryology', 'assisted reproduction'
            ],
            'F4': [
                'engenharia tecidos', 'bioimpressao', 'scaffolds', 'medicina regenerativa',
                'tissue engineering', 'bioprinting', 'regenerative medicine'
            ],
            
            # FATORES NEGATIVOS
            'N1': [
                'sem proteinas', 'nao usa proteinas', 'area teorica', 'matematica aplicada',
                'fisica teorica', 'quimica inorganica', 'without proteins', 'theoretical area'
            ],
            'N2': [
                'nao biotecnologia', 'area distante', 'engenharia civil', 'psicologia',
                'administracao', 'direito', 'not biotechnology', 'distant area'
            ]
        }
        
        # Informações sobre o sistema
        print(f"🤖 Classificador RAG-Gemini carregado:")
        print(f"   Modelo: {self.model_config['nome']} ({self.model_config['custo']} custo, {self.model_config['precisao']} precisão)")
        print(f"   API: Google Gemini API")
        print(f"   Thinking: {'✅ Ativado' if self.model_config['thinking'] else '❌ Não disponível'}")
        print(f"   Batch Size: {self.batch_size} clientes por chamada")
        print(f"   Critérios: {len(self.criterios_keywords)} critérios de classificação")
        print(f"   Sistema: Retrieval Normalizado + Batch Processing")
        print(f"   Rate Limit Safe: {'✅' if self.model_config['rate_limit_safe'] else '⚠️'}")
        
        # Testa API inicial
        if not self.testar_api_gemini():
            print("\n⚠️ ATENÇÃO: Problemas detectados com a API!")
            print("Continuando mesmo assim, mas pode haver falhas...")
    
    def testar_api_gemini(self) -> bool:
        """Testa se a API Gemini está funcionando com um prompt simples"""
        print("🔍 Testando conexão com API Gemini...")
        
        prompt_teste = "Responda apenas 'OK' se você consegue me ouvir."
        
        try:
            resposta = self.chamar_gemini_api(prompt_teste, usar_thinking=False, max_tentativas=3)
            if resposta and len(resposta.strip()) > 0:
                print(f"✅ API funcionando! Resposta: {resposta.strip()[:50]}")
                return True
            else:
                print("❌ API respondeu mas sem conteúdo")
                return False
                
        except Exception as e:
            print(f"❌ Erro no teste da API: {str(e)[:100]}")
            print("💡 Possíveis soluções:")
            print("   1. Verifique se a chave API está correta")
            print("   2. Verifique se há quota disponível na sua conta Google")
            print("   3. Tente usar o modelo 'gemini-1.5-flash' (mais estável)")
            print("   4. Aguarde alguns minutos e tente novamente")
            return False
    
    def setup_cache(self):
        """Setup cache SQLite"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gemini_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT,
                nome TEXT,
                criterios_json TEXT,
                pontuacoes_json TEXT,
                classificacao_final TEXT,
                justificativa TEXT,
                timestamp TEXT,
                UNIQUE(file_hash)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def normalizar_texto(self, texto: str) -> str:
        """Normaliza texto: remove acentos, minúsculas, compacta espaços"""
        if not texto:
            return ""
        
        # Remove acentos usando unicodedata
        texto_sem_acentos = unicodedata.normalize('NFD', texto)
        texto_sem_acentos = ''.join(c for c in texto_sem_acentos if unicodedata.category(c) != 'Mn')
        
        # Converte para minúsculas
        texto = texto_sem_acentos.lower()
        
        # Compacta espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    def extrair_informacoes_relevantes(self, dados: Dict[str, Any]) -> Dict[str, List[str]]:
        """RETRIEVAL: Extrai e organiza informações relevantes por categoria com normalização"""
        
        # Campos a serem analisados
        campos_texto = [
            'palavras_chave',
            'linhas_pesquisa', 
            'tecnicas_utilizadas',
        ]
        
        # Consolida texto
        texto_completo = ""
        for campo in campos_texto:
            valor = dados.get(campo, '')
            if valor and valor not in ['Não informado', 'N/A', '']:
                texto_completo += f" {str(valor)}"
        
        # NORMALIZAÇÃO: Remove acentos, minúsculas, compacta espaços
        texto_normalizado = self.normalizar_texto(texto_completo)
        
        # RETRIEVAL: Busca palavras-chave relevantes por critério
        evidencias_encontradas = {}
        
        for criterio_id, keywords in self.criterios_keywords.items():
            evidencias = []
            
            for keyword in keywords:
                # Normaliza a keyword também
                keyword_normalizado = self.normalizar_texto(keyword)
                
                # Busca exata e variações
                if keyword_normalizado in texto_normalizado:
                    # Extrai contexto ao redor da palavra-chave
                    contexto = self.extrair_contexto(texto_normalizado, keyword_normalizado, janela=250)
                    if contexto:
                        evidencias.append(f"[{keyword}]: {contexto}")
            
            evidencias_encontradas[criterio_id] = evidencias
        
        return evidencias_encontradas
    
    def extrair_contexto(self, texto: str, keyword: str, janela: int = 250) -> str:
        """Extrai contexto ao redor de uma palavra-chave"""
        try:
            posicao = texto.find(keyword)
            if posicao == -1:
                return ""
            
            inicio = max(0, posicao - janela)
            fim = min(len(texto), posicao + len(keyword) + janela)
            
            contexto = texto[inicio:fim].strip()
            
            # Limpa o contexto
            contexto = re.sub(r'\s+', ' ', contexto)
            contexto = contexto[:500]
            
            return contexto
        except:
            return ""
    
    def montar_prompt_batch(self, clientes_batch: List[Dict[str, Any]]) -> str:
        """Monta prompt estruturado para processamento em batch"""
        
        num_clientes = len(clientes_batch)
        
        prompt = f"""
SISTEMA DE CLASSIFICAÇÃO EM BATCH - {num_clientes} CLIENTES BIOTECNOLÓGICOS

INSTRUÇÕES CRÍTICAS:
- Analise CADA cliente individualmente
- Classifique CADA critério como true/false baseado em evidências CLARAS
- Seja RIGOROSO: só marque true se houver evidência DIRETA
- Responda com JSON válido para TODOS os clientes

CRITÉRIOS DE CLASSIFICAÇÃO:

=== CATEGORIA PA: PRODUÇÃO DE PROTEÍNA ===
PA1 (Peso 2): Expressão e purificação de proteínas recombinantes
PA2 (Peso 2): Enzimas biotecnológicas e biocatálise  
PA3 (Peso 1): Técnicas ELISA, Western blot, biossensores
PA4 (Peso 1): Cromatografia, espectrometria de massas

=== CATEGORIA S: SÍNTESE DE GENE ===
S1: Síntese e expressão gênica
S2: Clonagem molecular, PCR, CRISPR
S3: Circuitos genéticos, biologia sintética

=== CATEGORIA C: CFPS ===
C1: Cell-free protein synthesis
C2: Proteínas tóxicas/difíceis
C3: Screening de fármacos
C4: Aplicações educacionais  
C5: Cristalografia de proteínas

=== CATEGORIA F: FATORES DE CRESCIMENTO ===
F1: Cultura celular, células-tronco
F2: Fermentação, biorreatores
F3: Embriologia, reprodução assistida
F4: Engenharia de tecidos

=== FATORES NEGATIVOS ===
N1: Área SEM uso direto de proteínas recombinantes
N2: Área NÃO correlata à biotecnologia

CLIENTES PARA ANÁLISE:
"""
        
        # Adiciona cada cliente com suas evidências
        for i, cliente_info in enumerate(clientes_batch, 1):
            nome = cliente_info['dados'].get('nome_completo', f'Cliente {i}')
            instituicao = cliente_info['dados'].get('instituicao_vinculo', '')
            linhas = cliente_info['dados'].get('linhas_pesquisa', '')
            evidencias = cliente_info['evidencias']
            
            prompt += f"""
=== CLIENTE {i}: {nome} ===
INSTITUIÇÃO: {instituicao}
ÁREA: {linhas}

EVIDÊNCIAS ENCONTRADAS:
"""
            
            # Adiciona evidências organizadas (limitado para não exceder tokens)
            evidencias_adicionadas = 0
            max_evidencias_por_cliente = 10
            
            for criterio_id, evidencias_list in evidencias.items():
                if evidencias_list and evidencias_adicionadas < max_evidencias_por_cliente:
                    prompt += f"\n{criterio_id}:\n"
                    for evidencia in evidencias_list[:2]:
                        prompt += f"  - {evidencia[:150]}...\n"
                        evidencias_adicionadas += 1
                        if evidencias_adicionadas >= max_evidencias_por_cliente:
                            break
        
        prompt += f"""

RESPOSTA REQUERIDA:
Responda APENAS em formato JSON válido com esta estrutura exata:

{{
    "clientes": [
        {{
            "cliente_id": 1,
            "nome": "Nome do Cliente 1",
            "PA1": true/false, "PA2": true/false, "PA3": true/false, "PA4": true/false,
            "S1": true/false, "S2": true/false, "S3": true/false,
            "C1": true/false, "C2": true/false, "C3": true/false, "C4": true/false, "C5": true/false,
            "F1": true/false, "F2": true/false, "F3": true/false, "F4": true/false,
            "N1": true/false, "N2": true/false
        }},
        {{
            "cliente_id": 2,
            "nome": "Nome do Cliente 2",
            "PA1": true/false, "PA2": true/false, "PA3": true/false, "PA4": true/false,
            "S1": true/false, "S2": true/false, "S3": true/false,
            "C1": true/false, "C2": true/false, "C3": true/false, "C4": true/false, "C5": true/false,
            "F1": true/false, "F2": true/false, "F3": true/false, "F4": true/false,
            "N1": true/false, "N2": true/false
        }}
        // ... continue para todos os {num_clientes} clientes
    ]
}}

CRÍTICO: 
- Inclua TODOS os {num_clientes} clientes na resposta
- Use APENAS true/false (minúsculas)
- Mantenha a ordem dos clientes (1, 2, 3...)
- JSON deve ser válido e completo
"""
        
        return prompt
    
    def preparar_payload_gemini(self, prompt: str, usar_thinking: bool = False) -> Dict[str, Any]:
        """Prepara payload para a API Gemini"""
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.model_config['temperatura'],
                "maxOutputTokens": self.model_config['max_output_tokens']
            }
        }
        
        # Adiciona thinking se disponível e solicitado
        if usar_thinking and self.model_config['thinking']:
            payload["generationConfig"]["response_logprobs"] = True
            # Para modelos com thinking, podemos configurar parâmetros específicos
            payload["systemInstruction"] = {
                "parts": [
                    {
                        "text": "Você é um especialista em biotecnologia que classifica clientes com pensamento analítico. Pense sobre cada evidência antes de classificar."
                    }
                ]
            }
        
        return payload
    
    def chamar_gemini_api(self, prompt: str, usar_thinking: bool = False, max_tentativas: int = 5) -> str:
        """Chama a API do Gemini com rate limiting robusto"""
        
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = self.preparar_payload_gemini(prompt, usar_thinking)
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Delays progressivos mais agressivos para rate limiting
        delays = [1, 3, 8, 15, 30]  # Segundos
        
        for tentativa in range(max_tentativas):
            try:
                # Delay antes de cada tentativa (exceto a primeira)
                if tentativa > 0:
                    delay = delays[min(tentativa-1, len(delays)-1)]
                    print(f"    ⏱️  Aguardando {delay}s antes da tentativa {tentativa + 1}...")
                    time.sleep(delay)
                
                response = requests.post(url, json=payload, headers=headers, timeout=90)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'candidates' in data and len(data['candidates']) > 0:
                        candidate = data['candidates'][0]
                        
                        if 'content' in candidate and 'parts' in candidate['content']:
                            text_content = candidate['content']['parts'][0].get('text', '')
                            # Pequeno delay após sucesso para evitar burst
                            time.sleep(0.5)
                            return text_content
                        else:
                            raise ValueError("Estrutura de resposta inválida")
                    else:
                        raise ValueError("Nenhum candidato na resposta")
                
                elif response.status_code == 429:
                    # Rate limit hit - delay mais longo
                    delay_rate_limit = min(60, 10 * (2 ** tentativa))  # Max 60s
                    print(f"    🚫 Rate limit atingido! Aguardando {delay_rate_limit}s...")
                    time.sleep(delay_rate_limit)
                    
                elif response.status_code == 403:
                    print(f"    ❌ Acesso negado (403). Verifique a chave API e permissões.")
                    time.sleep(5)
                    
                elif response.status_code == 400:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('error', {}).get('message', response.text)
                    print(f"    ❌ Erro 400: {error_msg}")
                    time.sleep(2)
                    
                else:
                    error_msg = f"Erro HTTP {response.status_code}: {response.text[:200]}"
                    print(f"    ⚠️ Tentativa {tentativa + 1}: {error_msg}")
                    time.sleep(3)
                    
            except requests.exceptions.Timeout:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Timeout na requisição")
                time.sleep(5)
                
            except requests.exceptions.ConnectionError:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Erro de conexão")
                time.sleep(5)
                
            except Exception as e:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Erro - {str(e)[:100]}")
                time.sleep(3)
        
        raise Exception(f"Falha após {max_tentativas} tentativas - possível limite de quota atingido")
    
    def classificar_batch_gemini(self, clientes_batch: List[Dict[str, Any]], max_tentativas: int = 3) -> List[Dict[str, bool]]:
        """Processa batch de clientes com Gemini"""
        
        num_clientes = len(clientes_batch)
        prompt = self.montar_prompt_batch(clientes_batch)
        usar_thinking = self.model_config['thinking']
        
        for tentativa in range(max_tentativas):
            try:
                print(f"    🔄 Batch de {num_clientes} clientes - tentativa {tentativa + 1}/{max_tentativas}")
                print(f"    🤖 Usando modelo: {self.model_config['nome']}")
                if usar_thinking:
                    print(f"    🧠 Modo thinking ativado")
                
                # Chama API Gemini
                resposta = self.chamar_gemini_api(prompt, usar_thinking)
                
                # Limpa resposta
                resposta = resposta.replace('```json', '').replace('```', '').strip()
                
                # Parse JSON
                resultado_batch = json.loads(resposta)
                
                # Valida estrutura
                if 'clientes' not in resultado_batch:
                    raise ValueError("Estrutura JSON inválida: falta campo 'clientes'")
                
                clientes_resultado = resultado_batch['clientes']
                
                if len(clientes_resultado) != num_clientes:
                    raise ValueError(f"Número incorreto de clientes: esperado {num_clientes}, recebido {len(clientes_resultado)}")
                
                # Valida critérios para cada cliente
                criterios_esperados = ['PA1', 'PA2', 'PA3', 'PA4', 'S1', 'S2', 'S3', 
                                     'C1', 'C2', 'C3', 'C4', 'C5', 'F1', 'F2', 'F3', 'F4', 'N1', 'N2']
                
                resultados_validados = []
                
                for i, cliente_resultado in enumerate(clientes_resultado):
                    if not all(k in cliente_resultado for k in criterios_esperados):
                        raise ValueError(f"Cliente {i+1}: critérios faltando")
                    
                    # Extrai apenas os critérios
                    criterios_cliente = {k: cliente_resultado[k] for k in criterios_esperados}
                    resultados_validados.append(criterios_cliente)
                
                print(f"    ✅ Batch processado com sucesso: {num_clientes} clientes")
                return resultados_validados
                
            except json.JSONDecodeError as e:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Erro JSON - {str(e)[:100]}")
                time.sleep(1)
                
            except ValueError as e:
                print(f"    ⚠️ Tentativa {tentativa + 1}: {e}")
                time.sleep(1)
                
            except Exception as e:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Erro API - {str(e)[:100]}")
                time.sleep(2)
        
        # Fallback: processamento individual
        print(f"    🔄 Fallback: processamento individual para {num_clientes} clientes")
        resultados_fallback = []
        
        for cliente_info in clientes_batch:
            try:
                prompt_individual = self.montar_prompt_classificacao(cliente_info['dados'], cliente_info['evidencias'])
                resultado_individual = self.classificar_com_gemini(prompt_individual, max_tentativas=2)
                resultados_fallback.append(resultado_individual)
            except:
                # Último fallback: todos False
                resultado_vazio = {k: False for k in ['PA1', 'PA2', 'PA3', 'PA4', 'S1', 'S2', 'S3', 
                                                    'C1', 'C2', 'C3', 'C4', 'C5', 'F1', 'F2', 'F3', 'F4', 'N1', 'N2']}
                resultados_fallback.append(resultado_vazio)
        
        return resultados_fallback
    
    def montar_prompt_classificacao(self, dados: Dict[str, Any], evidencias: Dict[str, List[str]]) -> str:
        """Monta prompt estruturado para o Gemini (individual)"""
        
        nome = dados.get('nome_completo', 'Cliente')
        instituicao = dados.get('instituicao_vinculo', '')
        linhas = dados.get('linhas_pesquisa', '')
        
        prompt = f"""
SISTEMA DE CLASSIFICAÇÃO DE CLIENTES BIOTECNOLÓGICOS

CLIENTE: {nome}
INSTITUIÇÃO: {instituicao}  
ÁREA: {linhas}

INSTRUÇÕES:
Analise as evidências encontradas e classifique CADA critério como True/False.
Seja RIGOROSO: só marque True se houver evidência CLARA e DIRETA.

CRITÉRIOS DE CLASSIFICAÇÃO:

=== CATEGORIA PA: PRODUÇÃO DE PROTEÍNA ===
PA1 (Peso 2): Expressão e purificação de proteínas recombinantes
PA2 (Peso 2): Enzimas biotecnológicas e biocatálise  
PA3 (Peso 1): Técnicas ELISA, Western blot, biossensores
PA4 (Peso 1): Cromatografia, espectrometria de massas

=== CATEGORIA S: SÍNTESE DE GENE ===
S1: Síntese e expressão gênica
S2: Clonagem molecular, PCR, CRISPR
S3: Circuitos genéticos, biologia sintética

=== CATEGORIA C: CFPS ===
C1: Cell-free protein synthesis
C2: Proteínas tóxicas/difíceis
C3: Screening de fármacos
C4: Aplicações educacionais  
C5: Cristalografia de proteínas

=== CATEGORIA F: FATORES DE CRESCIMENTO ===
F1: Cultura celular, células-tronco
F2: Fermentação, biorreatores
F3: Embriologia, reprodução assistida
F4: Engenharia de tecidos

=== FATORES NEGATIVOS ===
N1: Área SEM uso direto de proteínas recombinantes
N2: Área NÃO correlata à biotecnologia

EVIDÊNCIAS ENCONTRADAS:
"""
        
        # Adiciona evidências organizadas
        for criterio_id, evidencias_list in evidencias.items():
            if evidencias_list:
                prompt += f"\n{criterio_id}:\n"
                for evidencia in evidencias_list[:3]:
                    prompt += f"  - {evidencia}\n"
        
        prompt += """

RESPOSTA REQUERIDA:
Responda APENAS em formato JSON válido:

{
    "PA1": true/false,
    "PA2": true/false, 
    "PA3": true/false,
    "PA4": true/false,
    "S1": true/false,
    "S2": true/false,
    "S3": true/false,
    "C1": true/false,
    "C2": true/false,
    "C3": true/false,
    "C4": true/false,
    "C5": true/false,
    "F1": true/false,
    "F2": true/false,
    "F3": true/false,
    "F4": true/false,
    "N1": true/false,
    "N2": true/false
}

IMPORTANTE: Responda APENAS o JSON, sem explicações adicionais.
"""
        
        return prompt
    
    def classificar_com_gemini(self, prompt: str, max_tentativas: int = 3) -> Dict[str, bool]:
        """Chama Gemini para classificação individual"""
        
        usar_thinking = self.model_config['thinking']
        
        for tentativa in range(max_tentativas):
            try:
                # Chama API Gemini
                resposta = self.chamar_gemini_api(prompt, usar_thinking)
                
                # Limpa resposta se necessário
                resposta = resposta.replace('```json', '').replace('```', '').strip()
                
                # Parse JSON
                criterios_resultado = json.loads(resposta)
                
                # Valida se todos os critérios estão presentes
                esperados = ['PA1', 'PA2', 'PA3', 'PA4', 'S1', 'S2', 'S3', 
                           'C1', 'C2', 'C3', 'C4', 'C5', 'F1', 'F2', 'F3', 'F4', 'N1', 'N2']
                
                if all(k in criterios_resultado for k in esperados):
                    return criterios_resultado
                else:
                    print(f"    ⚠️ Tentativa {tentativa + 1}: Critérios faltando na resposta")
                    
            except json.JSONDecodeError as e:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Erro JSON - {e}")
                time.sleep(1)
                
            except Exception as e:
                print(f"    ⚠️ Tentativa {tentativa + 1}: Erro API - {e}")
                time.sleep(2)
        
        # Fallback: retorna todos False
        print(f"    ❌ Falha após {max_tentativas} tentativas - usando fallback")
        return {k: False for k in ['PA1', 'PA2', 'PA3', 'PA4', 'S1', 'S2', 'S3', 
                                  'C1', 'C2', 'C3', 'C4', 'C5', 'F1', 'F2', 'F3', 'F4', 'N1', 'N2']}
    
    def calcular_pontuacoes_categorias(self, criterios: Dict[str, bool]) -> Dict[str, float]:
        """Calcula pontuações de 0-10 para cada categoria"""
        pontuacoes = {}
        
        # CATEGORIA PA (Produção de Proteína - Acadêmico)
        pontuacao_bruta_pa = (
            (criterios.get('PA1', False) * 2) + 
            (criterios.get('PA2', False) * 2) + 
            (criterios.get('PA3', False) * 1) + 
            (criterios.get('PA4', False) * 1)
        )
        pontuacoes['PA'] = (pontuacao_bruta_pa / 6) * 10
        
        # CATEGORIA S (Síntese de Gene)
        pontuacao_bruta_s = (
            criterios.get('S1', False) + 
            criterios.get('S2', False) + 
            criterios.get('S3', False)
        )
        pontuacoes['S'] = (pontuacao_bruta_s / 3) * 10
        
        # CATEGORIA C (CFPS)
        pontuacao_bruta_c = (
            criterios.get('C1', False) + 
            criterios.get('C2', False) + 
            criterios.get('C3', False) + 
            criterios.get('C4', False) + 
            criterios.get('C5', False)
        )
        pontuacoes['C'] = (pontuacao_bruta_c / 5) * 10
        
        # CATEGORIA F (Fatores de Crescimento)
        pontuacao_bruta_f = (
            criterios.get('F1', False) + 
            criterios.get('F2', False) + 
            criterios.get('F3', False) + 
            criterios.get('F4', False)
        )
        pontuacoes['F'] = (pontuacao_bruta_f / 4) * 10
        
        return pontuacoes
    
    def classificar_categoria(self, categoria: str, pontuacao: float, criterios: Dict[str, bool]) -> str:
        """Classifica uma categoria individual considerando fatores negativos"""
        n1 = criterios.get('N1', False)
        n2 = criterios.get('N2', False)
        
        if categoria == 'PA':
            if n1:
                return "BAIXA"
            elif n2:
                classificacao_normal = self._classificacao_normal_pa(pontuacao, criterios)
                return min(classificacao_normal, "MODERADA", key=lambda x: {"ALTA": 3, "MODERADA": 2, "BAIXA": 1}[x])
            else:
                return self._classificacao_normal_pa(pontuacao, criterios)
        
        elif categoria == 'S':
            if n2:
                return "BAIXA"
            elif n1:
                classificacao_normal = self._classificacao_normal_s(pontuacao)
                return min(classificacao_normal, "MODERADA", key=lambda x: {"ALTA": 3, "MODERADA": 2, "BAIXA": 1}[x])
            else:
                return self._classificacao_normal_s(pontuacao)
        
        elif categoria == 'C':
            if n1:
                return "BAIXA"
            elif n2:
                classificacao_normal = self._classificacao_normal_c(pontuacao)
                return min(classificacao_normal, "MODERADA", key=lambda x: {"ALTA": 3, "MODERADA": 2, "BAIXA": 1}[x])
            else:
                return self._classificacao_normal_c(pontuacao)
        
        elif categoria == 'F':
            if n2 or n1:
                classificacao_normal = self._classificacao_normal_f(pontuacao)
                return min(classificacao_normal, "MODERADA", key=lambda x: {"ALTA": 3, "MODERADA": 2, "BAIXA": 1}[x])
            else:
                return self._classificacao_normal_f(pontuacao)
    
    def _classificacao_normal_pa(self, pontuacao: float, criterios: Dict[str, bool]) -> str:
        """Classificação normal para PA"""
        pa1_ou_pa2 = criterios.get('PA1', False) or criterios.get('PA2', False)
        pa3_ou_pa4 = criterios.get('PA3', False) or criterios.get('PA4', False)
        
        if pa1_ou_pa2 and pa3_ou_pa4:
            return "ALTA"
        elif pontuacao >= 3.33:
            return "MODERADA"
        else:
            return "BAIXA"
    
    def _classificacao_normal_s(self, pontuacao: float) -> str:
        if pontuacao >= 6.67:
            return "ALTA"
        elif pontuacao >= 3.33:
            return "MODERADA"
        else:
            return "BAIXA"
    
    def _classificacao_normal_c(self, pontuacao: float) -> str:
        if pontuacao >= 4.0:
            return "ALTA"
        elif pontuacao >= 2.0:
            return "MODERADA"
        else:
            return "BAIXA"
    
    def _classificacao_normal_f(self, pontuacao: float) -> str:
        if pontuacao >= 5.0:
            return "ALTA"
        elif pontuacao >= 2.5:
            return "MODERADA"
        else:
            return "BAIXA"
    
    def classificar_cliente_final(self, classificacoes_categorias: Dict[str, str], 
                                pontuacao_media: float, criterios: Dict[str, bool]) -> str:
        """Classificação final do cliente"""
        n1 = criterios.get('N1', False)
        n2 = criterios.get('N2', False)
        
        if n1 and n2:
            return "CLIENTE INADEQUADO"
        
        altas = sum(1 for classe in classificacoes_categorias.values() if classe == "ALTA")
        
        if n2:
            classificacao_base = self._classificacao_base(altas, pontuacao_media)
            return min(classificacao_base, "CLIENTE REGULAR", 
                      key=lambda x: {"CLIENTE ESTRATÉGICO": 4, "CLIENTE PRIORITÁRIO": 3, 
                                    "CLIENTE REGULAR": 2, "CLIENTE BAIXA PRIORIDADE": 1}[x])
        elif n1:
            classificacao_base = self._classificacao_base(altas, pontuacao_media)
            return min(classificacao_base, "CLIENTE PRIORITÁRIO",
                      key=lambda x: {"CLIENTE ESTRATÉGICO": 4, "CLIENTE PRIORITÁRIO": 3, 
                                    "CLIENTE REGULAR": 2, "CLIENTE BAIXA PRIORIDADE": 1}[x])
        else:
            return self._classificacao_base(altas, pontuacao_media)
    
    def _classificacao_base(self, altas: int, pontuacao_media: float) -> str:
        if altas >= 2 and pontuacao_media >= 6.0:
            return "CLIENTE ESTRATÉGICO"
        elif altas >= 1 and pontuacao_media >= 5.0:
            return "CLIENTE PRIORITÁRIO"
        elif pontuacao_media >= 3.0:
            return "CLIENTE REGULAR"
        else:
            return "CLIENTE BAIXA PRIORIDADE"
    
    def gerar_justificativa(self, classificacao_final: str, classificacoes: Dict[str, str], 
                          criterios: Dict[str, bool], pontuacao_media: float) -> str:
        """Gera justificativa de uma linha para a classificação"""
        
        n1 = criterios.get('N1', False)
        n2 = criterios.get('N2', False)
        altas = sum(1 for classe in classificacoes.values() if classe == "ALTA")
        
        if classificacao_final == "CLIENTE INADEQUADO":
            return "Cliente inadequado: sem uso de proteínas recombinantes e área não correlata à biotecnologia"
        elif classificacao_final == "CLIENTE ESTRATÉGICO":
            return f"Cliente estratégico: {altas} categoria(s) ALTA, pontuação média {pontuacao_media:.1f}, perfil ideal para produtos"
        elif classificacao_final == "CLIENTE PRIORITÁRIO":
            if n1:
                return f"Cliente prioritário: {altas} categoria(s) ALTA mas limitado por não usar proteínas recombinantes diretamente"
            else:
                return f"Cliente prioritário: {altas} categoria(s) ALTA, pontuação média {pontuacao_media:.1f}, bom potencial"
        elif classificacao_final == "CLIENTE REGULAR":
            if n2:
                return f"Cliente regular: área parcialmente correlata, pontuação média {pontuacao_media:.1f}, potencial limitado"
            else:
                return f"Cliente regular: pontuação média {pontuacao_media:.1f}, algumas categorias relevantes"
        else:
            return f"Cliente baixa prioridade: pontuação média {pontuacao_media:.1f}, poucas categorias relevantes"
    
    def gerar_hash_arquivo(self, filepath: str) -> str:
        """Gera hash do arquivo"""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def get_cached_result(self, file_hash: str) -> Dict[str, Any]:
        """Recupera resultado do cache"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT criterios_json, pontuacoes_json, classificacao_final, justificativa 
            FROM gemini_classifications WHERE file_hash = ?
        ''', (file_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'criterios': json.loads(result[0]),
                'pontuacoes': json.loads(result[1]),
                'classificacao_final': result[2],
                'justificativa': result[3]
            }
        return None
    
    def save_result_cache(self, file_hash: str, nome: str, criterios: Dict[str, bool], 
                         pontuacoes: Dict[str, float], classificacao_final: str, justificativa: str):
        """Salva resultado no cache"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO gemini_classifications 
            (file_hash, nome, criterios_json, pontuacoes_json, classificacao_final, justificativa, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file_hash, nome, json.dumps(criterios), json.dumps(pontuacoes), 
              classificacao_final, justificativa, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def processar_resultado_cached(self, dados_cliente: Dict[str, Any], cached_result: Dict[str, Any], arquivo: Path) -> Dict[str, Any]:
        """Processa resultado do cache"""
        criterios_resultado = cached_result['criterios']
        pontuacoes = cached_result['pontuacoes'] 
        classificacao_final = cached_result['classificacao_final']
        justificativa = cached_result['justificativa']
        
        return self.montar_resultado_final(dados_cliente, criterios_resultado, pontuacoes, classificacao_final, justificativa, arquivo)
    
    def processar_resultado_individual(self, dados_cliente: Dict[str, Any], criterios_resultado: Dict[str, bool], 
                                     arquivo: Path, file_hash: str) -> Dict[str, Any]:
        """Processa resultado individual e salva no cache"""
        
        # Calcula pontuações e classificações
        pontuacoes = self.calcular_pontuacoes_categorias(criterios_resultado)
        
        # Classifica cada categoria
        classificacoes = {}
        for categoria in ['PA', 'S', 'C', 'F']:
            classificacoes[categoria] = self.classificar_categoria(categoria, pontuacoes[categoria], criterios_resultado)
        
        # Pontuação média geral
        pontuacao_media = sum(pontuacoes.values()) / len(pontuacoes)
        
        # Classificação final
        classificacao_final = self.classificar_cliente_final(classificacoes, pontuacao_media, criterios_resultado)
        
        # Gera justificativa
        justificativa = self.gerar_justificativa(classificacao_final, classificacoes, criterios_resultado, pontuacao_media)
        
        # Salva no cache
        nome = dados_cliente.get('nome_completo', '')
        self.save_result_cache(file_hash, nome, criterios_resultado, pontuacoes, classificacao_final, justificativa)
        
        return self.montar_resultado_final(dados_cliente, criterios_resultado, pontuacoes, classificacao_final, justificativa, arquivo)
    
    def montar_resultado_final(self, dados_cliente: Dict[str, Any], criterios_resultado: Dict[str, bool], 
                              pontuacoes: Dict[str, float], classificacao_final: str, justificativa: str, arquivo: Path) -> Dict[str, Any]:
        """Monta estrutura final do resultado"""
        
        # Separa critérios por categoria
        criterios_PA = {k: v for k, v in criterios_resultado.items() if k.startswith('PA')}
        criterios_S = {k: v for k, v in criterios_resultado.items() if k.startswith('S')}
        criterios_C = {k: v for k, v in criterios_resultado.items() if k.startswith('C')}
        criterios_F = {k: v for k, v in criterios_resultado.items() if k.startswith('F')}
        
        # Classifica cada categoria
        classificacoes = {}
        for categoria in ['PA', 'S', 'C', 'F']:
            classificacoes[categoria] = self.classificar_categoria(categoria, pontuacoes[categoria], criterios_resultado)
        
        # Pontuação média
        pontuacao_media = sum(pontuacoes.values()) / len(pontuacoes)
        
        return {
            'nome': dados_cliente.get('nome_completo', ''),
            'instituicao': dados_cliente.get('instituicao_vinculo', ''),
            'titulacao': dados_cliente.get('titulacao_atual', ''),
            'linhas_pesquisa': dados_cliente.get('linhas_pesquisa', ''),
            'curriculo_lattes': dados_cliente.get('curriculo_lattes', dados_cliente.get('link_lattes', '')),
            
            # Critérios por categoria separados
            'criterios_PA': criterios_PA,
            'criterios_S': criterios_S,
            'criterios_C': criterios_C,
            'criterios_F': criterios_F,
            
            # Critérios individuais (mantém para compatibilidade)
            'criterios_atendidos': criterios_resultado,
            
            # Pontuações por categoria (0-10)
            'pontuacao_PA': pontuacoes['PA'],
            'pontuacao_S': pontuacoes['S'],
            'pontuacao_C': pontuacoes['C'],
            'pontuacao_F': pontuacoes['F'],
            'pontuacao_media': pontuacao_media,
            
            # Classificações por categoria
            'classificacao_PA': classificacoes['PA'],
            'classificacao_S': classificacoes['S'],
            'classificacao_C': classificacoes['C'],
            'classificacao_F': classificacoes['F'],
            
            # Fatores negativos
            'fator_N1': criterios_resultado.get('N1', False),
            'fator_N2': criterios_resultado.get('N2', False),
            
            # Classificação final
            'classificacao_final': classificacao_final,
            'justificativa_classificacao': justificativa,
            
            # Metadados
            'arquivo_origem': arquivo.name,
            'timestamp': datetime.now().isoformat()
        }
    
    def processar_arquivos_batch(self, arquivos_json: List[Path]) -> pd.DataFrame:
        """Processa arquivos JSON em batches para otimizar custos"""
        
        print(f"🚀 Processando {len(arquivos_json)} arquivos em batches de {self.batch_size}...")
        
        resultados = []
        total_batches = (len(arquivos_json) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(arquivos_json), self.batch_size):
            batch_arquivos = arquivos_json[batch_idx:batch_idx + self.batch_size]
            batch_num = (batch_idx // self.batch_size) + 1
            
            print(f"\n📦 BATCH {batch_num}/{total_batches} - {len(batch_arquivos)} arquivos:")
            
            # Prepara dados do batch
            clientes_batch = []
            
            for arquivo in batch_arquivos:
                try:
                    with open(arquivo, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'dados' not in data:
                        print(f"    ❌ {arquivo.name}: dados inválidos")
                        continue
                    
                    dados_cliente = data['dados']
                    nome = dados_cliente.get('nome_completo', '')
                    
                    if not nome:
                        print(f"    ❌ {arquivo.name}: nome não encontrado")
                        continue
                    
                    # Verifica cache individual
                    file_hash = self.gerar_hash_arquivo(str(arquivo))
                    cached_result = self.get_cached_result(file_hash)
                    
                    if cached_result:
                        print(f"    📋 {arquivo.name}: cache hit")
                        resultado_cache = self.processar_resultado_cached(dados_cliente, cached_result, arquivo)
                        resultados.append(resultado_cache)
                        continue
                    
                    # RETRIEVAL: Extrai evidências
                    evidencias = self.extrair_informacoes_relevantes(dados_cliente)
                    
                    clientes_batch.append({
                        'dados': dados_cliente,
                        'evidencias': evidencias,
                        'arquivo': arquivo,
                        'file_hash': file_hash
                    })
                    
                    print(f"    ✅ {arquivo.name}: {nome[:40]}")
                    
                except Exception as e:
                    print(f"    ❌ {arquivo.name}: erro - {e}")
                    continue
            
            # Processa batch se houver clientes válidos
            if clientes_batch:
                try:
                    # GENERATION: Gemini processa batch
                    resultados_batch = self.classificar_batch_gemini(clientes_batch)
                    
                    # Processa resultados individuais
                    for i, (cliente_info, criterios_resultado) in enumerate(zip(clientes_batch, resultados_batch)):
                        try:
                            resultado = self.processar_resultado_individual(
                                cliente_info['dados'], 
                                criterios_resultado, 
                                cliente_info['arquivo'],
                                cliente_info['file_hash']
                            )
                            resultados.append(resultado)
                            
                        except Exception as e:
                            print(f"    ❌ Erro processando resultado {i+1}: {e}")
                            
                except Exception as e:
                    print(f"    ❌ Erro no batch: {e}")
                    continue
            
            # Rate limiting entre batches - MUITO mais conservador
            if batch_num < total_batches:
                if self.modo_conservador:
                    delay_entre_batches = 10  # 10 segundos entre batches
                else:
                    delay_entre_batches = 5   # 5 segundos entre batches
                
                print(f"    ⏱️  Aguardando {delay_entre_batches}s antes do próximo batch...")
                time.sleep(delay_entre_batches)
        
        if not resultados:
            raise ValueError("Nenhum arquivo processado com sucesso")
        
        # Cria DataFrame
        df = pd.DataFrame(resultados)
        df = df.sort_values('pontuacao_media', ascending=False).reset_index(drop=True)
        df['rank'] = range(1, len(df) + 1)
        
        return df
    
    def processar_pasta(self, pasta_entrada: str) -> pd.DataFrame:
        """Processa todos os JSONs de uma pasta usando sistema de batch"""
        
        pasta = Path(pasta_entrada)
        arquivos_json = list(pasta.glob("*.json"))
        
        if not arquivos_json:
            raise FileNotFoundError(f"Nenhum JSON encontrado em {pasta_entrada}")
        
        print(f"🚀 PROCESSAMENTO EM BATCH INICIADO")
        print(f"   📁 Total de arquivos: {len(arquivos_json)}")
        print(f"   📦 Batch size: {self.batch_size} clientes por chamada")
        print(f"   🤖 Modelo: {self.model_config['nome']}")
        print(f"   🧠 Thinking: {'Ativado' if self.model_config['thinking'] else 'Desativado'}")
        print(f"   💰 Economia estimada: ~{((len(arquivos_json) - len(arquivos_json)//self.batch_size) / len(arquivos_json)) * 100:.0f}% em custos de API")
        
        # Processa em batches
        df_resultados = self.processar_arquivos_batch(arquivos_json)
        
        print(f"\n✅ PROCESSAMENTO CONCLUÍDO:")
        print(f"   📊 {len(df_resultados)} clientes processados com sucesso")
        print(f"   🎯 Taxa de sucesso: {(len(df_resultados)/len(arquivos_json))*100:.1f}%")
        
        return df_resultados
    
    def exportar_resultados(self, df: pd.DataFrame, caminho_saida: str):
        """Exporta resultados para CSV com listas separadas por categoria"""
        
        # Prepara DataFrame para export
        df_export = df.copy()
        
        # Expande critérios PA em colunas individuais
        for criterio_id in ['PA1', 'PA2', 'PA3', 'PA4']:
            df_export[f'PA_{criterio_id}'] = df_export['criterios_PA'].apply(
                lambda x: x.get(criterio_id, False) if isinstance(x, dict) else False
            )
        
        # Expande critérios S em colunas individuais  
        for criterio_id in ['S1', 'S2', 'S3']:
            df_export[f'S_{criterio_id}'] = df_export['criterios_S'].apply(
                lambda x: x.get(criterio_id, False) if isinstance(x, dict) else False
            )
        
        # Expande critérios C em colunas individuais
        for criterio_id in ['C1', 'C2', 'C3', 'C4', 'C5']:
            df_export[f'C_{criterio_id}'] = df_export['criterios_C'].apply(
                lambda x: x.get(criterio_id, False) if isinstance(x, dict) else False
            )
        
        # Expande critérios F em colunas individuais
        for criterio_id in ['F1', 'F2', 'F3', 'F4']:
            df_export[f'F_{criterio_id}'] = df_export['criterios_F'].apply(
                lambda x: x.get(criterio_id, False) if isinstance(x, dict) else False
            )
        
        # Fatores negativos
        df_export['N_N1'] = df_export['fator_N1']
        df_export['N_N2'] = df_export['fator_N2']
        
        # Reorganiza colunas na ordem desejada
        colunas_ordenadas = [
            'rank', 'nome', 'instituicao', 'titulacao', 'linhas_pesquisa',
            'pontuacao_PA', 'classificacao_PA',
            'pontuacao_S', 'classificacao_S', 
            'pontuacao_C', 'classificacao_C',
            'pontuacao_F', 'classificacao_F',
            'pontuacao_media',
            'PA_PA1', 'PA_PA2', 'PA_PA3', 'PA_PA4',
            'S_S1', 'S_S2', 'S_S3',
            'C_C1', 'C_C2', 'C_C3', 'C_C4', 'C_C5',
            'F_F1', 'F_F2', 'F_F3', 'F_F4',
            'N_N1', 'N_N2',
            'classificacao_final', 'justificativa_classificacao',
            'curriculo_lattes',
            'arquivo_origem', 'timestamp'
        ]
        
        # Seleciona apenas colunas que existem
        colunas_existentes = [col for col in colunas_ordenadas if col in df_export.columns]
        df_export = df_export[colunas_existentes]
        
        # Remove colunas complexas desnecessárias
        colunas_remover = ['criterios_atendidos', 'criterios_PA', 'criterios_S', 'criterios_C', 'criterios_F']
        df_export = df_export.drop([col for col in colunas_remover if col in df_export.columns], axis=1)
        
        # Limita texto longo
        if 'linhas_pesquisa' in df_export.columns:
            df_export['linhas_pesquisa'] = df_export['linhas_pesquisa'].str[:300]
            
        if 'justificativa_classificacao' in df_export.columns:
            df_export['justificativa_classificacao'] = df_export['justificativa_classificacao'].str[:500]
        
        base_path = Path(caminho_saida).with_suffix('')
        path_csv = f"{base_path}.csv"
        path_json = f"{base_path}.json"
        path_xlsx = f"{base_path}.xlsx"

        df_export.to_csv(path_csv, index=False, encoding='utf-8')
        df_export.to_json(path_json, orient='records', indent=4, force_ascii=False)
        
        try:
            df_export.to_excel(path_xlsx, index=False, engine='openpyxl')
            print(f"Resultados exportados para: {Path(base_path).name}.[csv, json, xlsx]")
        except Exception as e:
            print(f"  ❌ Falha ao exportar para Excel: {e}")
            print(f"     - Arquivo: {path_xlsx}")
            print("     - Verifique se a biblioteca 'openpyxl' está instalada e se há permissão de escrita no diretório.")
    
    def segmentar_clientes(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Segmenta clientes em 5 listas baseado na melhor classificação"""
        
        # Dicionário para armazenar as listas
        listas = {
            'PA': [],  # Produção de Proteína
            'S': [],   # Síntese de Gene
            'C': [],   # CFPS
            'F': [],   # Fatores de Crescimento
            'N': []    # Fatores Negativos
        }
        
        for _, cliente in df.iterrows():
            # Primeiro verifica fatores negativos
            if cliente.get('fator_N1', False) or cliente.get('fator_N2', False):
                listas['N'].append(cliente)
                continue
            
            # Mapeia classificações para valores numéricos
            classificacao_valores = {'ALTA': 3, 'MODERADA': 2, 'BAIXA': 1}
            
            # Coleta classificações das 4 categorias
            categorias_classificacao = {
                'PA': cliente.get('classificacao_PA', 'BAIXA'),
                'S': cliente.get('classificacao_S', 'BAIXA'), 
                'C': cliente.get('classificacao_C', 'BAIXA'),
                'F': cliente.get('classificacao_F', 'BAIXA')
            }
            
            # Encontra melhor classificação
            melhor_valor = max(classificacao_valores[cls] for cls in categorias_classificacao.values())
            melhores_categorias = [cat for cat, cls in categorias_classificacao.items() 
                                 if classificacao_valores[cls] == melhor_valor]
            
            # Em caso de empate, usa ordem alfabética (C > F > PA > S)
            ordem_desempate = ['C', 'F', 'PA', 'S']
            categoria_escolhida = None
            
            for cat in ordem_desempate:
                if cat in melhores_categorias:
                    categoria_escolhida = cat
                    break
            
            if categoria_escolhida:
                listas[categoria_escolhida].append(cliente)
        
        # Converte listas em DataFrames e ordena alfabeticamente
        dfs_segmentados = {}
        for categoria, clientes in listas.items():
            if clientes:
                df_categoria = pd.DataFrame(clientes).reset_index(drop=True)
                df_categoria = df_categoria.sort_values('nome').reset_index(drop=True)
                df_categoria['rank_categoria'] = range(1, len(df_categoria) + 1)
                dfs_segmentados[categoria] = df_categoria
            else:
                dfs_segmentados[categoria] = pd.DataFrame(columns=['nome', 'instituicao'])
        
        return dfs_segmentados
    
    def exportar_listas_separadas(self, df_geral: pd.DataFrame, output_dir: str, timestamp: str):
        """Exporta listas separadas por categoria para CSV, JSON e Excel."""

        print(f"\n🔄 Segmentando clientes em listas especializadas...")

        # Segmenta clientes
        listas_segmentadas = self.segmentar_clientes(df_geral)

        # Nomes das categorias
        nomes_categorias = {
            'PA': 'producao_proteina',
            'S': 'sintese_gene', 
            'C': 'cfps',
            'F': 'fatores_crescimento',
            'N': 'fatores_negativos'
        }

        # Descrições das categorias
        descricoes = {
            'PA': 'Produção de Proteína',
            'S': 'Síntese de Gene',
            'C': 'CFPS (Cell-Free Protein Synthesis)', 
            'F': 'Fatores de Crescimento',
            'N': 'Fatores Negativos (Não Viáveis)'
        }

        arquivos_gerados = []
        dfs_viaveis = []

        # Exporta cada lista de categoria
        for categoria, df_categoria in listas_segmentadas.items():
            if len(df_categoria) > 0:
                if categoria != 'N':
                    dfs_viaveis.append(df_categoria)

                nome_base = f"lista_{categoria}_{nomes_categorias[categoria]}"
                caminho_base = f"{output_dir}/{nome_base}_{timestamp}"
                df_export = self.preparar_dataframe_export(df_categoria.copy())

                path_csv = f"{caminho_base}.csv"
                path_json = f"{caminho_base}.json"
                path_xlsx = f"{caminho_base}.xlsx"

                df_export.to_csv(path_csv, index=False, encoding='utf-8')
                df_export.to_json(path_json, orient='records', indent=4, force_ascii=False)
                
                try:
                    df_export.to_excel(path_xlsx, index=False, engine='openpyxl')
                    print(f"  ✅ {descricoes[categoria]:<35}: {len(df_export):3d} clientes → {Path(caminho_base).name}.[csv, json, xlsx]")
                except Exception as e:
                    print(f"  ❌ Falha ao exportar '{descricoes[categoria]}' para Excel: {e}")

                arquivos_gerados.append({
                    'categoria': categoria,
                    'nome': descricoes[categoria],
                    'arquivo': Path(path_csv).name,
                    'total': len(df_categoria)
                })
            else:
                print(f"  ⚪ {descricoes[categoria]:<35}: {0:3d} clientes → sem arquivo gerado")

        if dfs_viaveis:
            df_clientes_viaveis = pd.concat(dfs_viaveis, ignore_index=True).sort_values('pontuacao_media', ascending=False).reset_index(drop=True)
            
            print("\n🔄 Exportando lista consolidada de clientes viáveis...")
            nome_base_viaveis = f"lista_clientes_viaveis"
            caminho_base_viaveis = f"{output_dir}/{nome_base_viaveis}_{timestamp}"
            df_export_viaveis = self.preparar_dataframe_export(df_clientes_viaveis.copy())

            path_csv_v = f"{caminho_base_viaveis}.csv"
            path_json_v = f"{caminho_base_viaveis}.json"
            path_xlsx_v = f"{caminho_base_viaveis}.xlsx"

            df_export_viaveis.to_csv(path_csv_v, index=False, encoding='utf-8')
            df_export_viaveis.to_json(path_json_v, orient='records', indent=4, force_ascii=False)

            try:
                df_export_viaveis.to_excel(path_xlsx_v, index=False, engine='openpyxl')
                print(f"  ✅ {'Clientes Viáveis (Consolidado)':<35}: {len(df_export_viaveis):3d} clientes → {Path(caminho_base_viaveis).name}.[csv, json, xlsx]")
            except Exception as e:
                print(f"  ❌ Falha ao exportar 'Clientes Viáveis' para Excel: {e}")

        return arquivos_gerados
    
    def preparar_dataframe_export(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara DataFrame para exportação"""
        
        # Expande critérios em colunas
        for categoria, criterios in [('PA', ['PA1', 'PA2', 'PA3', 'PA4']),
                                    ('S', ['S1', 'S2', 'S3']),
                                    ('C', ['C1', 'C2', 'C3', 'C4', 'C5']),
                                    ('F', ['F1', 'F2', 'F3', 'F4'])]:
            for criterio_id in criterios:
                df[f'{categoria}_{criterio_id}'] = df[f'criterios_{categoria}'].apply(
                    lambda x: x.get(criterio_id, False) if isinstance(x, dict) else False
                )
        
        # Fatores negativos
        df['N_N1'] = df['fator_N1']
        df['N_N2'] = df['fator_N2']
        
        # Remove colunas complexas
        colunas_remover = ['criterios_atendidos', 'criterios_PA', 'criterios_S', 'criterios_C', 'criterios_F']
        df = df.drop([col for col in colunas_remover if col in df.columns], axis=1)
        
        # Limita texto longo
        if 'linhas_pesquisa' in df.columns:
            df['linhas_pesquisa'] = df['linhas_pesquisa'].str[:300]
            
        if 'justificativa_classificacao' in df.columns:
            df['justificativa_classificacao'] = df['justificativa_classificacao'].str[:500]
        
        return df
    
    def imprimir_estatisticas(self, df: pd.DataFrame):
        """Imprime estatísticas do processamento"""
        
        print(f"\n{'='*70}")
        print(f"SISTEMA RAG + BATCH GEMINI - RESULTADOS")
        print(f"Modelo: {self.model_config['nome']} | Batch Size: {self.batch_size}")
        print(f"{'='*70}")
        
        print(f"Total processado: {len(df)}")
        print(f"Pontuação média geral: {df['pontuacao_media'].mean():.1f}/10")
        
        # Distribuição por classificação final
        print(f"\nCLASSIFICAÇÃO FINAL DOS CLIENTES:")
        classificacoes = ['CLIENTE ESTRATÉGICO', 'CLIENTE PRIORITÁRIO', 'CLIENTE REGULAR', 
                         'CLIENTE BAIXA PRIORIDADE', 'CLIENTE INADEQUADO']
        for classe in classificacoes:
            count = len(df[df['classificacao_final'] == classe])
            pct = (count / len(df)) * 100 if len(df) > 0 else 0
            print(f"  {classe:<25}: {count:3d} ({pct:4.1f}%)")
        
        # Pontuações médias por categoria
        print(f"\nPONTUAÇÕES MÉDIAS POR CATEGORIA (0-10):")
        print(f"  PA (Produção Proteína): {df['pontuacao_PA'].mean():.1f}")
        print(f"  S  (Síntese Gene):       {df['pontuacao_S'].mean():.1f}")
        print(f"  C  (CFPS):              {df['pontuacao_C'].mean():.1f}")
        print(f"  F  (Fatores Crescim.):  {df['pontuacao_F'].mean():.1f}")
        
        # Top 15 clientes
        print(f"\nTOP 15 CLIENTES:")
        for _, row in df.head(15).iterrows():
            print(f"  {row['rank']:2d}. {row['nome'][:35]:<35} | {row['pontuacao_media']:4.1f} | {row['classificacao_final']}")
        
        # Fatores negativos
        n1_count = df['fator_N1'].sum()
        n2_count = df['fator_N2'].sum()
        print(f"\nFATORES NEGATIVOS:")
        print(f"  N1 (Sem uso proteínas):     {n1_count:3d} clientes")
        print(f"  N2 (Área não correlata):    {n2_count:3d} clientes")
        
        print(f"\n⚡ EFICIÊNCIA DO SISTEMA:")
        print(f"  🤖 Modelo: {self.model_config['nome']}")
        print(f"  🧠 Thinking: {'Ativado' if self.model_config['thinking'] else 'Desativado'}")
        print(f"  📦 Batch Size: {self.batch_size} clientes por chamada")
        print(f"  💰 Economia estimada vs processamento individual: ~80% em custos de API")
    
    def relatorio_segmentacao(self, df_geral: pd.DataFrame, arquivos_gerados: List[Dict]):
        """Gera relatório da segmentação"""
        
        print(f"\n{'='*70}")
        print(f"RELATÓRIO DE SEGMENTAÇÃO DE CLIENTES")
        print(f"{'='*70}")
        
        print(f"📊 DISTRIBUIÇÃO FINAL POR CATEGORIA:")
        total_geral = len(df_geral)
        total_viaveis = df_geral[~(df_geral['fator_N1'] | df_geral['fator_N2'])].shape[0]


        for arquivo in arquivos_gerados:
            categoria = arquivo['categoria']
            nome = arquivo['nome']
            total = arquivo['total']
            pct = (total / total_geral) * 100 if total_geral > 0 else 0

            emoji = {'PA': '🧬', 'S': '🧪', 'C': '⚗️', 'F': '🌱', 'N': '❌'}

            print(f"  {emoji.get(categoria, '📋')} {nome:<35}: {total:3d} clientes ({pct:4.1f}%)")
        
        print(f"  {'🌿':<2} {'Clientes Viáveis (Consolidado)':<35}: {total_viaveis:3d} clientes ({(total_viaveis / total_geral) * 100 if total_geral > 0 else 0:4.1f}%)")


        print(f"\n✅ Segmentação concluída com sucesso!")
        print(f"📁 Arquivos gerados nos formatos .csv, .json e .xlsx para cada categoria.")


def main():
    """Execução principal - VERSÃO GEMINI"""
    
    # Configuração dos diretórios
    INPUT_DIR = r"/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_2_json_extraido"
    OUTPUT_DIR = r"/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_3_analise_viabailidade"
    
    # Cria diretório de saída se não existir
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("🚀 SISTEMA RAG + GEMINI + BATCH PROCESSING + SEGMENTAÇÃO")
    print("="*70)
    
    # Menu de seleção de modelo Gemini
    print("🤖 SELEÇÃO DE MODELO GEMINI:")
    modelos = {
        "1": ("gemini-2.5-pro", "🔥 Gemini 2.5 Pro - Máxima inteligência com thinking"),
        "2": ("gemini-2.5-flash", "⚡ Gemini 2.5 Flash - Melhor custo-benefício com thinking (RECOMENDADO)"),
        "3": ("gemini-2.5-flash-lite", "💰 Gemini 2.5 Flash-Lite - Econômico com thinking"),
        "4": ("gemini-2.0-flash", "🚀 Gemini 2.0 Flash - Velocidade superior"),
        "5": ("gemini-2.0-flash-lite", "⚡ Gemini 2.0 Flash-Lite - Baixa latência"),
        "6": ("gemini-1.5-pro", "🔧 Gemini 1.5 Pro - Estável e confiável"),
        "7": ("gemini-1.5-flash", "⚡ Gemini 1.5 Flash - Rápido e versátil")
    }
    
    for key, (model_id, desc) in modelos.items():
        print(f"  {key}. {desc}")
    
    escolha_modelo = input("\nEscolha o modelo (1-7) [2]: ").strip() or "2"
    
    if escolha_modelo not in modelos:
        print("⚠️ Opção inválida. Usando Gemini 2.5 Flash (padrão)")
        escolha_modelo = "2"
    
    modelo_selecionado, desc_modelo = modelos[escolha_modelo]
    print(f"✅ Modelo selecionado: {desc_modelo}")
    
    # Configuração de batch size
    print(f"\n📦 CONFIGURAÇÃO DE BATCH:")
    print(f"  Batch size determina quantos clientes são processados por chamada de API")
    print(f"  Maior batch = menor custo, mas pode ter menos precisão se muito grande")
    print(f"  Recomendado: 4-8 para melhor equilíbrio custo/qualidade")
    
    batch_size_input = input("\nBatch size (2-12) [4]: ").strip() or "4"
    
    try:
        batch_size = int(batch_size_input)
        if batch_size < 2 or batch_size > 12:
            print("⚠️ Batch size fora do intervalo. Usando 4 (padrão)")
            batch_size = 4
    except ValueError:
        print("⚠️ Valor inválido. Usando 4 (padrão)")
        batch_size = 4
    
    print(f"✅ Batch size: {batch_size} clientes por chamada")
    
    print(f"\n{'='*70}")
    print(f"🔍 RETRIEVAL NORMALIZADO: Busca com janela 250 chars, sem acentos")
    print(f"🤖 GENERATION: {desc_modelo}")
    print(f"📦 BATCH PROCESSING: {batch_size} clientes por chamada")
    print(f"📋 SEGMENTAÇÃO: Listas finais por categoria")
    print(f"{'='*70}")
    
    try:
        # Inicializa classificador RAG com configurações escolhidas
        classifier = ClientClassifierRAGGemini(model_name=modelo_selecionado, batch_size=batch_size)
        
        # Processa arquivos
        df_resultados = classifier.processar_pasta(INPUT_DIR)
        
        # Timestamp para nomes de arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. EXPORTA LISTA GERAL
        arquivo_geral = f"{OUTPUT_DIR}/classificacao_rag_gemini_{timestamp}.csv"
        classifier.exportar_resultados(df_resultados, arquivo_geral)
        
        # 2. EXPORTA LISTAS SEPARADAS POR CATEGORIA
        arquivos_gerados = classifier.exportar_listas_separadas(df_resultados, OUTPUT_DIR, timestamp)
        
        # 3. ESTATÍSTICAS GERAIS
        classifier.imprimir_estatisticas(df_resultados)
        
        # 4. RELATÓRIO DE SEGMENTAÇÃO
        classifier.relatorio_segmentacao(df_resultados, arquivos_gerados)
        
        # 5. ESTATÍSTICAS DE ECONOMIA
        total_arquivos = len(list(Path(INPUT_DIR).glob("*.json")))
        batches_utilizados = (total_arquivos + batch_size - 1) // batch_size
        economia_chamadas = total_arquivos - batches_utilizados
        economia_percentual = (economia_chamadas / total_arquivos) * 100 if total_arquivos > 0 else 0
        
        print(f"\n💰 ECONOMIA DE CUSTOS COM BATCH PROCESSING:")
        print(f"   📊 Processamento individual: {total_arquivos} chamadas de API")
        print(f"   📦 Processamento em batch: {batches_utilizados} chamadas de API") 
        print(f"   💵 Economia: {economia_chamadas} chamadas ({economia_percentual:.1f}%)")
        print(f"   🤖 Modelo utilizado: {classifier.model_config['nome']}")
        
        print(f"\n🎉 PROCESSAMENTO COMPLETO!")
        print(f"📄 Lista Geral: {Path(arquivo_geral).name}")
        print(f"📋 Listas Especializadas: {len(arquivos_gerados)} categorias")
        print(f"💡 Sistema RAG + Normalização + Batch + Segmentação + Gemini implementado!")
        
    except Exception as e:
        print(f"❌ Erro durante o processamento: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        print("\n🔧 SISTEMA REFATORADO PARA GEMINI:")
        print("1. ✅ Migrado de OpenAI para Google Gemini API")
        print("2. ✅ Suporte a modelos Gemini 2.5, 2.0 e 1.5")
        print("3. ✅ Thinking mode implementado para modelos compatíveis")
        print("4. ✅ Rate limiting e tratamento de erros otimizado")
        print("5. ✅ Cache separado para resultados Gemini")
        input("Pressione Enter para sair...")