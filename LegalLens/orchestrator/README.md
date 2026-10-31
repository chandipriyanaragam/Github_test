# LegalLens Orchestrator: Intent Classifier

This is an independent module for classifying one user message into `ask`, `draft`, or `summarize`. It does not call or depend on the LegalLens backend and does not generate workflow content.

## Setup (PowerShell)

From `LegalLens/orchestrator`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Put your API key in this directory's `.env` file:

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-6-luna
```

The `.env` file is ignored by Git. Keep the key there and do not commit it.

## Try a classification

```powershell
python -m legallens_orchestrator.cli "Summarize this contract in five bullets"
```

Or run interactively:

```powershell
python -m legallens_orchestrator.cli
```

Example output:

```json
{
  "intent": "summarize",
  "confidence": 0.98,
  "reason": "The user asks for the contract's contents to be condensed into bullets."
}
```

## Python API

```python
from legallens_orchestrator import classify_intent

result = classify_intent("Draft a polite response to this notice")
print(result.intent, result.confidence, result.reason)
```

The returned Pydantic model validates the label and confidence range. Empty messages raise `ValueError`; missing API credentials raise `RuntimeError`. Model, network, and provider errors are allowed to surface to the caller so the caller can report or retry them.

## Scope and model configuration

The default model is `gpt-6-luna`; override it with `OPENAI_MODEL` if needed. The classifier uses temperature 0 and LangChain structured output to constrain the response to the declared schema. Intent definitions and tie-break rules live in [intent-classification.prompt.md](intent-classification.prompt.md).
