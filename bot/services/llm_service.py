import logging
from config.llm import get_llm_client


logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Кандидат на вакансию {vacancy}.
{candidate_data}

Дай краткое саммари: впечатление, 1-2 плюса, 1 вопрос для интервью. Без заголовков, 3-4 предложения."""


async def generate_candidate_summary(candidate_data: dict, vacancy_title: str = "") -> str | None:
    client, model = get_llm_client()

    # Только значимые для оценки поля
    lines = []
    if candidate_data.get("location"):
        lines.append(f"Город: {candidate_data['location']}")
    if candidate_data.get("english_level"):
        lines.append(f"Английский: {candidate_data['english_level']}")
    if candidate_data.get("salary_expectation"):
        lines.append(f"Зарплата: {candidate_data['salary_expectation']} руб.")
    if candidate_data.get("start_date"):
        lines.append(f"Выход: {candidate_data['start_date']}")
    if candidate_data.get("contract_type"):
        lines.append(f"Оформление: {candidate_data['contract_type']}")

    prompt = SUMMARY_PROMPT.format(
        vacancy=vacancy_title or "не указана",
        candidate_data="\n".join(lines),
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM summary error: {e}")
        print(f"[LLM ERROR] {e}", flush=True)
        return None