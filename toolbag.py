import pathlib
import json
import re

CWD = pathlib.Path.cwd()
EXCLUDE_DIRS = {'.', '..', '.git', '__pycache__', 'uv.lock'}

class Toolbag:
    def __init__(self):
        self.tools = {}

    def tool(self, fn):
        assert fn.__name__ not in self.tools, f"A tool named {fn.__name__} already in bag."
        self.tools[fn.__name__] = fn
        return fn

    def unpack(self):
        return list(self.tools.values())

bag = Toolbag()

def _filename_to_path(filename):
    if ('..' in filename) or (filename.startswith('/')):
        raise Exception(f"FAILURE: {filename} starts with '/' or contains '..' but must be under the current directory.")
    p = pathlib.Path(CWD / filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _delete_empty_parents(p: pathlib.Path):
    # For parents of p upto but not including CWD
    for parent in p.relative_to(CWD).parents[-1]:
        # If dir is empty
        if not next(parent.iterdir(), None):
            parent.rmdir()

def _find_lines_in_file(p, pattern):
    matches = {}
    with p.open(mode='rt', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            # Check if the line matches the pattern
            if pattern.search(line):
                # Store line number as string for cleaner JSON keys
                matches[str(i)] = line.strip()

    return matches if matches else None

@bag.tool
def list_files():
    """Recursively lists all files in current working directory.

    Returns JSON nested dictionary representing the directory tree.
    -> {'subdir': {'file1': last_modified_time_epoch}, 'file2': last_modified_time_epoch}"""
    def recur_dirs(dir):
        tree = {}
        for p in sorted(dir.iterdir()):
            if p.is_dir() and p.name not in EXCLUDE_DIRS:
                tree[p.name] = recur_dirs(p)
            else:
                tree[p.name] = p.c.stat()['st_mtime']
    tree = recur_dirs(CWD)
    return json.dumps(tree)

@bag.tool
def find_lines_in_file(filename, pattern: re.Pattern):
    """Reads a file and finds lines matching a regex pattern.

    (filename: file to search, pattern: regex pattern) -> JSON dictionary of {line_number (str): line_content (str)}.
    """
    patt = pattern.compile()
    p = _filename_to_path(filename)
    matches = _find_lines_in_file(p, patt)

    return json.dumps(matches if matches else {})

@bag.tool
def find_lines_in_all_files(pattern: re.Pattern):
    """Searches all files in current working dir and finds lines matching a regex pattern.

    (pattern: regex pattern) -> JSON: dictionary of {'filename': {line_number (str): line_content (str)}}.
    """
    def recurse_and_search(dir, pattern):
        results = {}
        for p in dir.iterdir():
            if p.is_dir() and p.name not in EXCLUDE_DIRS:
                matches = recurse_and_search(p, pattern)
            else:
                matches = _find_lines_in_file(p, pattern)
            if matches:
                results[p.name] = matches
        if results:
            return results
        else:
            return None
    patt = pattern.compile()

    matches = recurse_and_search(CWD, patt)

    return json.dumps(matches if matches else {})

@bag.tool
def save_to_file(filename, contents):
    """Saves contents to filename.

    (filename, contents) -> success/failure.

    File is assumed to be located under the current working directory.
    Overwrites file if it exists already.
    Creates parent dirs if they do not already exist."""
    with(_filename_to_path(filename).open(mode="wt")) as f:
        f.write(contents)
    return json.dumps({"success": f"Content written to {filename}"})

@bag.tool
def read_line_numbers(filename, start_line=1, end_line=-1):
    """Reads file and returns json identifying each line by line number.

    (filename, start_line=0, end_line=-1) -> {'line_number': 'line_contents'}.
    Can limit lines returned to start_line:end_line inclusive. Defaults to returning all lines.
    Set end_line=-1 (the default) to return through end of file."""
    start_line = int(start_line)
    end_line = int(end_line)
    p = _filename_to_path(filename)
    data = {}
    with p.open(mode='rt') as f:
        for line_number, line in enumerate(f, start=1):
            if end_line > 0 and line_number > end_line:
                break
            if line_number >= start_line:
                data[str(line_number)] = line.rstrip('\n')
    return json.dumps(data)

@bag.tool
def copy_lines(src_filename, src_start_line, src_end_line, dest_filename, dest_start_line, dest_end_line):
    """Copy lines from src to dest.

    Args:
        src_filename: str
        src_start_line: int, >= 0, <= total_lines
        src_end_line: int, > start, <= total_lines, may be -1 to indicate copy through end of file
        dest_filename: str
        dest_start_line: int, >= 0, <= total_lines
        dest_end_line: int, > start, <= total_lines, may be -1 to indicate replace through end of file
    """
    src_start_line, src_end_line, dest_start_line, dest_end_line = int(src_start_line), int(src_end_line), int(dest_start_line), int(dest_end_line)
    p = _filename_to_path(src_filename)
    with p.open(mode='rt') as f:
        lines = f.readlines()

    if src_start_line < 1 or src_start_line > len(lines) + 1:
        raise Exception(f"Error: src_start line {src_start_line} is out of bounds (1 to {len(lines)}).")

    start_index = src_start_line - 1
    if src_end_line == -1:
        end_index = len(lines)
    else:
        end_index = src_end_line

    if src_end_line < src_start_line:
        raise Exception(f"Error: src_end line ({src_end_line}) cannot be before start line ({src_start_line}).")
    if src_end_line > len(lines):
        raise Exception(f"Error: src_end line {src_end_line} exceeds total lines ({len(lines)}). Use end_line=-1 to copy up to end of file.")
    replace_lines_in_file(dest_filename, dest_start_line, dest_end_line, lines[start_index:end_index])

@bag.tool
def replace_lines_in_file(filename, start_line, end_line, replacement_contents):
    """
    Replace lines in a file from start_line to end_line (inclusive) with replacement_contents.
    If end_line is -1, replace from start_line to the end of the file.
    Lines can be deleted from a file by passing an empty string as replacement_contents
    """
    p = _filename_to_path(filename)
    with p.open(mode='rt') as f:
        lines = f.readlines()

    if start_line < 1 or start_line > len(lines) + 1:
        raise Exception(f"Error: Start line {start_line} is out of bounds (1 to {len(lines)}).")

    start_index = start_line - 1
    if end_line == -1:
        end_index = len(lines)
    else:
        end_index = end_line

    if end_line < start_line:
        raise Exception(f"Error: End line ({end_line}) cannot be before start line ({start_line}).")
    if end_line > len(lines):
        raise Exception(f"Error: End line {end_line} exceeds total lines ({len(lines)}). Use end_line=-1 to replace up to end of file.")

    with p.open(mode='wt') as f:
        f.write('\n'.join(lines[:start_index]))
        if replacement_contents:
            f.write(replacement_contents)
        f.write('\n'.join(lines[end_index:]))
    return json.dumps({"success": f"Replaced lines {start_line}:{end_line} in {filename}"})

@bag.tool
def delete_file(filename):
    """Deletes filename.

    (filename) -> success/failure.
    File is assumed to be located under the current working directory."""
    p = _filename_to_path(filename).unlink()
    _delete_empty_parents(p)
    return json.dumps({"success": f"Deleted {filename} and any empty parent dirs."})

@bag.tool
def move_file(src_filename, dest_filename):
    """Moves or renames src_filename to dest_filename.

    (src_filename, dest_filename) -> success/failure.
    Files are assumed to be located under the current working directory."""
    s = _filename_to_path(src_filename)
    d = _filename_to_path(dest_filename)
    s.rename(d)
    _delete_empty_parents(s)
    return json.dumps({"success": f"Renamed {src_filename} to {dest_filename}"})