import os
import requests
import streamlit as st
from openai import OpenAI
from llm_client import get_llm_client

client, model = get_llm_client()

# Repo and  raw URL
GITHUB_REPO = "pibook/_gallery"
GITHUB_BRANCH = "abb9bb2cf89fcac2c9cd5cb363be5704197d146c"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# local files 
md_folder = "./github_md"
output_folder = "./translated"
os.makedirs(md_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

def get_repo_files():
    """Λήψη λίστας των markdown αρχείων από το GitHub API"""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    response = requests.get(api_url)
    if response.status_code == 200:
        tree = response.json()["tree"]
        return [file["path"] for file in tree if file["path"].endswith(".md")][:10]  # first 10 files 
    else:
        st.error(f"Error fetching files: {response.status_code}")
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
        st.error(f"Error downloading {file_path}")
        return None

def translate_text(text, source_lang, target_lang, variation):
    """Translate text using selected LLM model while keeping the original YAML structure."""
    prompt = (
        f"Translate the following text from {source_lang} to {target_lang}. "
        f"Keep the original YAML structure without adding extra delimiters or formatting. "
        f"Preserve indentation and list formatting exactly as it is. "
        f"\n\n{text}\n"
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional translator. Translate the given YAML content without modifying the format."},
            {"role": "user", "content": prompt}
        ],
    )
    
    return response.choices[0].message.content.strip()

def list_saved_files():
    """Επιστρέφει την λίστα με τα μεταφρασμένα αποθηκευμένα αρχεία"""
    return [f for f in os.listdir(output_folder) if f.endswith(".md")]

st.title("GitHub Markdown Translator")
st.sidebar.header("Settings")

section = st.sidebar.radio("Select Section:", ["Saved Files", "Translation of MD Files"])

if section == "Saved Files":
    if "show_saved_files" not in st.session_state:
        st.session_state["show_saved_files"] = False
    
    if st.sidebar.button("Show Saved Files"):
        st.session_state["show_saved_files"] = not st.session_state["show_saved_files"]
        st.session_state.pop("editing_content", None)
        st.session_state.pop("editing_file", None)
    
    if st.session_state["show_saved_files"]:
        saved_files = list_saved_files()
        if saved_files:
            selected_saved_file = st.sidebar.selectbox("Select a file to edit:", saved_files)
            if st.sidebar.button("Edit"):
                with open(os.path.join(output_folder, selected_saved_file), "r", encoding="utf-8") as f:
                    st.session_state["editing_content"] = f.read()
                    st.session_state["editing_file"] = selected_saved_file
        else:
            st.sidebar.text("No saved files.")
    
    if "editing_content" in st.session_state:
        st.subheader(f"Editing: {st.session_state['editing_file']}")
        new_content = st.text_area("Edit file:", st.session_state["editing_content"], height=300)
        if st.button("Save Changes"):
            with open(os.path.join(output_folder, st.session_state["editing_file"]), "w", encoding="utf-8") as f:
                f.write(new_content)
            st.success("Changes saved!")
            st.session_state.pop("editing_content", None)
            st.session_state.pop("editing_file", None)

elif section == "Translation of MD Files":
    if st.sidebar.button("Fetch Files from GitHub"):
        files = get_repo_files()
        if files:
            st.session_state["files"] = files
            st.session_state["selected_file"] = None
            st.success("File list updated!")
    
    if "files" in st.session_state and st.session_state["files"]:
        selected_file = st.selectbox("Select a file for translation:", st.session_state["files"])
        if st.button("Download and Translate"):
            st.session_state.pop("translated_content_1", None)
            st.session_state.pop("translated_content_2", None)
            local_path = download_file(selected_file)
            if local_path:
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
                st.session_state["translated_content_1"] = translate_text(content, "Greek", "English", 1)
                st.session_state["translated_content_2"] = translate_text(content, "Greek", "English", 2)
                st.success("Translation completed!")
    
    if "translated_content_1" in st.session_state and "translated_content_2" in st.session_state:
        cols = st.columns(2)
        with cols[0]:
            final_translation_1 = st.text_area("Translation 1", st.session_state["translated_content_1"], height=300)
        with cols[1]:
            final_translation_2 = st.text_area("Translation 2", st.session_state["translated_content_2"], height=300)
        selected_option = st.radio("Select the translation to save:", ("Translation 1", "Translation 2"))
        if st.button("Save Selected Translation"):
            output_file = os.path.join(output_folder, os.path.basename(st.session_state["selected_file"]))
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_translation_1 if selected_option == "Translation 1" else final_translation_2)
            st.success(f" Saved: {output_file}")