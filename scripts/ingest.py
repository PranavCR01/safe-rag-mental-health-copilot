import json, faiss, numpy as np, tiktoken, os, yaml
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

CORPUS = "data/corpus.jsonl"
VEC_PATH = "storage/vectordb.faiss"
META_PATH = "storage/meta.npy"
SRC_MAP = "data/sources.yaml"

def embed(texts):
    # text-embedding-3-small is cheap/good; switch to large if needed
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in resp.data]).astype("float32")

def main():
    rows, texts = [], []
    with open(CORPUS, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line); rows.append(r); texts.append(r["text"])
    X = embed(texts)
    index = faiss.IndexFlatIP(X.shape[1])
    faiss.normalize_L2(X)
    index.add(X)
    os.makedirs("storage", exist_ok=True)
    faiss.write_index(index, VEC_PATH)
    np.save(META_PATH, np.array(rows, dtype=object))
    # copy sources for runtime
    with open(SRC_MAP,"r",encoding="utf-8") as f: yaml.safe_load(f)  # sanity check
    print(f"Ingested {len(rows)} chunks.")

if __name__ == "__main__": main()
