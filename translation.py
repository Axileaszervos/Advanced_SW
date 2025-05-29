import os
import requests
import subprocess
from openai import OpenAI
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from llm_client import get_llm_client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH")
MY_REPO_PATH = os.getenv("MY_REPO_PATH")
GITHUB_REMOTE_URL = os.getenv("GITHUB_REMOTE_URL")
SOURCE_LANG = os.getenv("SOURCE_LANG")
TARGET_LANG = os.getenv("TARGET_LANG")

llm = get_llm_client()

# Construct base URL to fetch raw files from GitHub
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# Create local folders if they don't exist
md_folder = "./github_md"
output_folder = "./translated"
os.makedirs(md_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Configure key bindings for multi-line input session
bindings = KeyBindings()

@bindings.add('enter', 'enter')
def _(event):
    "When double enter is pressed, end input."
    event.current_buffer.validate_and_handle()

session = PromptSession(key_bindings=bindings)

# Opens a prompt for manual editing of text
def edit_text_via_prompt_toolkit(text):
    return session.prompt("Edit the text:\n", multiline=True, default=text)

# Get a list of markdown files from the GitHub repository
def get_repo_files():
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    response = requests.get(api_url)
    if response.status_code == 200:
        tree = response.json()["tree"]
        return [file["path"] for file in tree if file["path"].endswith(".md")][:10]  # first ten files
    else:
        print(f"Error fetching files: {response.status_code}")
        return []

# Download a single file from the GitHub repository
def download_file(file_path):
    url = RAW_BASE_URL + file_path
    response = requests.get(url)
    if response.status_code == 200:
        local_path = os.path.join(md_folder, os.path.basename(file_path))
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        return local_path
    else:
        print(f"Error downloading {file_path}")
        return None

# Translate text using the selected LLM provider (OpenAI or Gemini)
def translate_text(text, user_prompt):
    full_prompt = (
        f"{user_prompt}\n\n"
        f"Translate the following text from {SOURCE_LANG} to {TARGET_LANG}."
        f"Preserve the original YAML structure, indentation, and list formatting exactly as it is.\n\n"
        f"{text}"
    )

    if llm["provider"] == "openai":
        response = llm["client"].chat.completions.create(
            model=llm["model"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt}
            ]
        )
        output = response.choices[0].message.content.strip()

    elif llm["provider"] == "gemini":
        Content, Part = llm["Content"], llm["Part"]
        response = llm["client"].generate_content(
            model=llm["model"],
            contents=[Content(parts=[Part(text=full_prompt)])]
        )
        output = response.candidates[0].content.parts[0].text.strip()

    else:
        raise ValueError("Unsupported LLM provider")

    # Clean markdown fenced code block syntax if it exists
    if output.startswith("```yaml"):
        output = output.removeprefix("```yaml").strip()
        output = output.removesuffix("```").strip()
    elif output.startswith("```"):
        output = output.removeprefix("```").strip()
        output = output.removesuffix("```").strip()

    return output

# Separate YAML front matter from the markdown body
def split_markdown_front_matter(text):
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            _, yaml_block, rest = parts
            return yaml_block.strip(), rest.lstrip()
    return text.strip(), ''

MY_REPO_PATH = os.getenv("MY_REPO_PATH")
TRANSLATED_REPO_FOLDER = os.path.join(MY_REPO_PATH, "translated")
os.makedirs(TRANSLATED_REPO_FOLDER, exist_ok=True)

# Prompt user for additional instructions to guide translation
prompt = session.prompt(
    "Provide a prompt for translating from {SOURCE_LANG} to {TARGET_LANG}.\n"
    "Prompt (double enter to confirm):\n",
    multiline=True
)

translated_files = []
files = get_repo_files()
for file in files:
    local_path = download_file(file)
    if local_path:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        yaml_part, rest_of_content = split_markdown_front_matter(content)
        translated_yaml = translate_text(yaml_part, prompt)
        translation = f"---\n{translated_yaml.strip()}\n---\n{rest_of_content}"
        print("Translation:")
        print(translation)

        # Ask user whether they want to edit the translated output
        choice = input("Would you like to edit the translation? (yes/no): ").strip().lower()
        if choice == 'yes':
            edited_text = session.prompt("Edit Translation:\n", default=translation)
            chosen_translation = edited_text
        else:
            chosen_translation = translation

        # Save translated file to output folder
        output_file = os.path.join(output_folder, os.path.basename(file))
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chosen_translation)
        print(f"Edited and saved text in {output_file}")

        # Save translated file also into the local Git repo path
        repo_output_file = os.path.join(TRANSLATED_REPO_FOLDER, os.path.basename(file))
        with open(repo_output_file, 'w', encoding='utf-8') as f:
            f.write(chosen_translation)
        print(f"Saved translated file to local repo at {repo_output_file}")

        # Add file to commit list
        translated_files.append(repo_output_file)

        if input("Do you want to proceed to the next file? (yes/no): ").lower() != 'yes':
            break

# Commit and push translated files to GitHub
if translated_files:
    try:
        subprocess.run(["git", "-C", MY_REPO_PATH, "add"] + translated_files, check=True)
        subprocess.run(["git", "-C", MY_REPO_PATH, "commit", "-m", "Add translated files"], check=True)

        # Check if remote origin is set; if not, add it
        result = subprocess.run(["git", "-C", MY_REPO_PATH, "remote"], capture_output=True, text=True)
        remotes = result.stdout.strip().splitlines()
        if "origin" not in remotes:
            subprocess.run(["git", "-C", MY_REPO_PATH, "remote", "add", "origin", GITHUB_REMOTE_URL], check=True)

        subprocess.run(["git", "-C", MY_REPO_PATH, "push", "-u", "origin", "main"], check=True)
        print("All translated files committed and pushed to GitHub.")

    except subprocess.CalledProcessError as e:
        print(" Git error:", e)
        print(" GITHUB_REMOTE_URL:", GITHUB_REMOTE_URL)
else:
    print("No translated files to commit.")
