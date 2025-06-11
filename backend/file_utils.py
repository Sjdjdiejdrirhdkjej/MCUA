import os
from pathlib import Path
import re

# Define the root directory for CUA files.
# Ensure this directory is created when the application starts or as needed.
CUA_DIR = Path("CUA")

def is_filename_safe(filename: str) -> bool:
    """
    Checks if the filename is safe:
    - Not empty
    - Does not contain '..'
    - Does not contain '/' or '\' (to prevent path traversal)
    - Consists of reasonably safe characters (alphanumeric, underscore, hyphen, dot)
    """
    if not filename:
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    # Allow alphanumeric, underscores, hyphens, and dots.
    # Disallow filenames starting with a dot (like .bashrc) for now for simplicity,
    # unless explicitly handled.
    if not re.match(r"^[a-zA-Z0-9_.-]+$", filename) or filename.startswith('.'):
        return False
    return True

def write_cua_file(filename: str, content: str) -> tuple[bool, str]:
    """
    Writes content to a file within the CUA_DIR.
    Performs basic security checks on the filename.
    """
    if not is_filename_safe(filename):
        return False, "Error: Invalid filename. Filenames must be simple, without paths or '..'."

    try:
        CUA_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CUA_DIR / filename

        # Additional check to ensure the resolved path is still within CUA_DIR
        # (Path.resolve() can be used, but `is_filename_safe` should largely cover this for simple names)
        if not file_path.resolve().is_relative_to(CUA_DIR.resolve()):
             return False, "Error: Filename results in path outside designated directory."

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, f"File '{filename}' written successfully to CUA directory."
    except IOError as e:
        return False, f"Error writing file: {e}"
    except Exception as e: # Catch any other unexpected errors
        return False, f"An unexpected error occurred while writing file: {e}"

def read_cua_file(filename: str) -> tuple[str | None, str]:
    """
    Reads content from a file within the CUA_DIR.
    Performs basic security checks on the filename.
    """
    if not is_filename_safe(filename):
        return None, "Error: Invalid filename. Filenames must be simple, without paths or '..'."

    try:
        # CUA_DIR.mkdir(parents=True, exist_ok=True) # Ensure directory exists if attempting to read (optional here, as write creates it)
        file_path = CUA_DIR / filename

        if not file_path.resolve().is_relative_to(CUA_DIR.resolve()):
             return None, "Error: Filename results in path outside designated directory."

        if file_path.exists() and file_path.is_file():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content, f"Content of '{filename}':"
        else:
            return None, f"Error: File '{filename}' not found in CUA directory."
    except IOError as e:
        return None, f"Error reading file: {e}"
    except Exception as e:
        return None, f"An unexpected error occurred while reading file: {e}"
