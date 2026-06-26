"""
AI Analysis Service — uses Claude Vision to assess construction site photos.
Teaching note: When AI_DEMO_MODE=true in .env, this returns realistic
fake data so you can test the full flow without an API key or internet.
Switch to AI_DEMO_MODE=false and add your ANTHROPIC_API_KEY to use real AI.
"""
import os, base64, json, random
from pathlib import Path


def analyse_image(image_path: str) -> dict:
    """Analyse a construction site photo and return risk assessment."""
    demo_mode = os.getenv("AI_DEMO_MODE", "true").lower() == "true"
    if demo_mode:
        return _demo_analysis()
    return _real_analysis(image_path)


def _real_analysis(image_path: str) -> dict:
    """Call Claude Vision API for real analysis."""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env file")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    suffix = Path(image_path).suffix.lower().lstrip(".")
    media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                      "png": "image/png", "webp": "image/webp"}
    media_type = media_type_map.get(suffix, "image/jpeg")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": media_type, "data": image_data}},
                {"type": "text", "text": """You are a Nigerian construction safety inspector
trained in LASBCA regulations. Analyse this construction site photo.

Return ONLY valid JSON (no markdown, no explanation):
{
  "risk_level": "safe" | "monitor" | "high_risk" | "critical",
  "risk_score": 0-100,
  "summary": "2-3 sentence overall assessment",
  "violations": ["list of specific safety violations observed"],
  "recommendations": ["list of corrective actions required"]
}"""}
            ]
        }]
    )

    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _demo_analysis() -> dict:
    """Return demo analysis data for testing without API key."""
    scenarios = [
        {
            "risk_level": "safe",
            "risk_score": 15.0,
            "summary": "The construction site demonstrates good safety practices. Workers are wearing appropriate PPE and scaffolding appears properly secured. The site is well-organised with clear safety signage.",
            "violations": [],
            "recommendations": ["Continue current safety protocols", "Schedule routine inspection next month"],
        },
        {
            "risk_level": "monitor",
            "risk_score": 42.0,
            "summary": "The site shows moderate safety compliance. Some workers lack proper head protection and material storage could be better organised. Overall risk is manageable with prompt corrective action.",
            "violations": ["Two workers without hard hats in active construction zone", "Building materials stored unsafely near edge without barriers"],
            "recommendations": ["Enforce mandatory hard hat policy immediately", "Install edge barriers around material storage areas", "Conduct toolbox safety talk with all site workers"],
        },
        {
            "risk_level": "high_risk",
            "risk_score": 71.0,
            "summary": "Significant safety hazards detected. Scaffolding appears structurally unsound on the eastern face and workers are operating without fall protection at heights above 3 metres. Immediate corrective action required before work continues.",
            "violations": ["Scaffolding bracing missing on east face — structural failure risk", "No fall arrest systems for workers at height", "Unsecured load-bearing equipment near site boundary", "Inadequate site fencing — public access risk"],
            "recommendations": ["HALT work on eastern scaffolding until structural inspection completed", "Install harness anchor points for all elevated work", "Secure all heavy equipment and establish exclusion zone", "Reinforce perimeter fencing before resuming operations"],
        },
        {
            "risk_level": "critical",
            "risk_score": 91.0,
            "summary": "CRITICAL safety violations detected. The structure shows signs of potential imminent collapse on the northern section. Workers are present in the danger zone without evacuation. Immediate stop-work and evacuation is strongly recommended.",
            "violations": ["Visible structural cracks in load-bearing column — imminent collapse risk", "Workers present in collapse danger zone", "No emergency evacuation plan visible", "Overloading of upper floor slab observed", "Zero PPE compliance on site"],
            "recommendations": ["EVACUATE all workers from northern section IMMEDIATELY", "Issue Stop-Work Order — do not resume until structural engineer certifies safety", "Engage licensed structural engineer for emergency assessment", "Contact LASBCA for mandatory inspection before any works resume", "Document all structural anomalies for regulatory report"],
        },
    ]
    weights = [0.35, 0.35, 0.20, 0.10]
    return random.choices(scenarios, weights=weights, k=1)[0]
