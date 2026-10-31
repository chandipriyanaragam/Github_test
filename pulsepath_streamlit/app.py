"""PulsePath: clinician-reviewed symptom intake demo.

Run with: streamlit run app.py
Set OPENAI_API_KEY or configure .streamlit/secrets.toml before use.
"""

import json
import os
import re

import streamlit as st
from openai import APIError, AuthenticationError, OpenAI
from streamlit.errors import StreamlitSecretNotFoundError


st.set_page_config(page_title="PulsePath Intake", page_icon="+", layout="wide")

SYSTEM_PROMPT = """You extract information from an unstructured patient symptom description.
This is administrative clinical intake support, not diagnosis or medical advice. Return only facts
supported by the description. Do not invent symptoms, vital signs, diagnoses, demographics, or
clinical history. A missing detail must be described as 'Not reported'.

For severity, use an integer 1 through 10 only when the patient explicitly supplies a numeric
severity. Otherwise set score to null and explain 'Not reported; no numeric score provided.'
For triage urgency, choose low, moderate, or high based only on the narrative's reported features;
write a short rationale and avoid diagnostic claims. Red flags must be concrete reported facts,
not speculative diagnoses. This output requires licensed clinician review and local protocol use."""

SUMMARY_SCHEMA = {
    "name": "clinical_intake_summary",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "chief_complaint": {"type": "string"},
            "symptom_onset_duration": {"type": "string"},
            "severity": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "score": {"type": ["integer", "null"], "minimum": 1, "maximum": 10},
                    "basis": {"type": "string"},
                },
                "required": ["score", "basis"],
            },
            "red_flags": {"type": "array", "items": {"type": "string"}},
            "triage_urgency": {"type": "string", "enum": ["low", "moderate", "high"]},
            "triage_rationale": {"type": "string"},
        },
        "required": [
            "chief_complaint",
            "symptom_onset_duration",
            "severity",
            "red_flags",
            "triage_urgency",
            "triage_rationale",
        ],
    },
}


def get_api_key() -> str | None:
    """Allow local development via environment variable or Streamlit's secrets store."""
    environment_key = os.getenv("OPENAI_API_KEY")
    if environment_key:
        return environment_key

    try:
        return st.secrets.get("OPENAI_API_KEY")
    except StreamlitSecretNotFoundError:
        return None


def create_summary(symptom_description: str, api_key: str) -> dict:
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Patient symptom description:\n{symptom_description}"},
        ],
        response_format={"type": "json_schema", "json_schema": SUMMARY_SCHEMA},
        temperature=0,
        # Avoid storing this sensitive intake content on the API by default.
        store=False,
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("The model returned no structured summary.")
    return json.loads(content)


def create_demo_summary(symptom_description: str) -> dict:
    """Return an explicitly non-clinical local preview when no API key is configured."""
    narrative = " ".join(symptom_description.split())
    lower_narrative = narrative.lower()
    red_flag_terms = {
        "chest": "Reported chest symptom",
        "shortness of breath": "Reported shortness of breath",
        "difficulty breathing": "Reported difficulty breathing",
        "faint": "Reported fainting or near-fainting",
        "unconscious": "Reported loss of consciousness",
        "weakness": "Reported weakness",
        "confusion": "Reported confusion",
        "bleeding": "Reported bleeding",
    }
    red_flags = [label for term, label in red_flag_terms.items() if term in lower_narrative]
    onset_match = re.search(r"(?:since|for|about|around)\s+[^.!,;]+", narrative, re.IGNORECASE)
    numeric_severity = re.search(r"\b(10|[1-9])\s*(?:/\s*10|out of 10)\b", lower_narrative)
    score = int(numeric_severity.group(1)) if numeric_severity else None

    if red_flags:
        urgency = "high"
        rationale = "Demo preview: reported terms match a configured attention signal. This is not clinical triage."
    elif len(narrative) > 80:
        urgency = "moderate"
        rationale = "Demo preview: a detailed narrative was supplied. This is not clinical triage."
    else:
        urgency = "low"
        rationale = "Demo preview: no configured attention signals were found. This is not clinical triage."

    return {
        "chief_complaint": narrative[:220] + ("..." if len(narrative) > 220 else ""),
        "symptom_onset_duration": onset_match.group(0) if onset_match else "Not reported",
        "severity": {
            "score": score,
            "basis": "Extracted from a reported numeric score." if score is not None else "Not reported; no numeric score provided.",
        },
        "red_flags": red_flags,
        "triage_urgency": urgency,
        "triage_rationale": rationale,
    }


def urgency_style(urgency: str) -> tuple[str, str]:
    styles = {
        "low": ("#e6f4ea", "#1e6b3d"),
        "moderate": ("#fff4d6", "#806000"),
        "high": ("#fce8e6", "#a12b21"),
    }
    return styles[urgency]


st.markdown(
    """<style>
    .block-container { max-width: 1040px; padding-top: 2.5rem; }
    .stApp { background: #f7f9f8; }
    h1 { color: #173a39; } .field-label { color: #5a6868; font-size: .8rem; font-weight: 700;
    text-transform: uppercase; } .summary-value { color: #1f2d2d; font-size: 1.05rem; }
    </style>""",
    unsafe_allow_html=True,
)

st.title("PulsePath Intake")
st.caption("Turn a raw symptom narrative into a structured summary for clinician review.")
st.warning(
    "Decision support only. Verify every result and follow your local emergency and clinical protocols. "
    "Do not enter real patient data unless your approved privacy, security, and data-use controls are in place.",
    icon="⚠️",
)

with st.sidebar:
    st.header("Session")
    st.caption("The API key is read from `OPENAI_API_KEY` or Streamlit secrets and is never displayed.")
    st.divider()
    st.caption("Model")
    st.code("gpt-4o")
    st.caption("Structured output is generated as a strict JSON schema.")

example = (
    "I have had a tight feeling in my chest for about 45 minutes. It started while I was carrying "
    "groceries upstairs. It spreads to my left arm, I am sweaty and nauseated, and it seems worse now."
)
description = st.text_area(
    "Raw patient symptom description",
    value=st.session_state.get("description", ""),
    placeholder="Paste a phone transcript, patient message, or nursing note...",
    height=210,
    help="Use only authorized, appropriately protected data.",
)

left, right = st.columns([1, 5])
with left:
    if st.button("Load example", use_container_width=True):
        st.session_state.description = example
        st.rerun()
with right:
    analyze = st.button("Create clinical summary", type="primary", use_container_width=False)

if analyze:
    if not description.strip():
        st.error("Enter a symptom description before creating a summary.")
    else:
        try:
            api_key = get_api_key()
            with st.spinner("Structuring narrative..."):
                st.session_state.summary = (
                    create_summary(description.strip(), api_key)
                    if api_key
                    else create_demo_summary(description.strip())
                )
                st.session_state.description = description
                st.session_state.demo_mode = not bool(api_key)
        except AuthenticationError:
            st.error("The OpenAI API key was rejected. Check the configured key and try again.")
        except APIError as error:
            st.error(f"OpenAI API request failed: {error}")
        except (ValueError, json.JSONDecodeError) as error:
            st.error(f"Could not read the structured summary: {error}")

summary = st.session_state.get("summary")
if summary:
    st.divider()
    if st.session_state.get("demo_mode"):
        st.info(
            "Demo mode: this preview was generated locally with simple text matching, not GPT-4o. "
            "Configure an API key for model-generated output.",
            icon="ℹ️",
        )
    st.subheader("Structured clinical summary")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="field-label">Chief complaint</div>', unsafe_allow_html=True)
        st.write(summary["chief_complaint"])
    with col2:
        st.markdown('<div class="field-label">Symptom onset & duration</div>', unsafe_allow_html=True)
        st.write(summary["symptom_onset_duration"])

    st.write("")
    severity_col, urgency_col = st.columns(2)
    with severity_col:
        st.markdown('<div class="field-label">Severity (1-10)</div>', unsafe_allow_html=True)
        score = summary["severity"]["score"]
        st.metric("Reported severity", f"{score}/10" if score is not None else "Not reported")
        st.caption(summary["severity"]["basis"])
    with urgency_col:
        st.markdown('<div class="field-label">Triage urgency</div>', unsafe_allow_html=True)
        urgency = summary["triage_urgency"]
        background, foreground = urgency_style(urgency)
        st.markdown(
            f'<span style="display:inline-block;padding:.5rem .75rem;border-radius:.35rem;'
            f'background:{background};color:{foreground};font-weight:700;text-transform:uppercase;">{urgency}</span>',
            unsafe_allow_html=True,
        )
        st.caption(summary["triage_rationale"])

    st.markdown('<div class="field-label">Reported red flags</div>', unsafe_allow_html=True)
    if summary["red_flags"]:
        for flag in summary["red_flags"]:
            st.markdown(f"- {flag}")
    else:
        st.caption("No red flags were explicitly reported in this description.")

    with st.expander("View structured JSON"):
        st.json(summary)
