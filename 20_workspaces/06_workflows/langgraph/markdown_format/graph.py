from typing import List
from .nodes import format_markdown_with_lmstudio

def run_markdown_format_workflow(files: List[str], model: str = "qwen/qwen3.6-27b", in_place: bool = False, output_dir: str = None) -> None:
    """
    Format one or more markdown files using LM Studio and the formatting prompt.
    Args:
        files: List of file paths to format.
        model: Model name for LM Studio.
        in_place: If True, overwrite files. If False, write to output_dir.
        output_dir: Directory to write formatted files if not in_place.
    """
    for file_path in files:
        formatted = format_markdown_with_lmstudio(file_path, model=model)
        if in_place:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(formatted)
        else:
            import os
            out_dir = output_dir or "formatted_markdown"
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, os.path.basename(file_path))
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(formatted)
