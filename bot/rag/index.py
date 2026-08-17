import os
import chromadb
import cohere
from db.models import Vacancy, VacancyTranslation
from db.session import SessionLocal

chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_or_create_collection(
    name="jobs",
    metadata={"hnsw:space": "cosine"}
)
co = cohere.Client(os.getenv("COHERE_API_KEY"))

BOT_LANG = os.getenv("BOT_LANG", "en")


def _embed(texts: list[str], input_type: str = "search_document") -> list[list[float]]:
    response = co.embed(
        texts=texts,
        model="embed-multilingual-v3.0",
        input_type=input_type,
    )
    return response.embeddings


def rebuild_index():
    """Переиндексирует вакансии на языке BOT_LANG из .env."""
    with SessionLocal() as session:
        # Берём активные вакансии с переводом на текущий язык
        rows = (
            session.query(Vacancy, VacancyTranslation)
            .outerjoin(
                VacancyTranslation,
                (VacancyTranslation.vacancy_id == Vacancy.id) &
                (VacancyTranslation.lang == BOT_LANG)
            )
            .filter(Vacancy.is_active == True)
            .all()
        )
        vac_list = []
        for v, tr in rows:
            title       = tr.title       if tr else v.title
            description = tr.description if tr else v.description
            vac_list.append((v.id, title, description))

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    if not vac_list:
        print(f"RAG [{BOT_LANG}]: no vacancies, index is empty")
        return

    texts = [f"{title}\n{desc or ''}" for _, title, desc in vac_list]
    embeddings = _embed(texts)

    for i, (vid, title, _) in enumerate(vac_list):
        collection.add(
            ids=[str(vid)],
            embeddings=[embeddings[i]],
            documents=[texts[i]],
            metadatas=[{"title": title, "lang": BOT_LANG}]
        )

    print(f"RAG [{BOT_LANG}]: indexed {len(vac_list)} vacancies")


def upsert_vacancy(vacancy: Vacancy):
    """Обновляет/добавляет вакансию в индекс на текущем языке."""
    with SessionLocal() as session:
        tr = session.query(VacancyTranslation).filter_by(
            vacancy_id=vacancy.id, lang=BOT_LANG
        ).first()
    title       = tr.title       if tr else vacancy.title
    description = tr.description if tr else vacancy.description

    text = f"{title}\n{description or ''}"
    embedding = _embed([text])[0]
    collection.upsert(
        ids=[str(vacancy.id)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"title": title, "lang": BOT_LANG}]
    )


def delete_vacancy(vacancy_id: int):
    collection.delete(ids=[str(vacancy_id)])


def search_vacancies(query: str, n_results: int = 5) -> list[dict]:
    count = collection.count()
    if count == 0:
        return []
    n_results = min(n_results, count)

    query_embedding = _embed([query], input_type="search_query")[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    vacancies = []
    for i, job_id in enumerate(results["ids"][0]):
        score = 1 - results["distances"][0][i]
        if score >= 0.5:
            vacancies.append({
                "vacancy_id": int(job_id),
                "title":      results["metadatas"][0][i]["title"],
                "score":      score,
            })
    return vacancies