# Buscador de Emails FAPESP com Gemini e Browser-Use (`Execute_3_Integracao 4.py`)

Este script automatiza a busca por endereços de email de pesquisadores, combinando a inteligência da API **Google Gemini** com a capacidade de automação de navegador da biblioteca **`browser-use`**. O sistema é projetado para encontrar emails de contato específicos de indivíduos, evitando endereços genéricos.

## Visão Geral do Funcionamento

O processo é executado na seguinte sequência:

1.  **Carregamento de Dados:** O script lê um arquivo CSV de uma pasta de entrada (`Passo_4_lista_email`) que contém os nomes dos pesquisadores a serem processados.
2.  **Busca de Contexto:** Para cada nome, ele procura um arquivo JSON correspondente em uma segunda pasta (`Passo_2_json_extraido`) para obter informações adicionais, como a instituição de vínculo do pesquisador.
3.  **Seleção de Configurações:** O usuário seleciona interativamente qual modelo Gemini deseja usar, se o navegador deve rodar de forma visível ou invisível (*headless*), e se a capacidade de visão do modelo deve ser ativada.
4.  **Automação da Busca (Browser-Use):** Para cada pesquisador, o script instancia um agente de IA (`Agent` do `browser-use`). Este agente recebe um *prompt* detalhado com a missão de encontrar o email e uma estratégia de busca.
5.  **Execução com Gemini:** O modelo Gemini controla o navegador, realizando buscas no Google, visitando páginas de instituições, perfis acadêmicos (Lattes, Google Scholar) e analisando o conteúdo para localizar o email.
6.  **Validação e Extração:** O resultado da busca é processado para extrair um email válido. O script possui regras para rejeitar emails genéricos (como `contato@`, `secretaria@`, etc.).
7.  **Salvamento dos Resultados:**
    -   Um novo arquivo JSON é salvo na pasta de saída (`Passo_5_json_final`), contendo todos os dados originais do pesquisador mais o email encontrado.
    -   Um arquivo de log detalhado é salvo na pasta `Logs_busca_email`, registrando todo o processo de busca para fins de auditoria e depuração.

## Principais Funcionalidades

-   **Inteligência Artificial na Navegação:** Utiliza o poder dos modelos Gemini para decidir os passos da busca, tornando o processo mais humano e eficiente que *scrapers* tradicionais.
-   **Interface Interativa:** Permite ao usuário configurar a execução, escolhendo o modelo de IA e o modo de operação do navegador, oferecendo flexibilidade entre desempenho e capacidade de depuração.
-   **Integração de Fontes de Dados:** Cruza informações de um CSV com uma base de arquivos JSON para enriquecer o contexto da busca.
-   **Validação de Email:** Implementa uma lógica para filtrar emails genéricos e de departamento, focando em encontrar o contato pessoal do pesquisador.
-   **Logging Completo:** Gera um registro detalhado de cada busca, o que é crucial para entender o "raciocínio" do agente de IA e verificar a fonte da informação.
-   **Tolerância a Falhas:** Estruturado para continuar o processo mesmo que a busca por um pesquisador falhe, e reporta estatísticas detalhadas no final da execução.

## Como Utilizar

### 1. Pré-requisitos

-   Python 3 instalado.
-   Instalar as bibliotecas necessárias. Execute os seguintes comandos no seu terminal:
    ```bash
    pip install browser-use google-generativeai pandas
    playwright install chromium
    ```
-   Uma chave de API válida do Google Gemini.

### 2. Configuração

-   **Chave da API:** Insira sua chave da API do Google Gemini na variável `GOOGLE_API_KEY` no início do script.
    ```python
    # LINHA 20
    GOOGLE_API_KEY = 'SUA_CHAVE_API_AQUI'
    ```
-   **Estrutura de Pastas:** O script espera a seguinte estrutura de pastas a partir do caminho base definido em `BASE_PATH`:
    -   `Passo_4_lista_email/`: Deve conter o arquivo CSV com a coluna `nome` dos pesquisadores.
    -   `Passo_2_json_extraido/`: Deve conter os arquivos JSON com os dados detalhados de cada pesquisador.
    -   `Passo_5_json_final/`: Pasta onde os JSONs atualizados com os emails serão salvos.
    -   `Logs_busca_email/`: Pasta onde os logs de cada busca serão armazenados.

### 3. Execução

Execute o script a partir do seu terminal:

```bash
python "Execute_3_Integracao 4.py"
```

O programa irá guiá-lo através das opções de configuração (modelo, modo do navegador, etc.) e solicitará uma confirmação final antes de iniciar a busca.

## Arquivos de Saída

-   **JSONs de Resultado (em `Passo_5_json_final/`):** Para cada pesquisador processado, um novo arquivo JSON (ex: `Nome_do_Pesquisador_email_[timestamp].json`) é criado. Este arquivo contém os dados originais e a nova chave `email_contato`.
-   **Logs de Busca (em `Logs_busca_email/`):** Para cada tentativa de busca, um arquivo JSON de log (ex: `busca_Nome_do_Pesquisador_[timestamp].json`) é gerado, contendo o resultado completo retornado pelo agente `browser-use`.
