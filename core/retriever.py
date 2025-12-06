#core/retriever.py
import os, json, yaml, faiss, numpy as np
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

INDEX = faiss.read_index("storage/vectordb.faiss")
META = np.load("storage/meta.npy", allow_pickle=True)
SOURCES = {s["id"]: s["url"] for s in yaml.safe_load(open("data/sources.yaml","r",encoding="utf-8"))}

def embed(q:str):
    v = client.embeddings.create(model="text-embedding-3-small", input=[q]).data[0].embedding
    x = np.array(v, dtype="float32"); faiss.normalize_L2(x.reshape(1,-1)); return x

def search(query: str, k=4):
    x = embed(query)
    D,I = INDEX.search(x.reshape(1,-1), k)
    hits = []
    for i in I[0]:
        if i < 0:
            continue
        obj = META[i]                     # this is already a dict
        row = dict(obj)                   # make a shallow copy so we can add url
        row["url"] = SOURCES.get(row["source_id"], "")
        hits.append(row)
    return hits
