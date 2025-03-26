import os
import requests
from openai import OpenAI
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

# Αρχικοποίηση του client της OpenAI
openai_key = "your_openai_key"
client = OpenAI(api_key=openai_key)



# Repo and  raw URL
GITHUB_REPO = "pibook/_gallery"
GITHUB_BRANCH = "abb9bb2cf89fcac2c9cd5cb363be5704197d146c"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

md_folder = "./github_md"
output_folder = "./translated"
os.makedirs(md_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# KeyBindings configuration
bindings = KeyBindings()

@bindings.add('enter', 'enter')
def _(event):
    "When double enter is pressed, end input."
    event.current_buffer.validate_and_handle()

session = PromptSession(key_bindings=bindings)

def edit_text_via_prompt_toolkit(text):
    return session.prompt("Edit the text:\n", multiline=True, default=text)

def get_repo_files():
    """Λήψη λίστας των markdown αρχείων από το GitHub API"""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    response = requests.get(api_url)
    if response.status_code == 200:
        tree = response.json()["tree"]
        return [file["path"] for file in tree if file["path"].endswith(".md")][:10]  # first ten files 
    else:
        print(f"Error fetching files: {response.status_code}")
        return []

def download_file(file_path):
    """Κατεβάζει ένα αρχείο από το GitHub"""
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

def translate_text(text, source_lang='Greek', target_lang='English', variation=1):
    """Translate text using OpenAI API while keeping the original YAML structure."""
    prompt = (
        f"Translate the following text from {source_lang} to {target_lang}. "
        f"Keep the original YAML structure without adding extra delimiters or formatting. "
        f"Preserve indentation and list formatting exactly as it is. "
        f"\n\n{text}\n"
    )
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional translator. Translate the given YAML content without modifying the format."},
            {"role": "user", "content": prompt}
        ],
    )
    
    return response.choices[0].message.content.strip()


files = get_repo_files()
for file in files:
    local_path = download_file(file)
    if local_path:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get two translations
        translation1 = translate_text(content, 'Greek', 'English', 1)
        translation2 = translate_text(content, 'Greek', 'English', 2)

        print("Translation 1:")
        print(translation1)
        print("\nTranslation 2:")
        print(translation2)

        choice = input("Do you want to edit Translation 1 or 2? (enter 1 or 2, or 'skip' to skip): ")
        if choice == '1':
            edited_text = session.prompt("Edit Translation 1:\n", default=translation1)
            chosen_translation = edited_text
        elif choice == '2':
            edited_text = session.prompt("Edit Translation 2:\n", default=translation2)
            chosen_translation = edited_text
        else:
            continue

        # Save the chosen and edited text
        output_file = os.path.join(output_folder, os.path.basename(file))
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chosen_translation)
        print(f"Edited and saved text in {output_file}")

        if input("Do you want to proceed to the next file? (yes/no): ").lower() != 'yes':
            break
