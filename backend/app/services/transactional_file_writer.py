
import os
import shutil
import tempfile

from pathlib import Path, PurePosixPath


class TransactionalFileWriter:

    ALLOWED_EXTENSIONS = {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".css",
        ".json",
        ".html",
        ".md",
        ".txt",
        ".toml",
        ".yaml",
        ".yml",
        ".sql",
    }

    def _safe_target(
        self,
        workspace: Path,
        relative_path: str,
    ) -> Path:

        if not isinstance(relative_path, str):
            raise ValueError("Invalid file path.")

        normalized = relative_path.replace("\\", "/")
        relative = PurePosixPath(normalized)

        if (
            not normalized.strip()
            or relative.is_absolute()
            or ".." in relative.parts
            or ":" in normalized
        ):
            raise ValueError(f"Unsafe file path: {relative_path}")

        if not relative.parts:
            raise ValueError("Empty file path.")

        if relative.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File extension not allowed: {relative_path}"
            )

        root = workspace.resolve()
        target = root.joinpath(*relative.parts)

        current = root

        for part in relative.parts:

            current = current / part

            if current.is_symlink():
                raise ValueError(
                    f"Symbolic links are not allowed: {relative_path}"
                )

        if not target.resolve(strict=False).is_relative_to(root):
            raise ValueError(
                f"File escapes project workspace: {relative_path}"
            )

        return target

    def _restore_backup(
        self,
        target: Path,
        backup_path: Path,
    ):

        if not backup_path.is_file():
            raise RuntimeError(
                f"Backup file is missing: {backup_path}"
            )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fd, temp_name = tempfile.mkstemp(
            prefix=".restore_",
            dir=str(target.parent),
        )

        os.close(fd)

        restore_path = Path(temp_name)

        try:

            shutil.copy2(
                backup_path,
                restore_path,
            )

            os.replace(
                restore_path,
                target,
            )

        finally:
            restore_path.unlink(missing_ok=True)

    def apply(
        self,
        workspace: Path,
        backup_directory: Path,
        changes: list[dict],
    ) -> list[dict]:

        workspace = workspace.resolve()

        backup_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        prepared = []
        staged = []
        applied = []
        seen_paths = set()

        # Validate every operation before changing any file.
        for change in changes:

            if not isinstance(change, dict):
                raise ValueError("Invalid change entry.")

            relative_path = change.get("path")
            action = change.get("action")
            content = change.get("content")

            if not isinstance(relative_path, str):
                raise ValueError("Every change needs a valid path.")

            normalized = relative_path.replace("\\", "/")
            relative = PurePosixPath(normalized)
            normalized = relative.as_posix()

            if normalized in seen_paths:
                raise ValueError(
                    f"Duplicate repair path: {normalized}"
                )

            seen_paths.add(normalized)

            if action not in {"create", "update", "delete"}:
                raise ValueError(
                    f"Unsupported repair action: {action}"
                )

            if action in {"create", "update"}:

                if not isinstance(content, str) or not content.strip():
                    raise ValueError(
                        f"File content is missing: {normalized}"
                    )

            target = self._safe_target(
                workspace,
                normalized,
            )

            exists = target.is_file()

            if target.exists() and not exists:
                raise ValueError(
                    f"Target is not a regular file: {normalized}"
                )

            if action == "create" and exists:
                raise ValueError(
                    f"Cannot create existing file: {normalized}"
                )

            if action in {"update", "delete"} and not exists:
                raise ValueError(
                    f"Cannot {action} missing file: {normalized}"
                )

            prepared.append({
                "path": normalized,
                "action": action,
                "target": target,
                "content": content,
            })

        try:

            # Stage new file contents and backups first.
            for index, item in enumerate(prepared):

                target = item["target"]

                backup_path = None
                temp_path = None

                if item["action"] in {"update", "delete"}:

                    backup_path = (
                        backup_directory / Path(item["path"])
                    )

                    if backup_path.exists():
                        raise RuntimeError(
                            f"Backup already exists: {backup_path}"
                        )

                    backup_path.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    shutil.copy2(
                        target,
                        backup_path,
                    )

                if item["action"] in {"create", "update"}:

                    target.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    fd, temp_name = tempfile.mkstemp(
                        prefix=".repair_",
                        suffix=target.suffix,
                        dir=str(target.parent),
                    )

                    temp_path = Path(temp_name)

                    with os.fdopen(
                        fd,
                        "w",
                        encoding="utf-8",
                        newline="",
                    ) as file:

                        file.write(item["content"])
                        file.flush()
                        os.fsync(file.fileno())

                staged.append({
                    **item,
                    "temp_path": temp_path,
                    "backup_path": backup_path,
                })

            # Apply all staged changes.
            for item in staged:

                action = item["action"]
                target = item["target"]

                if action in {"create", "update"}:

                    os.replace(
                        item["temp_path"],
                        target,
                    )

                elif action == "delete":

                    target.unlink()

                applied.append(item)

            return [
                {
                    "path": item["path"],
                    "action": item["action"],
                    "backup": (
                        str(item["backup_path"])
                        if item["backup_path"]
                        else None
                    ),
                }
                for item in applied
            ]

        except Exception:

            # Restore files changed in this batch.
            rollback_errors = []

            for item in reversed(applied):

                target = item["target"]
                action = item["action"]

                try:

                    if action == "create":

                        target.unlink(missing_ok=True)

                    elif action in {"update", "delete"}:

                        self._restore_backup(
                            target,
                            item["backup_path"],
                        )

                except Exception as rollback_error:

                    rollback_errors.append(
                        f"{item['path']}: {rollback_error}"
                    )

            if rollback_errors:
                raise RuntimeError(
                    "File operation failed and rollback was incomplete: "
                    + "; ".join(rollback_errors)
                )

            raise

        finally:

            for item in staged:

                temp_path = item.get("temp_path")

                if temp_path:
                    temp_path.unlink(missing_ok=True)

    def rollback(
        self,
        workspace: Path,
        changes: list[dict],
    ):

        workspace = workspace.resolve()
        errors = []

        for change in reversed(changes):

            try:

                target = self._safe_target(
                    workspace,
                    change["path"],
                )

                action = change["action"]
                backup = change.get("backup")

                if action == "create":

                    target.unlink(missing_ok=True)

                elif action in {"update", "delete"}:

                    if not backup:
                        raise RuntimeError(
                            f"No backup recorded for {change['path']}"
                        )

                    self._restore_backup(
                        target,
                        Path(backup),
                    )

            except Exception as error:

                errors.append(
                    f"{change.get('path')}: {error}"
                )

        if errors:
            raise RuntimeError(
                "Rollback failed: " + "; ".join(errors)
            )


transactional_file_writer = TransactionalFileWriter()
