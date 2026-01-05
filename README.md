#  AI Sandbox-Powered Data Analyst

A lightweight **CLI data analyst agent** that can:

- Upload a local dataset (`.csv` / `.xlsx`) into a secure, remote Python sandbox (E2B)
- Let an LLM drive **iterative analysis** by executing Python code in the sandbox
- Save any static visualizations produced by the sandbox **back to your machine** under `charts/`

This project showcases:

- Tool-using LLM orchestration
- Sandboxed code execution for safety
- Practical data-analysis UX via a simple terminal loop

---

## What `agent.py` does

`agent.py` runs a terminal application that:

1. Creates a conversation/session using the OpenAI client
2. Prompts you for a dataset path
3. Creates an E2B sandbox
4. Uploads your dataset into the sandbox
5. Spins up an agent with a single tool: **`python_code_execution`**
6. Runs an initial “understand the data” prompt
7. Enters a chat loop where you can ask questions and the agent executes Python to answer

### Chart saving (static)

If the executed code generates display outputs (e.g., `matplotlib` with `plt.show()`), the tool:

- Extracts image artifacts from `execution.results`
- Saves them locally as:

```
charts/chart_1.png
charts/chart_2.png
...
```

If no chart artifacts are detected, the tool returns the available result formats to help debug.

### Error logging

Sandbox execution errors are written to:

- `error.log`

This keeps your terminal output clean while preserving traceability.

---

## Tech stack

- **Python** (async)
- **OpenAI SDK** (`AsyncOpenAI`) for model calls
- **E2B Code Interpreter** (`AsyncSandbox`) for sandboxed Python execution
- **Agents framework** (`Agent`, `Runner`, `FunctionTool`, `ModelSettings`) for tool-using orchestration

---

## Installation

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

> Note: the `agents` dependency must match the library that provides:
> `Agent`, `Runner`, `FunctionTool`, and `ModelSettings`.
> If `pip` cannot resolve `agents`, install the correct package for your environment.

### 3) Set environment variables

You will need credentials for:

- **OpenAI**
- **E2B**

Typical setup (macOS / zsh):

```bash
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
export E2B_API_KEY="YOUR_E2B_KEY"
```

If your environment uses different variable names, set them according to your SDK configuration.

---

## Usage

Run the app:

```bash
python agent.py
```

You’ll be prompted:

1. **Dataset path** (local):

Example:

```text
Enter the path to the file you want to analyze: ./timeliner.xlsx
```

2. Then interact with the agent:

```text
Enter your message (or 'quit' to exit): summarize the dataset
```

Type `quit` to exit.

---

## Example prompts

### Quick overview

- “Give me a 200 word summary of the dataset structure.”
- “List the columns and missingness rates.”

### Comparative analysis

- “Compare mask usage across countries by income group.”
- “Which indicators differ the most between high- and low-income settings?”

### Time series / timelines

- “Create a time series chart that shows the number of events recorded each month.”
- “Show monthly event counts by year and highlight spikes.”

> Tip: for charts, ask explicitly for a visualization. The tool saves the image under `charts/`.

---

## Output files

- **`charts/`**
  - Saved static plots (`.png` / `.svg`) generated in the sandbox
- **`error.log`**
  - Logged sandbox execution errors

---

## Notes & limitations (MVP)

- **Async + CLI input**: this is a simple terminal MVP and uses `input()`.
- **File formats**: the agent is instructed to load via `pd.read_csv` or `pd.read_excel` depending on the dataset.
- **Sandbox timeouts**: the sandbox is currently created with `timeout=0` (meaning depends on E2B defaults). Adjust as needed.
- **Chart generation**: charts are saved only when the executed code produces a display result (e.g., with `plt.show()`).

---

## Portfolio highlights (why this project matters)

- **Safety by design**: code execution happens in an isolated sandbox, reducing risk.
- **Tool-using agent loop**: demonstrates how to wrap “code execution” as a tool for an LLM.
- **Real developer ergonomics**: persistent logs, deterministic chart saving, and a minimal but useful UX.

---

License: [MIT](LICENSE)
