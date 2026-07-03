print("[INDEX] import started", flush=True)
import chromadb
print("[INDEX] chromadb ok", flush=True)
from sentence_transformers import SentenceTransformer
print("[INDEX] sentence_transformers ok", flush=True)
from db.models import Vacancy
print("[INDEX] db.models ok", flush=True)
from db.session import SessionLocal
print("[INDEX] db.session ok", flush=True)
print("[INDEX] import ended", flush=True)

# Инициализация
chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_or_create_collection(
    name="jobs",
    metadata={"hnsw:space": "cosine"}
)
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def rebuild_index():
    """Загружает все активные вакансии из Postgres в ChromaDB"""
    with SessionLocal() as session:
        vacancies = session.query(Vacancy).filter_by(is_active=True).all()
        vac_list = [(v.id, v.title, v.description) for v in vacancies]

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    for vid, title, description in vac_list:
        text = f"{title}\n{description}"
        embedding = embedder.encode(text).tolist()
        collection.add(
            ids=[str(vid)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"title": title}]
        )

    print(f"RAG: проиндексировано {len(vac_list)} вакансий")


def upsert_vacancy(vacancy: Vacancy):
    text = f"{vacancy.title}\n{vacancy.description}"
    embedding = embedder.encode(text).tolist()
    collection.upsert(
        ids=[str(vacancy.id)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"title": vacancy.title}]
    )


def delete_vacancy(vacancy_id: int):
    collection.delete(ids=[str(vacancy_id)])


def search_vacancies(query: str, n_results: int = 5) -> list[dict]:
    query_embedding = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    vacancies = []
    for i, job_id in enumerate(results["ids"][0]):
        score = 1 - results["distances"][0][i]
        if score >= 0.4:
            vacancies.append({
                "vacancy_id": int(job_id),
                "title": results["metadatas"][0][i]["title"],
                "score": score
            })

    return vacancies