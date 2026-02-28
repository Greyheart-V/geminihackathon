import streamlit as st
import os
import re
from collections import Counter
from google import genai
from dotenv import load_dotenv

# 1. Load your API Key (Streamlit Cloud: use Secrets; local: use .env)
load_dotenv()
try:
    api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
except Exception:
    api_key = None
if not api_key:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY in Secrets (Cloud) or .env (local).")

# 2. Initialize the Gemini Client
client = genai.Client(api_key=api_key)

# Initialize conversation history and session cases
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "cases" not in st.session_state:
    st.session_state.cases = []

# 3. The AI Cage (System Instructions)
SYSTEM_INSTRUCTION = """
You are a livestock triage assistant for Kenyan smallholder farmers.

SCOPE:
- Friesian dairy cows
- Poultry (layers and broilers)
- Kenyan smallholder conditions

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

# 4. The User Interface (Streamlit)
st.set_page_config(page_title="Livestock Early Warning System", page_icon="🐄")
st.title("Kenya Livestock Early Warning & Risk Monitoring System")
st.write("Preliminary diagnostic assistant for Friesian cows and poultry, focused on early risk detection.")
st.warning(
    "⚠️ This tool provides preliminary livestock triage only. "
    "It does NOT replace a licensed veterinarian."
)

with st.expander("📞 Emergency Vet Guidance (Kenya)"):
    st.write(
        "If symptoms are severe, contact your nearest veterinary officer "
        "or county livestock extension office immediately."
    )

# 5. The Guardrails (Dropdowns to prevent user error)
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
    livestock_type = st.selectbox("Livestock Type", ["Friesian Cow", "Poultry (Layers)", "Poultry (Broilers)"])
with col2:
    age_stage = st.selectbox("Age/Stage", ["Calf / Hatchling", "Heifer / Grower", "Milking / Laying", "Incubation"])

symptom = st.selectbox("Primary Symptom", ["Lethargy / Weakness", "Drop in Production", "Abnormal Droppings", "Off-Feed", "Respiratory Issues"])
extra_details = st.text_area("Additional Details (Optional)", placeholder="E.g., Started 2 days ago...")

county = st.selectbox(
    "Your County",
    ["Nairobi", "Kiambu", "Nakuru", "Other"],
)

uploaded_image = st.file_uploader(
    "Upload image of the animal (optional)",
    type=["jpg", "jpeg", "png"],
)

# 6. The Execution Logic
if st.button("Analyze Symptoms"):
    with st.spinner("Analyzing symptoms..."):

        conversation_context = "\n".join(st.session_state.chat_history)

        # Secretly compile the user's choices into a clean prompt
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
            # Send to Gemini 2.5 Flash
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

            # Track cases for this session
            st.session_state.cases.append(
                {
                    "livestock": livestock_type,
                    "symptom": symptom,
                    "severity": severity,
                }
            )

            # Risk index based on severity
            RISK_MAP = {
                "LOW": 25,
                "MEDIUM": 60,
                "HIGH": 90,
                "UNKNOWN": 50,
            }
            risk_score = RISK_MAP.get(severity, 50)

            st.success("Analysis Complete")
            st.metric("AI-Derived Risk Index (Heuristic)", f"{risk_score}/100")
            st.markdown("### Severity Indicator")
            st.markdown(f":{color}[⬤]")
            st.markdown(response.text)

            # Simple flow indicator if more info is needed
            if "?" in response.text:
                st.info("Additional information required before full triage.")

            if severity == "HIGH":
                contact = VET_CONTACTS.get(county, "Contact nearest county vet office.")
                st.error(f"🚨 Emergency Contact: {contact}")

            # Session-based herd dashboard
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
