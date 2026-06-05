import os
import glob as glob_module
from datetime import datetime


def _resolve_path(path: str) -> str:
    base = os.path.abspath(os.getcwd())
    joined = os.path.normpath(os.path.join(base, path))
    if not joined.startswith(base):
        raise PermissionError(f"Access denied: path '{path}' is outside the workspace")
    return joined


def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: Relative path to the file from the workspace root
    """
    full = _resolve_path(path)
    if not os.path.isfile(full):
        return f"Error: File not found at '{path}'"
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        return f"Error: '{path}' is a binary file and cannot be read as text"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates the file if it doesn't exist.

    Args:
        path: Relative path to the file from the workspace root
        content: Text content to write to the file
    """
    full = _resolve_path(path)
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{path}'"
    except Exception as e:
        return f"Error writing file: {e}"


def append_file(path: str, content: str) -> str:
    """Append content to the end of an existing file.

    Args:
        path: Relative path to the file from the workspace root
        content: Text content to append
    """
    full = _resolve_path(path)
    if not os.path.isfile(full):
        return f"Error: File not found at '{path}'"
    try:
        with open(full, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully appended {len(content)} characters to '{path}'"
    except Exception as e:
        return f"Error appending to file: {e}"


def list_directory(path: str = ".") -> str:
    """List files and directories in a given path.

    Args:
        path: Relative directory path from the workspace root (default: root)
    """
    full = _resolve_path(path)
    if not os.path.isdir(full):
        return f"Error: Directory not found at '{path}'"
    try:
        entries = sorted(os.listdir(full))
        if not entries:
            return f"Directory '{path}' is empty"
        result = [f"Contents of '{path}/':"]
        for entry in entries:
            entry_path = os.path.join(full, entry)
            size = ""
            if os.path.isfile(entry_path):
                size = f" ({os.path.getsize(entry_path)} bytes)"
            elif os.path.isdir(entry_path):
                size = " (dir)"
            result.append(f"  {entry}{size}")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {e}"


def delete_file(path: str) -> str:
    """Delete a file or empty directory.

    Args:
        path: Relative path to the file or directory from the workspace root
    """
    full = _resolve_path(path)
    if not os.path.exists(full):
        return f"Error: Path not found at '{path}'"
    try:
        if os.path.isfile(full):
            os.remove(full)
            return f"Successfully deleted file '{path}'"
        elif os.path.isdir(full):
            os.rmdir(full)
            return f"Successfully deleted empty directory '{path}'"
        return f"Error: Unknown path type at '{path}'"
    except OSError as e:
        return f"Error deleting '{path}': {e}"
    except Exception as e:
        return f"Error: {e}"


def get_file_info(path: str) -> str:
    """Get metadata about a file or directory.

    Args:
        path: Relative path from the workspace root
    """
    full = _resolve_path(path)
    if not os.path.exists(full):
        return f"Error: Path not found at '{path}'"
    try:
        stat = os.stat(full)
        kind = "directory" if os.path.isdir(full) else "file"
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"Path: {path}\n"
            f"Type: {kind}\n"
            f"Size: {stat.st_size} bytes\n"
            f"Modified: {mtime}\n"
            f"Permissions: {oct(stat.st_mode)[-3:]}"
        )
    except Exception as e:
        return f"Error: {e}"


def search_files(pattern: str) -> str:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., "*.txt", "src/**/*.py")
    """
    try:
        base = os.path.abspath(os.getcwd())
        matches = glob_module.glob(pattern, root_dir=base, recursive=True)
        matches = [m for m in matches if os.path.isfile(os.path.join(base, m))]
        if not matches:
            return f"No files found matching '{pattern}'"
        result = [f"Files matching '{pattern}':"]
        for m in sorted(matches):
            size = os.path.getsize(os.path.join(base, m))
            result.append(f"  {m} ({size} bytes)")
        return "\n".join(result)
    except Exception as e:
        return f"Error searching files: {e}"
