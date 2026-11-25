# Setup and Run

How to install and run the Multi-Agent Research Assistant dashboard.

## Requirements

- Python 3.10 or newer
- Ollama, if you use the default local backend
- About 4 GB of free RAM for `qwen2.5:3b`

## 1. Install dependencies

From the project folder:

```powershell
Set-Location "Day 29"
```

```powershell
pip install -r requirements.txt
```

## 2. Start the local model (default backend)

In a separate terminal, leave this running:

```powershell
ollama serve
```

Then pull the model the dashboard expects:

```powershell
ollama pull qwen2.5:3b
```

If you prefer a different backend, choose it in the sidebar: OpenAI-compatible
local server, local Transformers, Hugging Face Inference API, or Anthropic.
Hosted backends need their usual environment variable (`HF_TOKEN` or
`ANTHROPIC_API_KEY`).

## 3. Run the dashboard

```powershell
python -m streamlit run app.py
```

Streamlit prints a local URL (usually `http://localhost:8501`) and opens it.

To pin the port:

```powershell
python -m streamlit run app.py --server.port 8520
```

On this machine, in Git Bash:

```bash
cd "/c/Linkific/Day 29"
"/c/Program Files/Python313/python" -m streamlit run app.py --server.port 8520
```

## 4. Stop the dashboard

Press `Ctrl+C` in the terminal running Streamlit.

## Optional settings

All of these can be changed from the sidebar, no restart needed:

| Setting | What it does |
| --- | --- |
| Backend | Which model provider to call |
| Model name | Model identifier for the chosen backend |
| Source mode | `local` documents, `web` search, or `both` |
| Documents folder | Where local `.txt`, `.md`, and `.pdf` files are read from (default `docs`) |
| Analysis passes | Maximum analyzer loop iterations |
| Writing passes | Maximum writer loop iterations |
| Approval threshold | Critic score required to accept a draft |

Environment variables from `config.py` still work as defaults, for example
`RA_BACKEND`, `RA_OLLAMA_MODEL`, `RA_SOURCE`, `RA_DOCS_DIR`.

## Notes

- Keep `.streamlit/config.toml`. It sets the light theme the layout is designed
  for; without it the widgets fall back to Streamlit's dark default and the
  page will look inconsistent.
- Completed runs are saved under `output/`.
- To use local documents, put `.txt`, `.md`, or `.pdf` files in `docs/` and set
  source mode to `local` or `both`.
- The command-line version still works independently:

  ```powershell
  python main.py "What are the benefits of AI code assistants?"
  ```

## Troubleshooting

**`Port 8501 is not available`**
Another Streamlit instance is already running. Either open that one, or start
this one on a different port with `--server.port 8521`.

**`Connection refused` or model errors from Ollama**
Check that `ollama serve` is running and that the model name in the sidebar
matches what you pulled (`ollama list`).

**Report says no sources were retrieved**
The `docs/` folder is empty or unreadable. Add files, or switch source mode to
`web` or `both`.

**Dashboard looks dark or unstyled**
`.streamlit/config.toml` is missing. Restore it and restart Streamlit.
