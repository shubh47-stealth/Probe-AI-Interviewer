# backend/app/ingestion/loader.py
import re
import pymupdf  # PyMuPDF
import httpx
from typing import List, Dict

# File extensions worth indexing from a candidate's GitHub repository
ALLOWED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".md"}
IGNORED_DIRS = {"node_modules", "venv", ".git", "dist", "build", "__pycache__", ".next"}

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts clean plain text from an uploaded Resume PDF."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages_text = [page.get_text("text") for page in doc]
    doc.close()
    return "\n".join(pages_text).strip()

def fetch_github_repo_files(repo_url: str, max_files: int = 15) -> List[Dict[str, str]]:
    """
    Fetches up to `max_files` core source code files from a public GitHub repository URL.
    Returns a list of {"source": "repo:path/to/file", "content": "..."} dicts for Hybrid RAG indexing.
    """
    if not repo_url or "github.com/" not in repo_url:
        return []

    # Parse owner and repo name from URL (e.g., https://github.com/owner/repo)
    match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url.rstrip("/"))
    if not match:
        return []
    owner, repo = match.group(1), match.group(2).replace(".git", "")

    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ProbeAI-Interviewer"}
    documents: List[Dict[str, str]] = []

    with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
        # 1. Get default branch (main or master)
        repo_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if repo_resp.status_code != 200:
            print(f"Warning: Could not access GitHub repo {owner}/{repo} (Status {repo_resp.status_code})")
            return []
        default_branch = repo_resp.json().get("default_branch", "main")

        # 2. Fetch recursive git tree
        tree_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1")
        if tree_resp.status_code != 200:
            return []

        tree = tree_resp.json().get("tree", [])
        candidate_files = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            # Skip ignored directories and lockfiles
            if any(part in IGNORED_DIRS for part in path.split("/")):
                continue
            ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if ext in ALLOWED_EXTENSIONS and item.get("size", 0) < 60_000:
                candidate_files.append(path)

        # Prioritize actual source files (src/, app/, backend/) and README
        candidate_files.sort(key=lambda p: (0 if "src/" in p or "app/" in p else 1, len(p)))

        # 3. Download raw file contents
        for file_path in candidate_files[:max_files]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{file_path}"
            raw_resp = client.get(raw_url)
            if raw_resp.status_code == 200 and len(raw_resp.text.strip()) > 30:
                documents.append({
                    "source": f"repo:{file_path}",
                    "content": f"File Path: {file_path}\n\n{raw_resp.text}"
                })

    print(f"Fetched {len(documents)} source files from GitHub repo {owner}/{repo}.")
    return documents