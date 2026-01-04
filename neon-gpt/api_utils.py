# ==========================================================
# api_utils.py — OpenRouter communication and output handling
# ==========================================================

import requests
import re
import time
import os


# === CONFIGURATION === #
API_KEY = "API-KEY"  # <-- Replace with your actual OpenRouter API key
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
#MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
MODEL = "deepseek/deepseek-v3.2-exp"
#MODEL = "openai/gpt-4o"
#MODEL = "mistralai/mistral-large-2512"

def extract_between_markers(text: str, start_marker: str, end_marker: str):
    """Extract all blocks between given markers."""
    pattern = re.compile(re.escape(start_marker) + r"(.*?)" + re.escape(end_marker), re.DOTALL)
    matches = pattern.findall(text)
    return [m.strip() for m in matches if m.strip()]


def save_output_to_file(content: str, filename: str):
    """Save extracted output to a text file."""
    os.makedirs("outputs", exist_ok=True)
    filepath = os.path.join("outputs", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"✅ Saved extracted output to {filepath}")
    return filepath


def send_prompt(prompt: str, persona: str, step_name: str, max_retries: int = 3, wait_time: int = 20):
    """
    Send a single stateless prompt to OpenRouter, extract between markers,
    save output to a file, and return the extracted content.
    """
    system_prompt = {
        "role": "system",
        "content": f"{persona}\n"
                   "Respond ONLY between ###start_output### and ###end_output### markers.\n"
                   "For Turtle syntax responses, use ONLY ###start_turtle### and ###end_turtle### markers.\n"
                   "Avoid explanations or text outside these markers."
    }
    user_prompt = {"role": "user", "content": prompt}

    for attempt in range(1, max_retries + 1):
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [system_prompt, user_prompt]
            }
        )

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            print(f"\n--- MODEL RESPONSE ({step_name}) ---\n{reply[:300]}...\n")
            extracted = extract_between_markers(reply, "###start_output###", "###end_output###")
            if not extracted:
                print("⚠️ No output markers found. Saving full reply instead.")
                extracted = [reply]

            # Save to file
            joined = "\n\n".join(extracted)
            filename = f"{step_name}.txt"
            save_output_to_file(joined, filename)
            return joined

        elif response.status_code == 429:
            if attempt < max_retries:
                print(f"⏳ Rate limit hit (429). Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print("❌ Max retry attempts reached due to rate limiting.")
                return None

        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

def load_ontology_as_context(ontology_file: str) -> str:
    """Load the current full ontology .ttl file as text for LLM context."""
    try:
        with open(ontology_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""