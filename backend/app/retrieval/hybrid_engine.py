# backend/app/retrieval/hybrid_engine.py
import os
import glob
import re
from typing import List
import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer
from app.schemas.interview import RubricChunk

class HybridRAGEngine:
    def __init__(self, collection_name: str = "interview_knowledge"):
        # 1. Load local Embedding Model (Dense) & Cross-Encoder (Reranker)
        print("Loading Embedding & Cross-Encoder models...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        # 2. Initialize Ephemeral/Local Chroma Vector Store
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
        
        # 3. In-memory store for BM25 corpus
        self.chunks_store: List[dict] = []
        self.bm25: BM25Okapi | None = None

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizer that preserves code identifiers, camelCase, and technical terms."""
        return re.findall(r"\w+", text.lower())

    def ingest_chunks(self, raw_documents: List[dict], chunk_size: int = 120, overlap: int = 25):
        """
        raw_documents: List of {"source": "filename_or_repo_path", "content": "text"}
        Splits by word windows with overlap and indexes into both ChromaDB and BM25.
        """
        new_ids, new_texts, new_metadatas = [], [], []

        for doc in raw_documents:
            words = doc["content"].split()
            step = max(1, chunk_size - overlap)
            for i in range(0, len(words), step):
                chunk_text = " ".join(words[i : i + chunk_size])
                if len(chunk_text.strip()) < 20:
                    continue
                chunk_id = f"{doc['source']}#chunk_{len(self.chunks_store)}"
                chunk_record = {
                    "chunk_id": chunk_id,
                    "source": doc["source"],
                    "content": chunk_text
                }
                self.chunks_store.append(chunk_record)
                new_ids.append(chunk_id)
                new_texts.append(chunk_text)
                new_metadatas.append({"source": doc["source"]})

        if new_texts:
            embeddings = self.embedder.encode(new_texts).tolist()
            self.collection.upsert(
                ids=new_ids,
                documents=new_texts,
                embeddings=embeddings,
                metadatas=new_metadatas
            )

        # Rebuild BM25 index across all stored chunks
        tokenized_corpus = [self._tokenize(c["content"]) for c in self.chunks_store]
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def load_rubrics_directory(self, directory_path: str):
        """Loads all .md files from data/rubrics/ into the hybrid index."""
        docs = []
        for file_path in glob.glob(os.path.join(directory_path, "*.md")):
            with open(file_path, "r", encoding="utf-8") as f:
                docs.append({
                    "source": f"rubric:{os.path.basename(file_path)}",
                    "content": f.read()
                })
        self.ingest_chunks(docs)
        print(f"Indexed {len(self.chunks_store)} chunks from {len(docs)} rubric files.")

    def retrieve_and_rerank(self, query: str, top_k_initial: int = 10, top_k_final: int = 3) -> List[RubricChunk]:
        """
        Executes Parallel Dense + BM25 Search -> Reciprocal Rank Fusion (RRF) -> Cross-Encoder Reranking.
        Returns full telemetry metadata for each chunk.
        """
        if not self.chunks_store:
            return []

        n_docs = min(top_k_initial, len(self.chunks_store))

        # --- A. Dense Vector Search (ChromaDB) ---
        query_embedding = self.embedder.encode([query]).tolist()
        dense_results = self.collection.query(query_embeddings=query_embedding, n_results=n_docs)
        dense_ids = dense_results["ids"][0] if dense_results["ids"] else []
        vector_ranks = {cid: rank + 1 for rank, cid in enumerate(dense_ids)}

        # --- B. Sparse Lexical Search (BM25) ---
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        ranked_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:n_docs]
        bm25_ranks = {self.chunks_store[idx]["chunk_id"]: rank + 1 for rank, idx in enumerate(ranked_bm25_indices)}

        # --- C. Reciprocal Rank Fusion (RRF, k=60) ---
        rrf_k = 60
        candidate_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
        rrf_scores = {}
        for cid in candidate_ids:
            score = 0.0
            if cid in vector_ranks:
                score += 1.0 / (rrf_k + vector_ranks[cid])
            if cid in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[cid])
            rrf_scores[cid] = score

        # Sort candidates by RRF score
        sorted_candidate_ids = sorted(candidate_ids, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k_initial]
        id_to_chunk = {c["chunk_id"]: c for c in self.chunks_store}
        candidates = [id_to_chunk[cid] for cid in sorted_candidate_ids]

        # --- D. Cross-Encoder Reranking ---
        pairs = [[query, c["content"]] for c in candidates]
        ce_scores = self.reranker.predict(pairs)

        reranked_chunks: List[RubricChunk] = []
        for c, ce_score in zip(candidates, ce_scores):
            cid = c["chunk_id"]
            reranked_chunks.append(
                RubricChunk(
                    chunk_id=cid,
                    source=c["source"],
                    content=c["content"],
                    bm25_rank=bm25_ranks.get(cid),
                    vector_rank=vector_ranks.get(cid),
                    rerank_score=round(float(ce_score), 4)
                )
            )

        # Sort by Cross-Encoder score descending and take Top-K
        reranked_chunks.sort(key=lambda x: x.rerank_score, reverse=True)
        return reranked_chunks[:top_k_final]