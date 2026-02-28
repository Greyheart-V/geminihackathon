import streamlit as st
import os
import re
from collections import Counter
from google import genai
from dotenv import load_dotenv

# API key: st.secrets on Streamlit Cloud, .env locally
load_dotenv()
try:
    api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
except Exception:
    api_key = None
if not api_key:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY in Secrets (Cloud) or .env (local).")

client = genai.Client(api_key=api_key)

# Session state: conversation, cases, last assessment (for follow-up form)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "cases" not in st.session_state:
    st.session_state.cases = []
if "last_response_text" not in st.session_state:
    st.session_state.last_response_text = None
if "last_severity" not in st.session_state:
    st.session_state.last_severity = None
if "last_color" not in st.session_state:
    st.session_state.last_color = None
if "last_risk_score" not in st.session_state:
    st.session_state.last_risk_score = None

# Model system prompt (triage rules, output format, no dosages)
SYSTEM_INSTRUCTION = """
You are a livestock triage assistant for Kenyan smallholder farmers.

SCOPE:
- Livestock: cattle (dairy and beef), goats, sheep
- Poultry: layers, broilers, indigenous/local chickens
- Kenyan smallholder conditions (low-cost, local inputs, limited vet access)

GOAL:
Provide SAFE preliminary triage and stabilization guidance only.

STRICT RULES:
1. Always output using EXACT markdown headings:
   ## Likely Issue
   ## Severity
   ## Immediate Care Steps
   ## When to Call a Vet

2. Severity MUST be one of:
   - LOW
   - MEDIUM
   - HIGH

3. If severity is HIGH:
   - The FIRST line under Immediate Care Steps must say:
     "Contact a licensed veterinarian immediately."

4. Never give drug dosages.
5. Prefer low-cost, locally accessible interventions.
6. If information is insufficient, state what additional signs to check.

STYLE:
- Clear
- Practical
- Farmer-friendly
- Kenya-relevant

If analyzing an image, clearly state:
"Image-based assessment may be inaccurate."
"""

st.set_page_config(page_title="Livestock Early Warning System", page_icon="🐄")
st.title("Kenya Livestock Early Warning & Risk Monitoring System")
st.write("Preliminary triage for livestock (cattle, goats, sheep) and poultry. Early risk detection only—not a substitute for a vet.")
st.warning(
    "⚠️ This tool provides preliminary livestock triage only. "
    "It does NOT replace a licensed veterinarian."
)

with st.expander("📞 Emergency Vet Guidance (Kenya)"):
    st.write(
        "If symptoms are severe, contact your nearest veterinary officer "
        "or county livestock extension office immediately."
    )

language = st.selectbox(
    "Language",
    ["English", "Swahili"],
)

VET_CONTACTS = {
    "Nairobi": "County Vet: +254 700 000 000",
    "Kiambu": "County Vet: +254 711 111 111",
    "Nakuru": "County Vet: +254 722 222 222",
}

col1, col2 = st.columns(2)
with col1:
    livestock_type = st.selectbox(
        "Livestock Type",
        [
            "Cattle (Dairy)",
            "Cattle (Beef)",
            "Goat",
            "Sheep",
            "Poultry (Layers)",
            "Poultry (Broilers)",
            "Poultry (Indigenous/Local)",
        ],
    )
with col2:
    age_stage = st.selectbox(
        "Age/Stage",
        [
            "Young (calf/kid/lamb/chick)",
            "Grower",
            "Adult / Milking / Laying",
            "Incubation (poultry)",
            "Other",
        ],
    )

symptom = st.selectbox(
    "Primary Symptom",
    [
        "Lethargy / Weakness",
        "Drop in Production",
        "Abnormal Droppings",
        "Off-Feed",
        "Respiratory Issues",
        "Bloat / Swelling",
        "Wound / Visible injury",
    ],
)
extra_details = st.text_area("Additional Details (Optional)", placeholder="E.g., Started 2 days ago...")

county = st.selectbox(
    "Your County",
    ["Nairobi", "Kiambu", "Nakuru", "Other"],
)

uploaded_image = st.file_uploader(
    "Upload image of the animal (optional)",
    type=["jpg", "jpeg", "png"],
)

if st.button("Analyze Symptoms"):
    with st.spinner("Analyzing symptoms..."):

        conversation_context = "\n".join(st.session_state.chat_history)

        compiled_prompt = f"""
Previous conversation:
{conversation_context}

New farmer report:
Livestock: {livestock_type}
Age/Stage: {age_stage}
Primary Symptom: {symptom}
Details: {extra_details if extra_details else "None provided"}

If information is insufficient, ask EXACTLY 2 targeted yes/no or short-answer questions.
Do NOT provide triage until those questions are answered.
Otherwise, provide full triage.
"""

        LANGUAGE_RULE = (
            "Respond in Swahili." if language == "Swahili" else "Respond in English."
        )

        contents = [compiled_prompt]
        if uploaded_image is not None:
            contents.append(uploaded_image)

        BASELINE_GUIDANCE = """
Emergency Livestock Stabilization (Offline Heuristic):
- Isolate the animal from the herd
- Provide clean, cool water
- Check for signs of fever, severe injury, or difficulty breathing
- Minimize stress (shade, quiet area)
- Contact your county veterinarian if symptoms worsen or do not improve
"""

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION + "\n" + LANGUAGE_RULE,
                )
            )

            st.session_state.chat_history.append(compiled_prompt)
            st.session_state.chat_history.append(response.text)

            def extract_severity(text: str) -> str:
                match = re.search(r"##\s*Severity\s*\n(LOW|MEDIUM|HIGH)", text, re.IGNORECASE)
                if match:
                    return match.group(1).upper()
                return "UNKNOWN"

            severity = extract_severity(response.text)

            def get_severity_color(text: str) -> str:
                upper = text.upper()
                if "HIGH" in upper:
                    return "red"
                elif "MEDIUM" in upper:
                    return "orange"
                else:
                    return "green"

            color = get_severity_color(response.text)

            RISK_MAP = {
                "LOW": 25,
                "MEDIUM": 60,
                "HIGH": 90,
                "UNKNOWN": 50,
            }
            risk_score = RISK_MAP.get(severity, 50)

            st.session_state.last_response_text = response.text
            st.session_state.last_severity = severity
            st.session_state.last_color = color
            st.session_state.last_risk_score = risk_score

            if "?" not in response.text:
                st.session_state.cases.append(
                    {
                        "livestock": livestock_type,
                        "symptom": symptom,
                        "severity": severity,
                    }
                )

            st.success("Analysis Complete")
            st.metric("AI-Derived Risk Index (Heuristic)", f"{risk_score}/100")
            st.markdown("### Severity Indicator")
            st.markdown(f":{color}[⬤]")
            st.markdown(response.text)

            if severity == "HIGH" and "?" not in response.text:
                contact = VET_CONTACTS.get(county, "Contact nearest county vet office.")
                st.error(f"🚨 Emergency Contact: {contact}")

            total_cases = len(st.session_state.cases)
            high_cases = sum(1 for c in st.session_state.cases if c["severity"] == "HIGH")

            st.subheader("Session-Based Herd Monitoring (Prototype)")
            st.write(f"Total Cases This Session: {total_cases}")
            st.write(f"High Risk Cases: {high_cases}")

            def detect_outbreak(cases):
                filtered = [
                    c["symptom"] for c in cases
                    if c["severity"] in ["MEDIUM", "HIGH"]
                ]
                counts = Counter(filtered)
                for s, count in counts.items():
                    if count >= 3:
                        return s
                return None

            outbreak = detect_outbreak(st.session_state.cases)
            if outbreak:
                st.error(f"🚨 Possible outbreak pattern detected: {outbreak}")
        except Exception:
            st.error("⚠️ Network issue detected.")
            st.info(BASELINE_GUIDANCE)

# Latest assessment block: redraw + follow-up form when model asked questions
if st.session_state.last_response_text:
    st.divider()
    st.subheader("Latest assessment")
    txt = st.session_state.last_response_text
    risk = st.session_state.last_risk_score
    color = st.session_state.last_color
    severity = st.session_state.last_severity
    st.metric("AI-Derived Risk Index (Heuristic)", f"{risk}/100")
    st.markdown("### Severity Indicator")
    st.markdown(f":{color}[⬤]")
    st.markdown(txt)
    if severity == "HIGH" and "?" not in txt:
        contact = VET_CONTACTS.get(county, "Contact nearest county vet office.")
        st.error(f"🚨 Emergency Contact: {contact}")

    if "?" in txt:
        st.caption("Answer the questions above so we can complete the triage.")
        with st.form("follow_up_form"):
            follow_up_answer = st.text_area(
                "Your answers",
                placeholder="E.g.: 1. Yes, still drinking. 2. No discharge seen.",
                help="Reply to each question in order. Short answers are fine.",
            )
            submitted = st.form_submit_button("Submit follow-up answers")
        if submitted and follow_up_answer.strip():
            with st.spinner("Completing triage..."):
                follow_up_message = "Farmer's additional information:\n" + follow_up_answer.strip()
                st.session_state.chat_history.append(follow_up_message)
                conv = "\n\n---\n\n".join(st.session_state.chat_history)
                LANGUAGE_RULE = (
                    "Respond in Swahili." if language == "Swahili" else "Respond in English."
                )
                try:
                    response2 = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=conv,
                        config=genai.types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION + "\n" + LANGUAGE_RULE,
                        ),
                    )
                    st.session_state.chat_history.append(response2.text)
                    st.session_state.last_response_text = response2.text
                    sev = re.search(r"##\s*Severity\s*\n(LOW|MEDIUM|HIGH)", response2.text, re.IGNORECASE)
                    st.session_state.last_severity = sev.group(1).upper() if sev else "UNKNOWN"
                    st.session_state.last_color = "red" if "HIGH" in response2.text.upper() else "orange" if "MEDIUM" in response2.text.upper() else "green"
                    st.session_state.last_risk_score = {"LOW": 25, "MEDIUM": 60, "HIGH": 90}.get(st.session_state.last_severity, 50)
                    if "?" not in response2.text:
                        st.session_state.cases.append({
                            "livestock": livestock_type,
                            "symptom": symptom,
                            "severity": st.session_state.last_severity,
                        })
                    st.rerun()
                except Exception:
                    st.error("⚠️ Network issue. Please try again.")
        elif submitted and not follow_up_answer.strip():
            st.warning("Please type your answers before submitting.")

st.divider()
# Reset conversation and case list for a new animal
if st.button("🔄 Clear session & start new case"):
    st.session_state.chat_history = []
    st.session_state.cases = []
    st.session_state.last_response_text = None
    st.session_state.last_severity = None
    st.session_state.last_color = None
    st.session_state.last_risk_score = None
    st.rerun()
