import json
import urllib.request

BASE = "http://127.0.0.1:8000"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as response:
        return json.loads(response.read().decode())

if __name__ == "__main__":
    print("Health:", get("/api/health"))
    print("Ollama:", get("/api/ollama/status"))
    print("Projects:", get("/api/projects"))
