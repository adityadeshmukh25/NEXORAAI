from pathlib import Path


class GeneratedFileWriter:

    def __init__(self):
        # All generated projects stay inside this directory.
        self.workspace = (
            Path(__file__).resolve().parents[2]
            / "generated_projects"
        )

        self.workspace.mkdir(
            parents=True,
            exist_ok=True
        )

        self.allowed_extensions = {
            ".py",
            ".tsx",
            ".ts",
            ".css",
            ".json",
            ".html",
            ".md",
            ".txt"
        }

        self.max_file_size = 200 * 1024  # 200 KB

    def write_generation(self, generation):

        project_id = generation.project_id
        generation_id = generation.id

        # Create a separate folder for each generation.
        project_folder = (
            self.workspace
            / f"project_{project_id}"
            / f"generation_{generation_id}"
        )

        project_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        written_files = []
        seen_paths = set()

        for file_data in generation.generated_files:

            relative_path = Path(
                file_data["path"].replace("\\", "/")
            )

            # Reject absolute paths and directory traversal.
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError(
                    f"Unsafe file path: {relative_path}"
                )

            if not relative_path.parts:
                raise ValueError("Empty file path.")

            if ":" in str(relative_path):
                raise ValueError(
                    f"Invalid file path: {relative_path}"
                )

            if relative_path.suffix.lower() not in self.allowed_extensions:
                raise ValueError(
                    f"Unsupported file extension: {relative_path}"
                )

            normalized_path = relative_path.as_posix().lower()

            if normalized_path in seen_paths:
                raise ValueError(
                    f"Duplicate generated file: {relative_path}"
                )

            seen_paths.add(normalized_path)

            content = file_data.get("content", "")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Empty or invalid content: {relative_path}"
                )

            if len(content.encode("utf-8")) > self.max_file_size:
                raise ValueError(
                    f"File exceeds 200 KB limit: {relative_path}"
                )

            destination = project_folder / relative_path

            # Confirm that the resolved destination stays in the workspace.
            resolved_destination = destination.resolve()

            if not resolved_destination.is_relative_to(
                project_folder.resolve()
            ):
                raise ValueError(
                    f"File destination is outside workspace: {relative_path}"
                )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            destination.write_text(
                content,
                encoding="utf-8"
            )

            written_files.append(
                str(destination.relative_to(self.workspace))
            )

        return {
            "workspace": str(project_folder),
            "file_count": len(written_files),
            "files": written_files
        }


file_writer = GeneratedFileWriter()