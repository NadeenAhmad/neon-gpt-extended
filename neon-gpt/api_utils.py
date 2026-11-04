# ==========================================================
# api_utils.py — LLM provider communication and output handling
# ==========================================================

import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


# === DEFAULT CONFIGURATION === #
API_KEY = None
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.getenv("NEON_MODEL") or os.getenv("MODEL") or "deepseek/deepseek-v3.2-exp"


def load_runtime_config(env_path: str = ".env") -> dict:
    """Load environment variables from a local .env file without extra dependencies."""
    env_file = Path(env_path)
    from dotenv import load_dotenv
    loaded = False
    if env_file.exists():
        loaded = load_dotenv(env_file)
        if loaded:
            print(f"✅ Loaded runtime config from {env_path}")
        else:
            print(f"⚠️ Failed to load runtime config from {env_path}. Using existing environment variables.")
    else:
        print(f"⚠️ No .env file found at {env_path}. Using existing environment variables.")
    return dict(os.environ)


def resolve_llm_config(
    provider: str = None,
    model: str = None,
    api_key: str = None,
    api_base: str = None,
    api_version: str = None,
):
    """Resolve LLM connection settings from provider-specific env vars and runtime args."""
    load_runtime_config()
    provider_name = (provider or os.getenv("NEON_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()
    if provider_name not in {"openrouter", "openai", "azure"}:
        raise ValueError(
            "Unsupported LLM provider. Use one of: openrouter, openai, azure. "
            "Set NEON_LLM_PROVIDER or pass provider=..."
        )

    if provider_name == "openrouter":
        resolved_api_key = api_key or os.getenv("NEON_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")
        resolved_api_base = api_base or os.getenv("NEON_API_BASE") or os.getenv("OPENROUTER_API_URL") or os.getenv("OPENROUTER_BASE_URL") or OPENROUTER_API_URL
        resolved_model = model or os.getenv("NEON_MODEL") or os.getenv("OPENROUTER_MODEL") or os.getenv("MODEL") or MODEL
    elif provider_name == "openai":
        resolved_api_key = api_key or os.getenv("NEON_API_KEY") or os.getenv("OPENAI_API_KEY")
        resolved_api_base = api_base or os.getenv("NEON_API_BASE") or os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1/chat/completions"
        resolved_model = model or os.getenv("NEON_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-4o-mini"
    else:
        resolved_api_key = api_key or os.getenv("NEON_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY")
        base_url = api_base or os.getenv("NEON_API_BASE") or os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_API_BASE") or os.getenv("AZURE_OPENAI_BASE_URL")
        if not base_url:
            raise ValueError(
                "Azure endpoint is missing. Set AZURE_OPENAI_ENDPOINT or pass api_base=."
            )

        base_url = base_url.rstrip("/")
        deployment_name = (
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_MODEL")
            or os.getenv("NEON_MODEL")
            or os.getenv("MODEL")
            or "gpt-4o-mini"
        )

        if "/openai/deployments/" not in base_url:
            base_url = f"{base_url}/openai/deployments/{deployment_name}"
        if not base_url.endswith("/chat/completions"):
            base_url = f"{base_url}/chat/completions"

        resolved_api_base = base_url
        api_version_value = api_version or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-10-21"
        parsed = urlparse(resolved_api_base)
        params = parse_qsl(parsed.query, keep_blank_values=True)
        params = [(key, value) for key, value in params if key.lower() != "api-version"]
        params.append(("api-version", api_version_value))
        resolved_api_base = urlunparse(parsed._replace(query=urlencode(params)))
        resolved_model = model or deployment_name

    if not resolved_api_key:
        raise ValueError(
            f"No API key found for provider '{provider_name}'. "
            "Set the relevant env var such as OPENROUTER_API_KEY, OPENAI_API_KEY, "
            "AZURE_OPENAI_API_KEY or NEON_API_KEY."
        )

    return {
        "provider": provider_name,
        "model": resolved_model,
        "api_key": resolved_api_key,
        "api_base": resolved_api_base,
    }


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


def send_prompt(
    prompt: str,
    persona: str,
    step_name: str,
    model: str = None,
    max_retries: int = 3,
    wait_time: int = 20,
    provider: str = None,
    api_key: str = None,
    api_base: str = None,
    api_version: str = None,
    timeout: int = 120,
):
    """
    Send a single prompt to a provider-agnostic chat completion endpoint,
    extract between markers, save output to a file, and return the extracted content.
    """
    config = resolve_llm_config(
        provider=provider,
        model=model,
        api_key=api_key,
        api_base=api_base,
        api_version=api_version,
    )

    system_prompt = {
        "role": "system",
        "content": f"{persona}\n"
                   "Respond ONLY between ###start_output### and ###end_output### markers.\n"
                   "For Turtle syntax responses, use ONLY ###start_turtle### and ###end_turtle### markers.\n"
                   "Avoid explanations or text outside these markers."
    }
    user_prompt = {"role": "user", "content": prompt}
    payload = {
        "model": config["model"],
        "messages": [system_prompt, user_prompt],
    }

    if config["provider"] == "azure":
        headers = {
            "Content-Type": "application/json",
            "api-key": config["api_key"],
        }
    else:
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }

    for attempt in range(1, max_retries + 1):
        response = requests.post(config["api_base"], headers=headers, json=payload, timeout=timeout)

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            print(f"\n--- MODEL RESPONSE ({step_name}) ---\n{reply[:300]}...\n")
            extracted = extract_between_markers(reply, "###start_output###", "###end_output###")
            if not extracted:
                print("⚠️ No output markers found. Saving full reply instead.")
                extracted = [reply]

            joined = "\n\n".join(extracted)
            filename = f"{step_name}.txt"
            save_output_to_file(joined, filename)
            return joined

        elif response.status_code == 429:
            if attempt < max_retries:
                print(f"⏳ Rate limit hit (429). Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
                continue
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