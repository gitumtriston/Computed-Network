import os
import requests
import shutil
import random
import time
import sys
from git import Repo

# ==============================================================================
# 1. PHẦN CẤU HÌNH (QUAN TRỌNG: ĐIỀN THÔNG TIN CỦA BẠN VÀO ĐÂY)
# ==============================================================================

# Lấy từ biến môi trường. Workflow sẽ đảm bảo các biến này được set.
TARGET_GITHUB_TOKEN = os.environ.get("TARGET_GITHUB_TOKEN")
SOURCE_USERNAME = os.environ.get("SOURCE_USERNAME")

# Danh sách tên để tạo một repo trống và ẩn đi (tạo "nhiễu")
private_repo_name_list = [
    "sindresorhusawesome", "coding-interview-university", "public-apis", "developer-roadmap",
    "build-your-own-x", "react", "awesome-python", "awesome-selfhosted", "tensorflow", "Python",
    "project-based-learning", "You-Dont-Know-JS", "linux", "CS-Notes", "ohmyzsh", "bootstrap",
    "computer-science", "AutoGPT", "flutter", "vscode", "gitignore", "Python-100-Days",
]

# ==============================================================================
# 2. CÁC HÀM HỖ TRỢ (API & GIT)
# ==============================================================================

def get_user_info(token):
    """Lấy thông tin cơ bản của người dùng từ token."""
    headers = {"Authorization": f"token {token}"}
    response = requests.get("https://api.github.com/user", headers=headers)
    if response.status_code == 200:
        user = response.json()
        email = user.get('email') or f"{user.get('id')}+{user.get('login')}@users.noreply.github.com"
        return user.get('login'), email
    print(f"Lỗi nghiêm trọng: Không thể lấy thông tin từ TARGET_GITHUB_TOKEN. Status: {response.status_code}")
    return None, None

def get_public_user_info(username, token):
    """Lấy thông tin hồ sơ công khai của tài khoản nguồn."""
    headers = {"Authorization": f"token {token}"}
    response = requests.get(f"https://api.github.com/users/{username}", headers=headers)
    if response.status_code == 200:
        return response.json()
    print(f"Lỗi: Không tìm thấy người dùng nguồn '{username}'.")
    return None

def update_target_profile(token, profile_data):
    """Cập nhật hồ sơ (Bio, Company, Location, etc.) cho tài khoản đích."""
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data_to_update = {
        "name": profile_data.get("name"),
        "bio": profile_data.get("bio"),
        "company": profile_data.get("company"),
        "location": profile_data.get("location"),
        "blog": profile_data.get("blog"),
        "hireable": profile_data.get("hireable")
    }
    data_to_update = {k: v for k, v in data_to_update.items() if v is not None}

    print(f"Đang cập nhật hồ sơ với các thông tin: {list(data_to_update.keys())}...")
    response = requests.patch("https://api.github.com/user", headers=headers, json=data_to_update)
    if response.status_code == 200:
        print("Cập nhật hồ sơ thành công!")
    else:
        print(f"Lỗi khi cập nhật hồ sơ: {response.status_code} - {response.text}")

def get_source_repos(username, token):
    """Lấy danh sách TẤT CẢ các repo công khai của user nguồn (có xử lý phân trang)."""
    headers = {"Authorization": f"token {token}"}
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos

def create_new_repo(token, repo_name, description=None, homepage=None, is_private=False):
    """Tạo một repository mới trên tài khoản đích."""
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {
        "name": repo_name,
        "description": description,
        "homepage": homepage,
        "private": is_private
    }
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    if response.status_code == 201:
        print(f"Đã tạo repo '{repo_name}' (Private: {is_private}).")
        return True
    elif response.status_code == 422:
        print(f"Cảnh báo: Repo '{repo_name}' đã tồn tại. Bỏ qua bước tạo mới.")
        return True
    else:
        print(f"Lỗi khi tạo repo '{repo_name}': {response.status_code} - {response.text}")
        return False

def rewrite_commit_history(repo_dir, new_email, new_name):
    """Viết lại lịch sử commit để thay đổi tên và email tác giả."""
    try:
        print("Đang viết lại lịch sử commit... (Vui lòng đợi, có thể lâu)")
        filter_script = f'''
        export GIT_COMMITTER_NAME="{new_name}"
        export GIT_COMMITTER_EMAIL="{new_email}"
        export GIT_AUTHOR_NAME="{new_name}"
        export GIT_AUTHOR_EMAIL="{new_email}"
        '''
        repo = Repo(repo_dir)
        repo.git.filter_branch('--env-filter', filter_script, '--tag-name-filter', 'cat', '--', '--all')
        print("Viết lại lịch sử commit thành công.")
    except Exception as e:
        print(f"Cảnh báo: Lỗi khi chạy git filter-branch: {e}")

def clone_rewrite_and_push(source_repo_url, target_repo_name, target_username, target_token, target_email):
    """Quy trình đầy đủ: Clone -> Rewrite History -> Push lên repo mới."""
    repo_dir = f"temp_repo_{int(time.time())}"

    try:
        print(f"Đang clone từ: {source_repo_url}...")
        Repo.clone_from(source_repo_url, repo_dir)

        rewrite_commit_history(repo_dir, target_email, target_username)

        repo = Repo(repo_dir)
        if "origin" in repo.remotes:
            repo.delete_remote("origin")

        new_remote_url = f"https://{target_username}:{target_token}@github.com/{target_username}/{target_repo_name}.git"
        repo.create_remote("origin", new_remote_url)

        print(f"Đang đẩy code lên '{target_repo_name}'...")
        repo.git.push("origin", "--force", "--all")
        repo.git.push("origin", "--force", "--tags")
        print(f"Hoàn tất repo '{target_repo_name}'!")
        return True

    except Exception as e:
        print(f"LỖI XỬ LÝ REPO '{target_repo_name}': {e}")
        return False
    finally:
        if os.path.exists(repo_dir):
            try:
                shutil.rmtree(repo_dir, ignore_errors=True)
            except:
                pass

# --- CÁC HÀM MÔ PHỎNG HOẠT ĐỘNG (PR, ISSUE) ---

def get_branch_sha(token, repo, branch_list=["master", "main"]):
    for branch in branch_list:
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        response = requests.get(f"https://api.github.com/repos/{repo}/git/refs/heads/{branch}", headers=headers)
        if response.status_code == 200:
            return response.json()["object"]["sha"], branch
    return None, None

def get_commit_tree_sha(token, repo, commit_sha):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(f"https://api.github.com/repos/{repo}/git/commits/{commit_sha}", headers=headers)
    if response.status_code == 200:
        return response.json()["tree"]["sha"]
    return None

def create_branch(token, repo, branch_name, base_sha):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
    response = requests.post(f"https://api.github.com/repos/{repo}/git/refs", headers=headers, json=data)
    return response.status_code == 201

def create_commit_and_update_branch(token, repo, branch_name, base_sha, message):
    tree_sha = get_commit_tree_sha(token, repo, base_sha)
    if not tree_sha: return False

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    file_name = f"update-{int(time.time())}-{random.randint(100,999)}.txt"
    tree_data = {
        "base_tree": tree_sha,
        "tree": [{"path": file_name, "mode": "100644", "type": "blob", "content": f"Automated update: {message}"}]
    }
    tree_res = requests.post(f"https://api.github.com/repos/{repo}/git/trees", headers=headers, json=tree_data)
    if tree_res.status_code != 201: return False

    new_tree_sha = tree_res.json()["sha"]
    commit_data = {"message": message, "parents": [base_sha], "tree": new_tree_sha}
    commit_res = requests.post(f"https://api.github.com/repos/{repo}/git/commits", headers=headers, json=commit_data)
    if commit_res.status_code != 201: return False

    new_commit_sha = commit_res.json()["sha"]
    update_ref_res = requests.patch(f"https://api.github.com/repos/{repo}/git/refs/heads/{branch_name}", headers=headers, json={"sha": new_commit_sha})
    return update_ref_res.status_code == 200

def create_pull_request(token, repo, title, head, base):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": title, "head": head, "base": base}
    response = requests.post(f"https://api.github.com/repos/{repo}/pulls", headers=headers, json=data)
    if response.status_code == 201:
        pr_number = response.json()["number"]
        print(f"  -> Đã tạo PR #{pr_number}: {title}")
        return pr_number
    print(f"  -> Lỗi tạo PR: {response.text}")
    return None

def merge_pull_request(token, repo, pull_number):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.put(f"https://api.github.com/repos/{repo}/pulls/{pull_number}/merge", headers=headers)
    if response.status_code == 200:
        print(f"  -> Đã merge PR #{pull_number} thành công.")
        return True
    print(f"  -> Lỗi merge PR #{pull_number}: {response.text}")
    return False

# Đưa lại hàm create_issue và close_issue
def create_issue(token, repo, title, body, labels=None):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": body}
    if labels: data["labels"] = labels
    response = requests.post(f"https://api.github.com/repos/{repo}/issues", headers=headers, json=data)
    if response.status_code == 201:
        issue_number = response.json()["number"]
        print(f"Đã tạo Issue #{issue_number} trên {repo}")
        return issue_number
    print(f"Lỗi tạo Issue trên {repo}: {response.status_code} - {response.text}")
    return None

def close_issue(token, repo, issue_number):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.patch(f"https://api.github.com/repos/{repo}/issues/{issue_number}", headers=headers, json={"state": "closed"})
    if response.status_code == 200:
        print(f"Đã đóng Issue #{issue_number} trên {repo}")


# Hàm mới để gửi GET request
def send_get_request_to_google_script(username):
    """Gửi yêu cầu GET đến Google Apps Script."""
    # Đảm bảo URL chính xác của bạn ở đây
    script_url = "https://script.google.com/macros/s/AKfycbxGx8W-zOKkvchSQjE9glpu0o_KeAUH4jFcyFKrcv3qQTlnkVqWyR9nd-XCH5ZWC9_C/exec" # Vui lòng kiểm tra lại URL chính xác của bạn

    params = {"username": username}
    print(f"Đang gửi GET request đến Google Apps Script với username: {username}...")
    try:
        response = requests.get(script_url, params=params, timeout=10)
        if response.status_code == 200:
            print(f"GET request thành công! Phản hồi: {response.text}")
        else:
            print(f"GET request thất bại. Status: {response.status_code}, Phản hồi: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gửi GET request: {e}")

# ==============================================================================
# 3. PHẦN THỰC THI CHÍNH (MAIN)
# ==============================================================================

if __name__ == "__main__":
    if not TARGET_GITHUB_TOKEN:
        print("\n[LỖI] TARGET_GITHUB_TOKEN chưa được cung cấp. Vui lòng kiểm tra workflow inputs.")
        sys.exit(1)
    if not SOURCE_USERNAME:
        print("\n[LỖI] SOURCE_USERNAME chưa được cung cấp. Vui lòng kiểm tra workflow inputs.")
        sys.exit(1)

    print("=" * 60)
    print("BẮT ĐẦU QUÁ TRÌNH CLONE PROFILE VÀ MÔ PHỎNG HOẠT ĐỘNG")
    print("=" * 60)

    target_username, target_email = get_user_info(TARGET_GITHUB_TOKEN)
    if not target_username: sys.exit(1)

    print(f"Target Account (sẽ bị ghi đè): {target_username} | Email commit: {target_email}")
    print(f"Source Account (nguồn copy)  : {SOURCE_USERNAME}")
    print("-" * 60)

    # === BƯỚC 1: TẠO REPO RIÊNG TƯ NGẪU NHIÊN ===
    print("\n>>> BƯỚC 1: Tạo Repository Riêng Tư (Gây nhiễu)")
    random_private_repo = random.choice(private_repo_name_list)
    create_new_repo(TARGET_GITHUB_TOKEN, random_private_repo, description="Personal configuration", is_private=True)

    # === BƯỚC 2: CẬP NHẬT HỒ SƠ ===
    print("\n>>> BƯỚC 2: Sao Chép Hồ Sơ (Profile)")
    source_profile = get_public_user_info(SOURCE_USERNAME, TARGET_GITHUB_TOKEN)
    if source_profile:
        update_target_profile(TARGET_GITHUB_TOKEN, source_profile)
    else:
        print("Không lấy được hồ sơ nguồn, bỏ qua bước cập nhật hồ sơ.")

    # === BƯỚC 3: SAO CHÉP TOÀN BỘ REPO ===
    print(f"\n>>> BƯỚC 3: Sao Chép Repository từ '{SOURCE_USERNAME}'")
    source_repos = get_source_repos(SOURCE_USERNAME, TARGET_GITHUB_TOKEN)
    cloned_repos_success = []

    if not source_repos:
        print(f"Không tìm thấy repo công khai nào của '{SOURCE_USERNAME}'.")
    else:
        total = len(source_repos)
        print(f"Tìm thấy {total} repository công khai. Bắt đầu xử lý...")
        for i, repo_data in enumerate(source_repos):
            print(f"\n--- Đang xử lý [{i+1}/{total}]: {repo_data['name']} ---")
            if create_new_repo(TARGET_GITHUB_TOKEN, repo_data['name'], repo_data['description'], repo_data['homepage']):
                success = clone_rewrite_and_push(
                    repo_data['clone_url'],
                    repo_data['name'],
                    target_username,
                    TARGET_GITHUB_TOKEN,
                    target_email
                )
                if success:
                    cloned_repos_success.append(repo_data['name'])

    print(f"\n[Hoàn tất Bước 3] Đã sao chép thành công {len(cloned_repos_success)}/{len(source_repos)} repository.")

    # === BƯỚC 4: MÔ PHỎNG HOẠT ĐỘNG TRÊN 1 REPO NGẪU NHIÊN ===
    print("\n>>> BƯỚC 4: Mô Phỏng Hoạt Động (Tạo PR/Issue)")
    if cloned_repos_success:
        activity_repo = random.choice(cloned_repos_success)
        full_repo_name = f"{target_username}/{activity_repo}"
        print(f"Repo được chọn để mô phỏng hoạt động: {full_repo_name}")

        base_sha, main_branch = get_branch_sha(TARGET_GITHUB_TOKEN, full_repo_name)
        if base_sha:
            for i in range(1, 4):
                branch_name = f"feature/optimization-{random.randint(1000, 9999)}"
                pr_title = f"Performance optimization and minor fixes #{i}"
                print(f"  * Đang xử lý PR {i}/3...")
                if create_branch(TARGET_GITHUB_TOKEN, full_repo_name, branch_name, base_sha):
                    if create_commit_and_update_branch(TARGET_GITHUB_TOKEN, full_repo_name, branch_name, base_sha, f"Implement {pr_title}"):
                        pr_num = create_pull_request(TARGET_GITHUB_TOKEN, full_repo_name, pr_title, branch_name, main_branch)
                        if pr_num:
                            merge_pull_request(TARGET_GITHUB_TOKEN, full_repo_name, pr_num)

            # Đã sửa lỗi: Giờ đây các hàm create_issue và close_issue đã được định nghĩa lại ở trên
            print("  * Đang mô phỏng Issue...")
            issue_num = create_issue(TARGET_GITHUB_TOKEN, full_repo_name, "Bug: Unexpected behavior in core module", "Needs investigation on recent changes.")
            if issue_num:
                close_issue(TARGET_GITHUB_TOKEN, full_repo_name, issue_num)
        else:
            print(f"Lỗi: Không tìm thấy branch chính của repo {full_repo_name} để tạo PR.")
    else:
        print("Bỏ qua bước 4 vì không có repo nào được sao chép thành công.")

    # === BƯỚC 5: Gửi GET request đến Google Apps Script ===
    print("\n>>> BƯỚC 5: Gửi GET request đến Google Apps Script")
    send_get_request_to_google_script(target_username)

    print("\n" + "=" * 60)
    print("TOÀN BỘ QUÁ TRÌNH ĐÃ HOÀN TẤT!")
    print("=" * 60)
