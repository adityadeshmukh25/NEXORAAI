
import httpx

from app.config import settings


class OllamaService:

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    async def check_connection(self):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.base_url}/api/tags"
                )

                response.raise_for_status()
                data = response.json()

                models = [
                    model.get("name", "")
                    for model in data.get("models", [])
                ]

                model_available = any(
                    name == self.model
                    or name.startswith(self.model + ":")
                    for name in models
                )

                return {
                    "connected": True,
                    "model": self.model,
                    "model_available": model_available,
                    "available_models": models,
                }

        except Exception as error:
            return {
                "connected": False,
                "model": self.model,
                "model_available": False,
                "error": str(error),
            }

    async def generate_json(self, prompt: str) -> str:

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "format": "json",
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0.1,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": 4096,
            },
        }

        timeout = httpx.Timeout(
            connect=15,
            read=self.timeout,
            write=60,
            pool=15,
        )

        try:
            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:

                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                response.raise_for_status()

                try:
                    result = response.json()
                except ValueError as error:
                    raise RuntimeError(
                        "Ollama returned an invalid response envelope."
                    ) from error

                if not isinstance(result, dict):
                    raise RuntimeError(
                        "Ollama returned an unexpected response format."
                    )

                # Detect output truncation.
                done_reason = result.get("done_reason")

                if done_reason == "length":
                    raise RuntimeError(
                        "Ollama stopped because it reached the output "
                        "token limit. Reduce the batch size or simplify "
                        "the generated code."
                    )

                if result.get("done") is False:
                    raise RuntimeError(
                        "Ollama response was not completed."
                    )

                message = result.get("message") or {}
                content = message.get("content", "")

                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError(
                        "Ollama returned an empty response."
                    )

                return content

        except httpx.TimeoutException as error:
            raise RuntimeError(
                f"Ollama timed out after {self.timeout} seconds. "
                "The model may be too slow or under memory pressure."
            ) from error

        except httpx.ConnectError as error:
            raise RuntimeError(
                "Cannot connect to Ollama. "
                "Check whether Ollama is running."
            ) from error

        except httpx.HTTPStatusError as error:
            raise RuntimeError(
                f"Ollama HTTP error: {error.response.status_code}. "
                f"Details: {error.response.text[:500]}"
            ) from error


ollama_service = OllamaService()
