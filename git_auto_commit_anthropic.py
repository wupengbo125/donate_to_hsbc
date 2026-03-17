import os
import time
import subprocess
import requests

import argparse

# ================= CONFIGURATION =================
API_URL = "https://ark.cn-beijing.volces.com/api/coding/v1/messages"
API_KEY = "b0ac5f3e-ca10-4527-a22a-5848291e7f3b"
MODEL_ID = "ark-code-latest" 
# =================================================

def get_git_root():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.STDOUT).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_staged_diff():
    try:
        return subprocess.check_output(['git', 'diff', '--cached'], stderr=subprocess.STDOUT).decode().strip()
    except subprocess.CalledProcessError:
        return ""

def get_staged_files():
    try:
        output = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], stderr=subprocess.STDOUT).decode().strip()
        return output.splitlines() if output else []
    except subprocess.CalledProcessError:
        return []

def generate_commit_message(diff):
    if not diff: return "minor changes"
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_ID,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": f"Generate a concise git commit message for this diff. Only return the message text.\n\nDiff:\n{diff}"}]
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()['content'][0]['text'].strip()
    except Exception as e:
        print(f"Error: {e}")
        return "auto commit (anthropic)"

def monitor_git(do_push=False):
    git_root = get_git_root()
    if not git_root: return
    index_path = os.path.join(git_root, '.git', 'index')
    if not os.path.exists(index_path): return

    print(f"Monitoring git changes (Anthropic/Ark Mode, Push: {do_push})...")
    last_mtime = os.path.getmtime(index_path)

    while True:
        try:
            current_mtime = os.path.getmtime(index_path)
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                files = get_staged_files()
                if files:
                    print(f"Detected: {', '.join(files)}")
                    diff = get_staged_diff()
                    message = generate_commit_message(diff)
                    try:
                        subprocess.check_call(['git', 'commit', '-m', message])
                        print("Committed successfully.")
                    except subprocess.CalledProcessError as e:
                        print(f"Commit skipped or failed (might be empty): {e}")
                    
                    if do_push:
                        print("Pushing changes...")
                        try:
                            subprocess.check_call(['git', 'push'])
                            print("Pushed successfully.")
                        except subprocess.CalledProcessError as e:
                            print(f"Push failed: {e}")
            time.sleep(2)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Git auto-commit monitor (Anthropic)")
    parser.add_argument("--push", action="store_true", help="Automatically push after commit")
    args = parser.parse_args()
    
    monitor_git(do_push=args.push)
