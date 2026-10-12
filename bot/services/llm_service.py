import io
import logging
import os
import tempfile

import pdfplumber

from config.llm import get_llm_client
from config.settings import BOT_LANG

logger = logging.getLogger(__name__)

# Язык ответа LLM — берём из BOT_LANG
RESPONSE_LANG = {
    "ru": "Russian",
    "en": "English",
    "lo": "Lao",
    "th": "Thai",
}.get(BOT_LANG, "English")

SUMMARY_PROMPT = """\
You are an HR assistant preparing a concise, evidence-based candidate summary for a recruiter.

Vacancy:
{vacancy}

Candidate answers:
{candidate_data}

{resume_section}

Write a concise summary in {response_lang}.

Include:
- Overall fit for the vacancy, based only on available evidence.
- 1-2 relevant strengths supported by the candidate's answers or resume.
- One material risk, mismatch, or missing piece of information. If none can be established, state that there is insufficient information to identify one.
- 1-2 specific questions worth asking at the interview.

Rules:
- Write 3-5 sentences in total.
- Do not use headings, bullet points, greetings, or introductory phrases.
- Do not invent facts, qualifications, employment history, salary benchmarks, or language proficiency.
- Clearly distinguish confirmed facts from assumptions.
- Assess salary expectations against the vacancy's stated salary range only if both are available. Otherwise, state that the comparison cannot be made.
- Mention age or location only when directly relevant to an explicit job requirement or work arrangement.
- If information is missing, say so briefly instead of guessing.
- Avoid generic praise, corporate jargon, and repetitive wording.
- Use the resume and candidate answers together. If they conflict, mention the discrepancy rather than choosing one version.
- Return only the summary, with no explanations about these instructions.
"""

RESUME_SECTION_TEMPLATE = """\
Resume content:
{resume_text}
"""


def extract_text_from_pdf(file_bytes: bytes) -> str | None:
    """Извлекает текст из PDF через pdfplumber."""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages).strip()
            return text if text else None
    except Exception as e:
        logger.warning(f"PDF extract failed: {e}")
        return None


def extract_text_from_docx(file_bytes: bytes) -> str | None:
    """
    Извлекает текст из DOCX/DOC.
    Сначала пробует python-docx (для .docx),
    затем docx2txt (справляется и со старым .doc).
    """
    # Попытка 1: python-docx
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs).strip()
        if text:
            return text
    except Exception as e:
        logger.debug(f"python-docx failed: {e}")

    # Попытка 2: docx2txt (работает и с бинарным .doc)
    try:
        import docx2txt
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            text = docx2txt.process(tmp_path).strip()
            return text if text else None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        logger.warning(f"DOCX extract failed (both methods): {e}")
        return None


async def download_telegram_file(bot, file_id: str) -> tuple[bytes, str] | None:
    """
    Скачивает файл из Telegram по file_id.
    Возвращает (bytes, filename) или None при ошибке.
    """
    try:
        tg_file = await bot.get_file(file_id)
        file_path = tg_file.file_path
        filename = file_path.split("/")[-1].lower()

        file_bytes = await bot.download_file(file_path)
        if hasattr(file_bytes, "read"):
            file_bytes = file_bytes.read()

        return file_bytes, filename
    except Exception as e:
        logger.warning(f"Failed to download Telegram file {file_id}: {e}")
        return None


async def extract_resume_text(bot, file_id: str) -> str | None:
    """
    Скачивает файл резюме из Telegram и извлекает текст.
    Поддерживает PDF, DOCX и старый DOC.
    """
    result = await download_telegram_file(bot, file_id)
    if not result:
        return None

    file_bytes, filename = result

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename.endswith((".docx", ".doc")):
        return extract_text_from_docx(file_bytes)
    else:
        logger.info(f"Unsupported resume format: {filename}")
        return None


async def generate_candidate_summary(
    candidate_data: dict,
    vacancy_title: str = "",
    bot=None,
    resume_file_id: str | None = None,
) -> str | None:
    """
    Генерирует AI-summary кандидата.
    Если передан bot + resume_file_id — скачивает и анализирует резюме.
    Если резюме ссылка или нет файла — анализирует только анкету.
    """
    client, model = get_llm_client()

    # ── Данные анкеты ────────────────────────────────────────
    lines = []
    if candidate_data.get("location"):
        lines.append(f"Location: {candidate_data['location']}")
    if candidate_data.get("age"):
        lines.append(f"Age: {candidate_data['age']}")
    if candidate_data.get("languages"):
        lines.append(f"Languages: {candidate_data['languages']}")
    if candidate_data.get("experience"):
        lines.append(f"Experience: {candidate_data['experience']}")
    if candidate_data.get("salary_amount"):
        currency = candidate_data.get("salary_currency", "")
        lines.append(f"Salary expectation: {candidate_data['salary_amount']} {currency}".strip())
    if candidate_data.get("start_date"):
        lines.append(f"Available from: {candidate_data['start_date']}")
    if candidate_data.get("work_type"):
        lines.append(f"Work type: {candidate_data['work_type']}")

    # ── Резюме-файл (если есть) ──────────────────────────────
    resume_section = ""
    if bot and resume_file_id:
        resume_text = await extract_resume_text(bot, resume_file_id)
        if resume_text:
            truncated = resume_text[:3000]
            if len(resume_text) > 3000:
                truncated += "\n[... truncated ...]"
            resume_section = RESUME_SECTION_TEMPLATE.format(resume_text=truncated)
            logger.info(f"Resume text extracted: {len(resume_text)} chars")
        else:
            logger.info("Resume file found but text extraction failed (possibly image-based PDF or unsupported format)")

    prompt = SUMMARY_PROMPT.format(
        vacancy=vacancy_title or "not specified",
        candidate_data="\n".join(lines) if lines else "No data",
        resume_section=resume_section,
        response_lang=RESPONSE_LANG,
    )


    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3,
        )

        if not response.choices:
            logger.error(
                "LLM returned no choices. Model=%s, response=%r",
                model, response,
            )
            return None

        choice = response.choices[0]
        raw = choice.message.content

        logger.info(
            "LLM response: model=%s, finish_reason=%s, content=%r",
            model, choice.finish_reason, raw,
        )

        if not raw or not raw.strip():
            logger.error(
                "LLM returned empty summary. Model=%s, finish_reason=%s",
                model, choice.finish_reason,
            )
            return None

        return raw.strip()

    except Exception:
        logger.exception("LLM summary generation failed. Model=%s", model)
        return None
