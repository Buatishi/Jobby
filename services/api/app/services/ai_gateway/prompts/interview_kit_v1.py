from typing import Any

SYSTEM_PROMPT = (
    "Actuás como Recruiter Senior, Hiring Manager, Career Coach y Consultor de "
    "Preparación para Entrevistas con experiencia en el mercado latinoamericano. "
    "Generás un Kit de Entrevista personalizado y accionable. Lenguaje: español "
    "rioplatense, coloquial profesional. Sé específico con evidencia real del CV. "
    "Respondé ÚNICAMENTE con JSON válido."
)


def build_user_prompt(
    *,
    nombre: str,
    cv_text: str,
    skills: list[dict[str, Any]],
    experiences: list[dict[str, Any]],
    company_name: str,
    job_title: str,
    job_description: str,
    company_data_or_no_disponible: dict[str, Any] | str,
    interviewer_name: str,
    interviewer_role: str,
    role_type: str,
    background_summary: str,
) -> str:
    return (
        "CANDIDATO:\n"
        f"- Nombre: {nombre}\n"
        f"- CV (texto): {cv_text}\n"
        f"- Skills confirmadas: {skills}\n"
        f"- Experiencias: {experiences}\n\n"
        "PUESTO:\n"
        f"- Empresa: {company_name}\n"
        f"- Título: {job_title}\n"
        f"- Descripción: {job_description}\n\n"
        "EMPRESA (LinkedIn):\n"
        f"{company_data_or_no_disponible}\n\n"
        "ENTREVISTADOR (LinkedIn):\n"
        f"- Nombre: {interviewer_name}\n"
        f"- Rol: {interviewer_role} ({role_type})\n"
        f"- Background: {background_summary}\n\n"
        "Generá el JSON con estas claves exactas:\n"
        "overall_summary, compatibility_areas, strengths, risks, argumentario, "
        "model_answers, candidate_questions, action_plan\n\n"
        "Schema esperado:\n"
        "{\n"
        '  "overall_summary": "string",\n'
        '  "compatibility_areas": ['
        '{"name": "string", "score": 0, "notes": "string"}],\n'
        '  "strengths": [{"title": "string", "evidence": "string"}],\n'
        '  "risks": [{"title": "string", "mitigation": "string"}],\n'
        '  "argumentario": ["string"],\n'
        '  "model_answers": [{"question": "string", "answer": "string", '
        '"evaluation_criteria": ["string"]}],\n'
        '  "candidate_questions": ["string"],\n'
        '  "action_plan": {"title": "string", "steps": ["string"]}\n'
        "}"
    )
