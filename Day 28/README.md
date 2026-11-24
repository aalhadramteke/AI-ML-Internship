# Multi-Agent Research Assistant (fully local)

Coordinator + Research Agent + Analyzer + Critic + Writer, wired as a LangGraph.
Default: Ollama LLM + your own documents in `docs/` + local embeddings. No cloud, no API keys.

## Initialize directory
Set-Location 'C:\Linkific\Day 28'

## Setup (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# LLM: install Ollama from https://ollama.com, then:
ollama pull qwen2.5:3b
```

## Add knowledge
Put `.txt`, `.md`, `.pdf` files in `docs/`.

## Run
```powershell
$env:RA_BACKEND="ollama"
$env:RA_OLLAMA_MODEL="qwen2.5:3b"
$env:RA_SOURCE="local"
$env:RA_MAX_SOURCES="8"
$env:RA_SOURCE_CHARS="800"

dir docs 

python main.py "What does each agent do in a multi-agent research assistant?"
python main.py "How many paid leave days do Sunrise Tech employees get?"
python main.py "What is the price of the Sunrise Notes Pro plan?"
python main.py "Can a small AI model run on a 6GB graphics card?"
python main.py "Who is the CEO of Sunrise Tech?"
python main.py "Your research question"
```

Output: `output\report_<ts>.md`, `output\run_<ts>.log`.

## Go fully offline
After the first run downloads the embedding model:
```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
```

## Options
| Setting | Values |
|---|---|
| RA_BACKEND | ollama (default), openai_compat (LM Studio / llama.cpp), hf_local, hf_api, anthropic |
| RA_SOURCE | local (default), web (needs `pip install ddgs`), both |
| RA_OLLAMA_MODEL | qwen2.5:3b, qwen2.5:7b, llama3.2:3b, ... |
| RA_OPENAI_BASE | http://localhost:1234/v1 (LM Studio) |

## Files
config.py, state.py, llm.py, tools.py, agents.py, graph.py, main.py
