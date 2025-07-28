import requests
import subprocess
import json
from run_initial import RunInitialMain
from utils import GithubSCM


class GitHubWebhookManager(GithubSCM):

    def __init__(self, folder_path):

        self.folder_path = folder_path
        self.repo_url = self.get_github_url(self.folder_path)
        self.repo_url=self.repo_url.rstrip('/')
        self.webhook_url = self.generate_webhook_url() 
        self.token = self.get_github_token()
        self.owner, self.repo = self.extract_owner_repo()

    def get_github_url(self,folder_path):
        github_url = self.github_repo_url(folder_path)
        return github_url
    
    def get_github_token(self):
        """Refresh the GitHub authentication token to include webhook permissions"""
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)

        if result.returncode != 0:
            print("❌ Error: GitHub authentication failed or insufficient permissions. Run 'gh auth login' first.")
            exit(1)

        return result.stdout.strip()

    def extract_owner_repo(self):
        """Extracts the owner and repository name from the SSH or HTTPS GitHub URL."""
        if self.repo_url.startswith("git@github.com:"):
            # SSH URL format: git@github.com:owner/repo.git
            repo_path = self.repo_url.split(":")[-1]  # Get "owner/repo.git"
        elif self.repo_url.startswith("https://github.com/"):
            # HTTPS URL format: https://github.com/owner/repo.git
            repo_path = self.repo_url.split("github.com/")[-1]  # Get "owner/repo.git"
        else:
            raise ValueError("❌ Invalid repository URL format")

        owner, repo = repo_path.replace(".git", "").split("/")
        return owner, repo

    def generate_webhook_url(self):
        """
        Fetches the instance IP and appends the webhook path.
        """
        run = RunInitialMain(self.folder_path)
        instance_ip = run.get_instance_ip()

        print(f"http://{instance_ip}:8080/github-webhook/")

        return f"http://{instance_ip}:8080/github-webhook/"


    def create_webhook(self):
        """Creates a GitHub webhook using the API"""

        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/hooks"
        print(api_url)
        payload = {
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "url": self.webhook_url,
                "content_type": "json",
                "secret": "your-webhook-secret",
                "insecure_ssl": "0"
            }
        }

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.token}"
        }

        print(payload)

        response = requests.post(api_url, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            return f"✅ Webhook successfully created for {self.owner}/{self.repo}!"
        elif response.status_code == 404:
            return "❌ Error: Repository not found or incorrect permissions."
        elif response.status_code == 401:
            return "❌ Authentication error. Ensure your token is valid."
        else:
            return f"❌ Failed to create webhook. HTTP Response: {response.status_code}, {response.text}"

# Usage
if __name__ == "__main__":
    folder_path = "/Users/mitulgarg/Desktop/Mitul/Auto Anchor/other/AutoAnchorWebsite/my-react-project"
    work_dir = "/Users/mitulgarg/Desktop/Mitul/Auto Anchor/other/AutoAnchorWebsite/my-react-project"
    
    webhook_manager = GitHubWebhookManager(folder_path,work_dir)
    webhook_manager.create_webhook()
