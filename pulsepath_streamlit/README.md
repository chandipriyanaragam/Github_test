# PulsePath Intake

Streamlit app that turns a raw symptom narrative into a structured, clinician-reviewable summary using `gpt-4o`.

## Run

1. From this folder, install dependencies: `pip install -r requirements.txt`
2. Set `OPENAI_API_KEY` in your shell, or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add the key there.
3. Start the app: `streamlit run app.py`

The app uses strict JSON-schema output for chief complaint, onset and duration, severity, red flags, and triage urgency. It sets `store=False` on the request. Treat it as a prototype: real clinical use requires privacy, security, validation, governance, and protocol integration.
