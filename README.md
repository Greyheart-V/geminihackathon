# Kenya Livestock Early Warning & Risk Monitoring System

**This project is an MVP.** It is a prototype for preliminary livestock triage only. It does not replace a licensed veterinarian. Data (e.g. session case counts and risk scores) is for demonstration and is not medical or diagnostic.

---

## What problem it addresses

Many smallholder farmers in Kenya have limited or delayed access to veterinary care. When an animal shows symptoms, knowing whether to act immediately, what to do first, and when to escalate can be unclear. This MVP helps bridge that gap by offering **preliminary** triage and stabilization guidance so farmers can take safer first steps while seeking or waiting for professional care.

## What the app does

- **Triage by symptom:** The farmer selects livestock type (Friesian cow, layers, broilers), age/stage, primary symptom, and optional details. Optional photo upload is supported; image-based assessment is explicitly framed as potentially inaccurate.
- **Structured output:** The assistant returns a likely issue, severity (LOW / MEDIUM / HIGH), immediate care steps, and when to call a vet. It does not give drug dosages and favors low-cost, locally relevant advice.
- **Follow-up questions:** If information is insufficient, the assistant asks a small number of targeted questions before giving full triage, so the flow stays controlled.
- **Language:** Responses can be in English or Swahili.
- **County vet hint:** For high severity, the app shows a county-based emergency contact hint (Nairobi, Kiambu, Nakuru, or “contact nearest county vet”).
- **Session-only herd view:** Within a single browser session, the app tracks cases and shows total and high-risk counts. If the same symptom appears multiple times at MEDIUM/HIGH severity, it may flag a possible outbreak pattern. **This is session-based only and is not persistent or validated data.**
- **Risk index:** A simple heuristic risk score (e.g. 25 / 60 / 90) is derived from the stated severity. It is labeled as an AI-derived heuristic, not a clinical or diagnostic measure.
- **Offline fallback:** If the network or API fails, the app shows a short list of general stabilization steps (isolate, water, monitor, contact vet if worsening) so the farmer still gets basic guidance.

The app is built with Streamlit and uses the Gemini API for the triage responses.

---

## Running locally

From the project root, with a virtual environment activated and dependencies installed from `requirements.txt`:

`streamlit run code/app.py`

Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in a `.env` file in the `code` folder (or in your environment). Do not commit `.env` or any file containing the key.

---

## Deploying with Streamlit (e.g. Streamlit Community Cloud)

- Point the deployment at this repository.
- Set the **main file path** to `code/app.py`.
- Add the Gemini API key in the deployment secrets (e.g. `GOOGLE_API_KEY` or `GEMINI_API_KEY` as used in the app).
- The app will install dependencies from the root `requirements.txt`.

---

## MVP disclaimer

This is a minimum viable product. Scope is limited to Friesian dairy cows and poultry (layers and broilers) in a Kenyan smallholder context. The risk index, session dashboard, and outbreak-style alert are heuristic and for illustration only. Always treat professional veterinary advice as authoritative.
