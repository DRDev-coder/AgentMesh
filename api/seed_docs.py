import json
import requests

def seed():
    with open('/app/data/product_docs.json') as f:
        docs = json.load(f)

    for doc in docs:
        try:
            resp = requests.post(
                'http://chromadb:8000/api/v1/collections/product_docs/documents',
                json={'ids': [doc['id']], 'documents': [doc['text']]},
                timeout=10
            )
            print(f"Seeded: {doc['id']} — {resp.status_code}")
        except Exception as e:
            print(f"Failed to seed {doc['id']}: {e}")

if __name__ == "__main__":
    seed()
