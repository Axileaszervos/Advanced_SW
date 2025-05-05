import argparse
import sys

print("""
Welcome to the GitHub Markdown Translation Tool using LLMs (OpenAI or Gemini).

You can translate Markdown files from a public GitHub repository branch using either OpenAI or Gemini models.

❯ You will be asked to provide:
  - LLM provider (e.g. openai or gemini)
  - API key (e.g. sk-... or AIza...)
  - Model name (e.g. gpt-3.5-turbo or gemini-1.5-pro-latest)

❯ After translation:
  - You'll review and optionally edit the output.
  - Press double Enter to accept edits.
  - Translations are saved locally and committed to Git.

Example (CLI):
  python translation.py --provider openai --api_key sk-... --model gpt-3.5-turbo
""")

def get_llm_client():
    parser = argparse.ArgumentParser(
        description=(
    "Translation tool for Markdown files from a GitHub repository using LLMs (OpenAI or Gemini).\n\n"
    "You can provide the following arguments via command line or enter them interactively when prompted:\n"
    "  --provider      LLM provider (openai or gemini)\n"
    "  --api_key       API key for the selected provider\n"
    "  --model         Model name (e.g. gpt-3.5-turbo or gemini-1.5-pro-latest)\n\n"
    "Example usage:\n"
    "  python translation.py --provider openai --api_key sk-... --model gpt-3.5-turbo\n"
    "  python translation.py --provider gemini --api_key AIza... --model gemini-1.5-pro-latest\n\n"
    "During execution, the script will:\n"
    "  1. Fetch .md files from the specified GitHub repository\n"
    "  2. Translate the content using the selected LLM\n"
    "  3. Prompt you to optionally edit the translation\n\n"
    "To accept or finish editing the translated text, press **double Enter**.\n"
),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--provider", type=str, help="LLM provider (openai or gemini)")
    parser.add_argument("--api_key", type=str, help="API key for the provider")
    parser.add_argument("--model", type=str, help="Model name (e.g. gpt-3.5-turbo or gemini-1.5-pro-latest)")
    args, _ = parser.parse_known_args()

    provider = (args.provider or input("Enter provider (openai or gemini): ")).strip().lower()
    api_key = args.api_key or input("Enter API key: ").strip()
    model = args.model or input("Enter model name: ").strip()

    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("Missing dependency: pip install openai")
        client = OpenAI(api_key=api_key)
        return {"provider": "openai", "client": client, "model": model}

    elif provider == "gemini":
        try:
            from google.ai.generativelanguage_v1 import GenerativeServiceClient
            from google.ai.generativelanguage_v1.types import Content, Part
            from google.api_core.client_options import ClientOptions
        except ImportError:
            sys.exit("Missing dependency: pip install --upgrade google-ai-generativelanguage")

        model_name = f"models/{model}" if not model.startswith("models/") else model
        client = GenerativeServiceClient(
            client_options=ClientOptions(
                api_key=api_key,
                api_endpoint="generativelanguage.googleapis.com"
            )
        )
        return {
            "provider": "gemini",
            "client": client,
            "model": model_name,
            "Content": Content,
            "Part": Part
        }

    else:
        sys.exit("Unsupported provider. Choose 'openai' or 'gemini'.")
