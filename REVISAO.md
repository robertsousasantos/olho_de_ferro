# Revisão do projeto "Olho de Ferro"

## Execução prática

| Etapa | Comando | Resultado |
|-------|---------|-----------|
| Extração (Etapa 1) | `python -m src.step1_extraction` | Falhou ao inicializar o Selenium porque o `webdriver-manager` precisa baixar o ChromeDriver da internet, algo bloqueado neste ambiente. 【8715d9†L1-L7】 |
| Classificação (Etapa 2) | `python -m src.step2_classification` | Interrupção imediata: não há JSONs na pasta de entrada, portanto o pipeline não segue adiante. 【711d4c†L1-L6】 |
| Busca de e-mails (Etapa 3) | `python -m src.step3_email_search` | O script aborta antes de rodar por causa de um erro de sintaxe na f-string que imprime o modo do browser. 【1fc291†L1-L10】 |

> **Observação:** mesmo que o ambiente tivesse acesso à internet, ainda seria necessário instalar o Google Chrome/Chromium para que o Selenium conseguisse abrir o navegador. O projeto depende de uma automação de navegador real e não fornece alternativa headless baseada em HTML estático.

## Problemas principais por etapa

### Etapa 1 – `src/step1_extraction.py`
* O construtor interrompe o processo se a variável `GOOGLE_API_KEY` não estiver definida, mas a chave só é exigida depois que o usuário passa por várias interações via `input()`. Isso torna a experiência ruim e dificulta o reuso programático do extrator. 【F:src/step1_extraction.py†L29-L168】
* A classe inteira é projetada para execução interativa e bloqueia a automação: há pelo menos cinco chamadas a `input()` (seleção de modelo, modo, criação de CSV, confirmação de início, modo headless), o que inviabiliza rodar em produção sem monkeypatch. 【F:src/step1_extraction.py†L97-L198】【F:src/step1_extraction.py†L620-L707】
* O método `processar_resposta_gemini` faz parsing por texto livre apenas dividindo a resposta em linhas com `:`. Qualquer campo que contenha o caractere `:` no corpo (por exemplo URLs ou descrições) quebra o mapeamento e pode descartar dados válidos. 【F:src/step1_extraction.py†L548-L579】
* Há código duplicado (`processar_batch`) e comentários `# ...` que sugerem trechos omitidos/obsoletos. Isso dificulta a manutenção e aumenta o risco de regressões. 【F:src/step1_extraction.py†L520-L707】
* O pipeline assume que o `webdriver-manager` conseguirá baixar o ChromeDriver em tempo de execução, sem prever cache offline ou dependência explicitada no repositório. 【F:src/step1_extraction.py†L36-L116】

### Etapa 2 – `src/step2_classification.py`
* O construtor aceita modelos como `gemini-2.5-flash`, mas a tabela `self.modelos_disponiveis` só define versões 1.5; quando se pede 2.5 o código troca silenciosamente para `gemini-1.5-flash`. Isso gera relatórios inconsistentes e confusos para o usuário. 【F:src/step2_classification.py†L37-L47】
* A função crítica `classificar_batch_gemini` não faz requisições ao Gemini; em vez disso roda uma heurística baseada em substring, mas o resto da classe é escrito como se houvesse um motor RAG real. O resultado final não reflete os prompts prometidos na documentação. 【F:src/step2_classification.py†L94-L140】
* A cache SQLite é criada mas nunca lida: não existem consultas que reaproveitem classificações anteriores. O custo de manter o arquivo e o código extra não traz benefício. 【F:src/step2_classification.py†L49-L72】
* Imports como `hashlib`, `time` e `requests` não são usados; isso indica dívida técnica e complica o entendimento do que realmente é necessário para rodar. 【F:src/step2_classification.py†L5-L16】

### Etapa 3 – `src/step3_email_search.py`
* O script não compila por conta de f-strings com aspas duplas internas sem escape nas linhas 296-297. Isso impede qualquer execução. 【F:src/step3_email_search.py†L282-L299】
* Mesmo após corrigir a sintaxe, a biblioteca `browser_use` exige Playwright/navegador instalado; o repositório não documenta essa dependência nem oferece scripts de provisionamento, tornando a etapa frágil. 【F:src/step3_email_search.py†L31-L47】【F:src/step3_email_search.py†L198-L258】
* A lógica de `_extrair_email_do_resultado` depende de um formato textual específico gerado pelo agente; qualquer mudança no prompt do `browser_use` faz a extração falhar, porque o código só considera linhas com `📧 EMAIL:` ou uma regex sem validação de domínio. 【F:src/step3_email_search.py†L120-L183】

## Arquitetura e orquestração
* O orquestrador `src/main.py` simplesmente encadeia as três classes, mas cada etapa exige interação manual (`input()`), o que inviabiliza rodar o pipeline de ponta a ponta em modo batch. 【F:src/main.py†L24-L93】
* Como a Etapa 1 depende de navegador real e rede liberada, todo o pipeline falha em ambientes controlados (CI/CD, servidores sem GUI). Falta uma estratégia headless baseada em API pública ou dados exportados.
* Não existe suíte de testes automatizados nem verificação estática; qualquer alteração precisa ser validada manualmente.

## Recomendações
1. **Rever dependência do Selenium**: parametrizar para aceitar HTML pré-baixado ou mockar o driver em ambientes sem Chrome, e permitir configuração via argumentos em vez de `input()`.
2. **Implementar de fato o consumo do Gemini** ou, alternativamente, documentar que a classificação usa heurística simples até que a integração seja concluída.
3. **Corrigir o erro de sintaxe das f-strings e encapsular a etapa 3 em funções puramente programáticas**, substituindo `input()` por parâmetros e adicionando testes unitários para `_extrair_email_do_resultado`.
4. **Adicionar scripts de instalação de dependências extras** (Chromium, Playwright) ou documentar claramente os pré-requisitos.
5. **Criar testes ou pelo menos checagens automatizadas** para garantir que cada módulo importe corretamente e que caminhos de arquivo existam antes do processamento.

Com esses ajustes o projeto tende a ficar mais previsível e mais fácil de executar em ambientes reais.
