import chromadb
from pathlib import Path

client = chromadb.PersistentClient(path="./chroma_db")
try:
    client.delete_collection("it_kb")
except: pass
collection = client.create_collection("it_kb")

for path in Path("knowledge_base").glob("*.md"):
    collection.add(
        documents=[path.read_text()],
        ids=[path.stem],
        metadatas=[{"category": path.stem}]
    )
    print(f"Loaded: {path.name}")
print("Done.")