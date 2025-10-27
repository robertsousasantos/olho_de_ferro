# Sistema de Classificação de Clientes com RAG e Gemini (`Execute_2_Verificacao de viabilidade_v16.py`)

Este script é um sistema avançado para classificar pesquisadores (clientes) com base em seu perfil e área de atuação, utilizando uma abordagem de **Retrieval-Augmented Generation (RAG)** com a API do **Google Gemini**. O objetivo é identificar o potencial de cada cliente para diferentes frentes de negócio em biotecnologia.

## Visão Geral do Funcionamento

O sistema processa uma pasta de arquivos JSON, onde cada arquivo contém informações extraídas sobre um pesquisador. Para cada pesquisador, o script:

1.  **Retrieval (Recuperação):** Extrai e normaliza informações-chave do arquivo JSON, como linhas de pesquisa, palavras-chave e técnicas utilizadas. Ele busca por termos específicos associados a critérios predefinidos.
2.  **Generation (Geração):** Monta um *prompt* estruturado contendo as evidências recuperadas e o envia para o modelo de linguagem (LLM) do Google Gemini.
3.  **Batch Processing (Processamento em Lote):** Para otimizar custos e tempo, o script agrupa vários clientes em uma única chamada à API do Gemini, processando-os em lote.
4.  **Classificação:** O Gemini analisa as evidências e classifica cada cliente em múltiplos critérios, retornando os resultados em formato JSON.
5.  **Pontuação e Segmentação:** O script calcula uma pontuação para cada categoria principal (Produção de Proteína, Síntese de Gene, etc.), atribui uma classificação final (ex: "CLIENTE ESTRATÉGICO") e segmenta os clientes em listas especializadas.
6.  **Exportação:** Gera relatórios detalhados em formatos CSV, JSON e Excel, incluindo uma lista geral e listas separadas para cada categoria de interesse.

## Principais Funcionalidades

-   **Integração com Google Gemini:** Suporte para uma variedade de modelos Gemini (2.5 Pro, 2.5 Flash, 1.5 Pro, etc.), permitindo ao usuário escolher o melhor balanço entre custo, velocidade e precisão.
-   **Processamento em Lote (Batch Processing):** Reduz significativamente o número de chamadas à API, resultando em uma grande economia de custos (estimada em mais de 80%).
-   **Sistema de Cache:** Utiliza um banco de dados SQLite (`client_classifier_rag_cache_gemini.db`) para armazenar os resultados das classificações. Se um arquivo não foi modificado, o resultado é recuperado do cache, evitando reprocessamento e custos desnecessários.
-   **Lógica de Classificação Robusta:**
    -   **4 Categorias Principais:**
        -   `PA`: Produção de Proteína
        -   `S`: Síntese de Gene
        -   `C`: CFPS (Cell-Free Protein Synthesis)
        -   `F`: Fatores de Crescimento
    -   **2 Fatores Negativos:** Identifica perfis que não utilizam proteínas recombinantes (`N1`) ou atuam em áreas não correlatas à biotecnologia (`N2`).
-   **Segmentação Automática:** Cria listas de clientes separadas para cada uma das 4 categorias principais, facilitando o direcionamento de campanhas de marketing e vendas.
-   **Interface de Linha de Comando (CLI) Interativa:** Permite que o usuário selecione o modelo Gemini e configure o tamanho do lote (batch size) antes de iniciar o processamento.

## Como Utilizar

### 1. Pré-requisitos

-   Python 3 instalado.
-   Bibliotecas necessárias instaladas: `pandas`, `requests`, `openpyxl`.
-   Uma chave de API do Google Gemini.

### 2. Configuração

-   **Chave da API:** Insira sua chave da API do Google Gemini na variável `self.api_key` dentro da classe `ClientClassifierRAGGemini`.
    ```python
    # LINHA 30
    self.api_key = 'SUA_CHAVE_API_AQUI'
    ```
-   **Diretórios de Entrada/Saída:** Os caminhos dos diretórios de entrada e saída são definidos na função `main()`. Por padrão:
    -   **Entrada:** `/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_2_json_extraido`
    -   **Saída:** `/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_3_analise_viabailidade`

### 3. Execução

Execute o script a partir do seu terminal:

```bash
python "Execute_2_Verificacao de viabilidade_v16.py"
```

Ao ser executado, o programa solicitará:
1.  A escolha do **modelo Gemini** a ser utilizado.
2.  O **tamanho do lote (batch size)** para o processamento.

O script então iniciará o processo de classificação e exibirá o progresso em tempo real.

## Arquivos de Saída

O script gera os seguintes arquivos no diretório de saída:

-   **`classificacao_rag_gemini_[timestamp].(csv|json|xlsx)`**: Um relatório completo com todos os clientes processados, suas pontuações, classificações e a justificativa para a classificação final.
-   **`lista_[CATEGORIA]_[nome_categoria]_[timestamp].(csv|json|xlsx)`**: Listas segmentadas para cada categoria (`PA`, `S`, `C`, `F`, `N`). Por exemplo:
    -   `lista_PA_producao_proteina_...`
    -   `lista_C_cfps_...`
-   **`lista_clientes_viaveis_[timestamp].(csv|json|xlsx)`**: Uma lista consolidada contendo todos os clientes considerados viáveis (ou seja, que não foram classificados na categoria `N`).

Este README fornece uma visão geral do funcionamento e das capacidades do script `Execute_2_Verificacao de viabilidade_v16.py`.
