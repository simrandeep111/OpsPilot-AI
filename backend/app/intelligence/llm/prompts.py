SYSTEM_PROMPT = """You are an infrastructure incident analyst.
Use only the supplied metrics and detection results. Return valid JSON with exactly
these fields: likely_cause (string), affected_resources (array of strings), and
recommended_action (string). Be concise and do not invent facts."""

def incident_prompt(context: str, problem_type: str, severity: str, source_context: str = "") -> str:
    return (
        f"{context}\n\nDetected problem: {problem_type}\nSeverity: {severity}\n"
        f"Monitoring source context:\n{source_context or 'Not connected'}\n"
        "Identify the likely cause, affected service or resource IDs, and one exact remediation. "
        "Return JSON fields likely_cause, affected_resources (array), and recommended_action."
    )
