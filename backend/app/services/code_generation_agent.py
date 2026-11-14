
import json
from typing import Any

from app.services.ollama_service import ollama_service
from app.schemas.code_generation import (
    CodeGenerationResult,
    GeneratedFile,
)


class CodeGenerationAgent:

    MAX_RETRIES = 3

    # Generate a small number of files per Ollama request.
    FILE_BATCHES = [
        [
            "backend/app/main.py",
            "backend/app/database.py",
        ],
        [
            "backend/app/models.py",
            "backend/app/schemas.py",
        ],
        [
            "backend/app/routes/products.py",
        ],
        [
            "frontend/package.json",
            "frontend/src/main.tsx",
            "frontend/src/index.css",
        ],
        [
            "frontend/src/App.tsx",
        ],
    ]

    ALLOWED_EXTENSIONS = {
        ".py",
        ".tsx",
        ".ts",
        ".css",
        ".json",
    }

    async def generate_code(
        self,
        architecture,
        instructions=None,
    ) -> CodeGenerationResult:

        architecture_data = architecture.architecture_result

        if isinstance(architecture_data, str):
            architecture_data = json.loads(architecture_data)

        if hasattr(architecture_data, "model_dump"):
            architecture_data = architecture_data.model_dump()

        if not isinstance(architecture_data, dict):
            raise ValueError(
                "Architecture data must be a valid dictionary."
            )

        # Generate each batch independently.
        all_generated_files = []
        summaries = []

        for batch_number, file_paths in enumerate(
            self.FILE_BATCHES,
            start=1,
        ):

            print(
                f"Generating batch {batch_number}/"
                f"{len(self.FILE_BATCHES)}: {file_paths}"
            )

            batch_result = await self._generate_batch(
                architecture_data=architecture_data,
                instructions=instructions,
                requested_files=file_paths,
                batch_number=batch_number,
            )

            all_generated_files.extend(
                batch_result["generated_files"]
            )

            batch_summary = batch_result.get("summary", "")

            if batch_summary:
                summaries.append(batch_summary)

        # Validate the complete generated project.
        result = CodeGenerationResult.model_validate(
            {
                "summary": " ".join(summaries),
                "generated_files": all_generated_files,
            }
        )

        self._validate_generated_files(result.generated_files)

        expected_files = {
            path
            for batch in self.FILE_BATCHES
            for path in batch
        }

        actual_files = {
            file.path.replace("\\", "/")
            for file in result.generated_files
        }

        missing_files = expected_files - actual_files

        if missing_files:
            raise ValueError(
                "Code generation incomplete. Missing files: "
                + ", ".join(sorted(missing_files))
            )

        if len(actual_files) != len(result.generated_files):
            raise ValueError(
                "Duplicate generated file paths detected."
            )

        print(
            f"Code generation completed successfully. "
            f"Total files: {len(result.generated_files)}"
        )

        return result

    async def _generate_batch(
        self,
        architecture_data: dict,
        instructions: str | None,
        requested_files: list[str],
        batch_number: int,
    ) -> dict[str, Any]:

        project_overview = architecture_data.get(
            "project_overview",
            "",
        )

        system_architecture = architecture_data.get(
            "system_architecture",
            {},
        )

        database_design = architecture_data.get(
            "database_design",
            {},
        )

        api_design = architecture_data.get(
            "api_design",
            {},
        )

        project_structure = architecture_data.get(
            "project_structure",
            {},
        )

        architecture_context = f"""
PROJECT OVERVIEW:
{project_overview}

SYSTEM ARCHITECTURE:
{json.dumps(system_architecture, indent=2)}

DATABASE DESIGN:
{json.dumps(database_design, indent=2)}

API DESIGN:
{json.dumps(api_design, indent=2)}

PROJECT STRUCTURE:
{json.dumps(project_structure, indent=2)}
"""

        requested_files_text = "\n".join(
            f"- {path}" for path in requested_files
        )

        prompt = f"""
You are an expert Python and React software developer.

Generate complete source code for the requested files.

PROJECT ARCHITECTURE:
{architecture_context}

ADDITIONAL INSTRUCTIONS:
{instructions or "Follow the architecture and create a minimal working application."}

TECHNOLOGY RULES:
- Python and FastAPI for the backend.
- SQLite and SQLAlchemy for database operations.
- React and TypeScript for the frontend.
- Do not use Django.
- Do not introduce a Node.js backend.
- Use consistent model, schema, and API field names.
- Keep code simple and modular.
- Do not generate passwords, API keys, or real credentials.
- Do not execute generated code.
- Do not use placeholder implementations.
- Include necessary imports.
- Do not omit important function implementations.
- Use synchronous SQLAlchemy consistently unless explicitly configured otherwise.
- Use Pydantic response schemas, not SQLAlchemy models, as FastAPI response models.

FILES TO GENERATE IN THIS BATCH:
{requested_files_text}

IMPORTANT OUTPUT RULES:
1. Generate ONLY the files listed in this batch.
2. Include every requested file.
3. Each file must contain complete source code.
4. Keep the source code concise but functional.
5. Do not include Markdown code fences.
6. Do not include explanations outside JSON.
7. Escape quotation marks and newlines correctly.
8. Return valid JSON only.

REQUIRED JSON FORMAT:

{{
    "summary": "Short description of this batch",
    "generated_files": [
        {{
            "path": "exact requested file path",
            "language": "python or typescript or json or css",
            "description": "Description of the file",
            "content": "Complete source code"
        }}
    ]
}}
"""

        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):

            try:
                current_prompt = prompt

                if attempt > 1:
                    current_prompt += f"""

RETRY INSTRUCTIONS:
Your previous response was invalid or incomplete.

Previous error:
{last_error}

Generate a shorter and simpler implementation.
Do not omit any requested file.
Ensure every JSON string is properly escaped.
Return valid JSON only.
"""

                response = await ollama_service.generate_json(
                    current_prompt
                )

                data = self._parse_json_response(response)

                if not isinstance(data, dict):
                    raise ValueError(
                        "Expected a JSON object from the model."
                    )

                if "generated_files" not in data:
                    raise ValueError(
                        "Response does not contain generated_files."
                    )

                if not isinstance(data["generated_files"], list):
                    raise ValueError(
                        "generated_files must be a JSON array."
                    )

                batch_result = {
                    "summary": data.get("summary", ""),
                    "generated_files": data["generated_files"],
                }

                # Validate generated file objects.
                validated_files = []

                for item in batch_result["generated_files"]:
                    generated_file = GeneratedFile.model_validate(item)
                    validated_files.append(generated_file)

                batch_result["generated_files"] = validated_files

                self._validate_generated_files(validated_files)

                expected = set(requested_files)

                actual = {
                    file.path.replace("\\", "/")
                    for file in validated_files
                }

                if actual != expected:
                    missing = expected - actual
                    unexpected = actual - expected

                    raise ValueError(
                        f"Batch file mismatch. "
                        f"Missing: {sorted(missing)}. "
                        f"Unexpected: {sorted(unexpected)}."
                    )

                print(
                    f"Batch {batch_number} succeeded "
                    f"on attempt {attempt}."
                )

                return batch_result

            except Exception as error:
                last_error = str(error)

                print(
                    f"Batch {batch_number}, "
                    f"attempt {attempt}/{self.MAX_RETRIES} failed: "
                    f"{last_error}"
                )

        raise ValueError(
            f"Code generation failed for batch {batch_number} "
            f"after {self.MAX_RETRIES} attempts. "
            f"Files: {requested_files}. "
            f"Last error: {last_error}"
        )

    @staticmethod
    def _parse_json_response(response: Any) -> dict:

        if isinstance(response, dict):
            return response

        if not isinstance(response, str):
            raise ValueError(
                "Ollama returned an unsupported response type."
            )

        text = response.strip()

        if not text:
            raise ValueError(
                "Ollama returned an empty response."
            )

        # Remove Markdown fences if the model accidentally adds them.
        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        # Locate and decode the first JSON object.
        start = text.find("{")

        if start == -1:
            raise ValueError(
                "No JSON object found in Ollama response."
            )

        decoder = json.JSONDecoder()

        try:
            data, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid or incomplete JSON response: {error}"
            ) from error

        if not isinstance(data, dict):
            raise ValueError(
                "Ollama response must contain a JSON object."
            )

        return data

    def _validate_generated_files(
        self,
        generated_files: list[GeneratedFile],
    ) -> None:

        for file in generated_files:

            path = file.path.replace("\\", "/")
            parts = path.split("/")

            # Reject absolute paths and directory traversal.
            if (
                path.startswith("/")
                or ".." in parts
                or ":" in path
                or not path
            ):
                raise ValueError(
                    f"Unsafe generated file path: {file.path}"
                )

            extension = "." + path.rsplit(".", 1)[-1]

            if extension not in self.ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported generated file extension: "
                    f"{file.path}"
                )

            if not file.content or not file.content.strip():
                raise ValueError(
                    f"Empty source code: {file.path}"
                )


code_generation_agent = CodeGenerationAgent()
