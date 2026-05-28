# PromptGuard CI Lite

Protótipo da Sprint 2 do grupo G11: **CI/CD e ciclo de vida para aplicações LLM (LLMOps / AgentOps)**.

O projeto demonstra uma rotina mínima de regression eval para aplicações baseadas em LLMs: prompts, casos de avaliação e linha de base ficam versionados no repositório; a cada alteração relevante, o pipeline executa as avaliações e bloqueia a entrega se a acurácia regredir mais de 10%.

## Objetivo

O objetivo é simular um fluxo de CI/CD para uma aplicação LLM simples de classificação de perguntas de contexto geral. Em vez de depender de uma API externa, o protótipo usa um provedor local determinístico que representa o comportamento do modelo. Isso permite executar a entrega em qualquer máquina e no GitHub Actions sem chave de API.

O foco do trabalho não é criar um chatbot completo, mas demonstrar o ciclo de vida LLMOps/AgentOps:

- versionamento de prompt;
- versionamento dos casos de avaliação;
- execução automática de evals;
- comparação com baseline;
- bloqueio de regressão acima de 10%;
- geração de dashboard HTML com os resultados.

As perguntas são classificadas em categorias objetivas, como `GEOGRAFIA`, `MATEMATICA`, `TECNOLOGIA`, `HISTORIA`, `CIENCIAS` e `FORA_ESCOPO`.

## Estrutura

```text
.
├── .github/workflows/promptguard-ci.yml
├── baseline.json
├── data/eval_cases.json
├── promptfooconfig.yaml
├── promptguard.py
├── prompts/system_prompt.txt
├── prompts/user_prompt.txt
├── reports/dashboard.html
└── requirements.txt
```

## Dependências

- Python 3.10 ou superior
- Node.js 20 ou superior, apenas para executar o Promptfoo

O código Python usa somente biblioteca padrão. O arquivo `requirements.txt` existe para manter o fluxo de instalação explícito.

## Como Rodar

Instale as dependências Python:

```bash
python -m pip install -r requirements.txt
```

Execute a avaliação local:

```bash
python promptguard.py evaluate
```

O comando gera:

- `reports/results.json`
- `reports/dashboard.html`

Para testar uma pergunta individual:

```bash
python promptguard.py answer "Qual é o prazo de entrega do painel?"
```

Para executar com Promptfoo:

```bash
npx --yes promptfoo@latest eval -c promptfooconfig.yaml --no-progress-bar
```

## Regra de Regressão

A linha de base está em `baseline.json`. A avaliação atual é comparada com essa baseline.

O pipeline falha quando:

```text
baseline_accuracy - current_accuracy > 0.10
```

Ou seja, uma regressão maior que 10% bloqueia o merge.

## CI/CD

O workflow `.github/workflows/promptguard-ci.yml` roda em Pull Requests que alterem código, prompt, baseline, casos de avaliação ou configuração do Promptfoo.

Etapas do workflow:

1. instala Python;
2. instala dependências do projeto;
3. executa `python promptguard.py evaluate`;
4. instala Node.js;
5. executa `npx --yes promptfoo@latest eval -c promptfooconfig.yaml`.

## Dashboard

O dashboard HTML em `reports/dashboard.html` mostra:

- acurácia atual;
- acurácia da baseline;
- regressão calculada;
- total de casos avaliados;
- casos aprovados e reprovados;
- decisão final do pipeline.

Esse arquivo serve como apoio visual para o painel acadêmico.
