# ==========================================================
# api_utils.py — LLM communication and output handling
# ==========================================================

import requests
import re
import time
import os


# === CONFIGURATION === #
# Set these environment variables before running the scripts:
#   LLM_API_KEY   your API key (OPENROUTER_API_KEY also works)
#   LLM_MODEL     the model, as your provider names it (optional)
#   LLM_API_URL   an OpenAI-compatible chat completions endpoint (optional)
# The defaults are the setup used in the paper: OpenRouter, DeepSeek V3.2.
# Other models used in the paper (OpenRouter names): openai/gpt-4o,
# mistralai/mistral-large-2512, meta-llama/llama-4-maverick-17b-128e-instruct.
# Examples of other endpoints:
#   OpenAI:        https://api.openai.com/v1/chat/completions   (LLM_MODEL=gpt-4o)
#   Ollama, local: http://localhost:11434/v1/chat/completions   (no key needed)
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-v3.2-exp"


def llm_settings():
    """Return (url, model, key) from the environment."""
    url = os.environ.get("LLM_API_URL") or DEFAULT_API_URL
    model = os.environ.get("LLM_MODEL") or DEFAULT_MODEL
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not key and "openrouter.ai" in url:
        raise RuntimeError("No API key found. Set LLM_API_KEY (or OPENROUTER_API_KEY) to your OpenRouter key.")
    return url, model, key


def describe_llm() -> str:
    """The model and endpoint in use, for logs (never the key)."""
    url, model, _ = llm_settings()
    return f"{model} at {url}"

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
    Send a single stateless prompt to the configured model, extract between markers,
    save output to a file, and return the extracted content.
    """
    url, model, key = llm_settings()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
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
            url,
            headers=headers,
            json={
                "model": model,
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