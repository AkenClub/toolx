import json
import os
import tempfile


def atomic_write_json(file_path, data, indent=4):
    """Write JSON through a same-directory temporary file and atomic replace."""
    target_path = os.path.abspath(os.fspath(file_path))
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="." + os.path.basename(target_path) + ".",
            suffix=".tmp",
            dir=directory,
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, indent=indent, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, target_path)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
