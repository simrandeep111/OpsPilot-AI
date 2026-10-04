SYSTEM_PROMPT = """You are an infrastructure incident analyst.
Use only the supplied metrics and detection results. Return valid JSON with exactly
these fields: likely_cause (string), affected_resources (array of strings), and
recommended_action (string). Be concise and do not invent facts."""

def incident_prompt(context: str, problem_type: str, severity: str, aws_context: str = "") -> str:
    return (
        f"{context}\n\nDetected problem: {problem_type}\nSeverity: {severity}\n"
        f"AWS read-only inventory:\n{aws_context or 'Not connected'}\n"
        "Identify the likely cause, affected AWS resource IDs, and one exact remediation. "
        "Return JSON fields likely_cause, affected_resources (array), and recommended_action."
    )
