# Extrator de Dados da FAPESP com Gemini

Este projeto é um script em Python para automatizar a extração de informações detalhadas sobre pesquisadores a partir da Biblioteca Virtual (BV) da FAPESP. Ele utiliza Selenium para navegar e extrair o conteúdo das páginas e a API do Google Gemini para processar e estruturar os dados em formato JSON e CSV.

## Funcionalidades Principais

- **Busca Automatizada**: Procura pesquisadores na BV FAPESP a partir de uma lista de nomes.
- **Extração de Conteúdo**: Coleta todo o texto da página de perfil do pesquisador.
- **Processamento com IA**: Utiliza a API do Google Gemini para analisar o texto e extrair informações estruturadas com base em um prompt detalhado.
- **Múltiplos Modelos Gemini**: Permite a escolha entre diferentes versões do Gemini (1.0, 1.5, etc.).
- **Modo de Processamento Flexível**:
    - **Individual**: Processa um nome por vez.
    - **Batch Otimizado**: Processa um lote de pesquisadores (tamanho configurável de 3 a 10) em uma única chamada à API, gerando grande economia de custos e tempo.
- **Geração de Múltiplos Arquivos**:
    - Para cada pesquisador encontrado, gera um arquivo `.json` e um `.csv` individuais.
    - Ao final da execução, gera dois relatórios consolidados:
        1. `relatorio_comparativo_...csv`: Lista todos os nomes pesquisados com o status "Encontrado" ou "Não Encontrado".
        2. `nomes_nao_encontrados_...csv`: Lista apenas os nomes que não foram localizados.

## Tecnologias Utilizadas

- **Python 3**
- **Google Generative AI (Gemini)**: Para processamento de linguagem natural.
- **Selenium**: Para automação de navegador e web scraping.
- **Pandas**: Para manipulação de dados e criação de arquivos CSV.
- **WebDriver Manager**: Para gerenciamento automático do driver do Chrome.

---

## Instalação e Configuração

Siga os passos abaixo para configurar o ambiente de execução.

### 1. Pré-requisitos

- Python 3.8 ou superior.
- Google Chrome instalado.

### 2. Instalar Dependências

Execute o comando abaixo para instalar todas as bibliotecas necessárias:

```bash
pip install google-generativeai selenium pandas webdriver-manager
```

### 3. Configurar a API Key do Gemini

Você precisa de uma API Key do Google AI Studio.

Abra o arquivo `Execute_1_busca_internet_gemi_6.py` e insira sua chave na seguinte linha:

```python
# Linha 23 (aproximadamente)
def configurar_api_key():
    """Configura a API key do Gemini"""
    api_key = 'SUA_API_KEY_AQUI'  # <-- SUBSTITUA PELA SUA CHAVE
    os.environ['GOOGLE_API_KEY'] = api_key
    print("✅ API Key configurada")
    return True
```

---

## Como Usar

### 1. Estrutura de Pastas

O script utiliza caminhos absolutos (hardcoded) para entrada e saída. Certifique-se de que estas pastas existam ou ajuste os caminhos no script.

- **Pasta de Entrada**: Onde você deve colocar seu arquivo `.csv` com os nomes dos pesquisadores.
  - **Caminho no script**: `CONFIG['PASTA_NOMES']`
  - **Valor Padrão**: `/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_1_Lista_nomes_cvs`

- **Pasta de Saída**: Onde todos os arquivos de resultado (JSON, CSV individuais e relatórios) serão salvos.
  - **Caminho no script**: `CONFIG['PASTA_RESULTADOS']`
  - **Valor Padrão**: `/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_2_json_extraido`

### 2. Preparar o Arquivo de Entrada

- Crie um arquivo `.csv` na pasta de entrada.
- O arquivo deve conter uma coluna com os nomes completos dos pesquisadores. O script reconhece nomes de colunas comuns como `nome`, `name`, `pesquisador`, etc.

### 3. Executar o Script

Abra um terminal e execute o script com Python:

```bash
python3 Execute_1_busca_internet_gemi_6.py
```

### 4. Siga o Menu Interativo

O script irá guiá-lo através de um menu de configuração:

1.  **Escolha do Modelo Gemini**: Selecione a versão da IA que deseja usar. A opção `[1]` (Gemini 1.5 Flash) é a padrão.
2.  **Escolha da Opção de Processamento**:
    - **`1` a `3`**: Modos individuais.
    - **`4`**: **Modo Batch Otimizado (Recomendado)**. Esta opção carrega um arquivo CSV.
3.  **Configuração do Batch Size** (se escolher a opção 4): Defina quantos pesquisadores serão processados por vez em cada chamada à API (entre 3 e 10). O padrão é 5.
4.  **Confirmação**: Pressione `Enter` para iniciar.
5.  **Modo Headless**: Decida se deseja ver a janela do navegador durante a execução.

---

## Saída (Resultados)

Todos os arquivos são salvos na `PASTA_RESULTADOS`.

### Resultados Individuais

Para cada pesquisador encontrado, dois arquivos são criados:

- `FAPESP_[Nome]_[Timestamp].json`: Contém todos os dados extraídos pela IA em formato JSON, com metadados sobre a execução.
- `FAPESP_[Nome]_[Timestamp].csv`: Contém os mesmos dados, mas formatados em uma única linha de um arquivo CSV.

### Relatórios Finais

Ao final de todo o processo, dois relatórios em CSV são gerados:

- `relatorio_comparativo_[Timestamp].csv`: Uma tabela com todos os nomes do arquivo de entrada e uma coluna `status` indicando se foram `Encontrado` ou `Não Encontrado`.
- `nomes_nao_encontrados_[Timestamp].csv`: Uma lista simples contendo apenas os nomes dos pesquisadores que não foram encontrados.
