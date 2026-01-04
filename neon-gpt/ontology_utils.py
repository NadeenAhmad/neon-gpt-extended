# ==========================================================
# ontology_utils.py — Turtle extraction and ontology handling
# ==========================================================

import re
import os
from rdflib import Graph


def init_ontology_file(domain_name: str):
    """Create or clear ontology file at start."""
    ontology_filename = f"{domain_name}_ontology.ttl"
    with open(ontology_filename, "w", encoding="utf-8") as f:
        f.write("# Generated Turtle ontology\n\n")
    print(f"🧩 Initialized ontology file: {ontology_filename}")
    return ontology_filename


def extract_and_save_turtle(response_text: str, ontology_file: str, step_name: str):
    """Extract Turtle code between markers and append to ontology file."""
    matches = re.findall(r"###start_turtle###(.*?)###end_turtle###", response_text, re.DOTALL)
    if not matches:
        print("⚠️ No Turtle code found in response.")
        return

    with open(ontology_file, "a", encoding="utf-8") as f:
        for i, block in enumerate(matches, start=1):
            cleaned = block.strip()
            if cleaned:
                f.write(f"# --- Turtle block from {step_name} ---\n")
                f.write(cleaned + "\n\n")
                print(f"✅ Appended Turtle block {i} from {step_name} to {ontology_file}")

def load_previous_output(previous_step_name: str):
    """Load text from a previous step file if it exists."""
    filepath = os.path.join("outputs", f"{previous_step_name}.txt")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def append_output(source_step: str, target_step: str):
    """Append the text output of one step file to another."""
    src_path = os.path.join("outputs", f"{source_step}.txt")
    dst_path = os.path.join("outputs", f"{target_step}.txt")
    if os.path.exists(src_path) and os.path.exists(dst_path):
        with open(src_path, "r", encoding="utf-8") as src, open(dst_path, "a", encoding="utf-8") as dst:
            dst.write("\n\n# --- Appended from step: " + source_step + " ---\n")
            dst.write(src.read())
        print(f"📎 Appended {source_step}.txt → {target_step}.txt")

