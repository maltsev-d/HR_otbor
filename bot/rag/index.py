import os
import chromadb
import cohere
from db.models import Vacancy
from db.session import SessionLocal

chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_or_create_collection(
    name="jobs",
    metadata={"hnsw:space": "cosine"}
)
co = cohere.Client(os.getenv("COHERE_API_KEY"))


def _embed(texts: list[str]) -> list[list[float]]:
    response = co.embed(
        texts=texts,
        model="embed-multilingual-v3.0",
        input_type="search_document",
    )
    return response.embeddings


def rebuild_index():
    with SessionLocal() as session:
        vacancies = session.query(Vacancy).filter_by(is_active=True).all()
        vac_list = [(v.id, v.title, v.description) for v in vacancies]

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    if not vac_list:
        print("RAG: вакансий нет, индекс пуст")
        return

    texts = [f"{title}\n{desc or ''}" for _, title, desc in vac_list]
    embeddings = _embed(texts)

    for i, (vid, title, _) in enumerate(vac_list):
        collection.add(
            ids=[str(vid)],
            embeddings=[embeddings[i]],
            documents=[texts[i]],
            metadatas=[{"title": title}]
        )

    print(f"RAG: проиндексировано {len(vac_list)} вакансий")


def upsert_vacancy(vacancy: Vacancy):
    text = f"{vacancy.title}\n{vacancy.description or ''}"
    embedding = _embed([text])[0]
    collection.upsert(
        ids=[str(vacancy.id)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"title": vacancy.title}]
    )


def delete_vacancy(vacancy_id: int):
    collection.delete(ids=[str(vacancy_id)])


def search_vacancies(query: str, n_results: int = 5) -> list[dict]:
    response = co.embed(
        texts=[query],
        model="embed-multilingual-v3.0",
        input_type="search_query",
    )
    query_embedding = response.embeddings[0]

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
                "title": results["metadatas"][0][i]["title"],
                "score": score
            })

    return vacancies