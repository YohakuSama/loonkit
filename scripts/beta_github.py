"""Small repository-scoped GitHub REST client; never logs tokens or follows redirects."""
from __future__ import annotations
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "YohakuSama/loonkit"


class GitHubError(RuntimeError):
    def __init__(self, status_code, method, path):
        self.status_code=status_code
        super().__init__('GitHub ' + method + ' ' + path.split('?')[0] + ' failed with HTTP ' + str(status_code))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    def __init__(self, token: str):
        if not token:
            raise ValueError("a repository-scoped GitHub token is required")
        self._token = token
        self._opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, payload=None):
        cleanup = ((method == 'PATCH' and re.fullmatch(r'/pulls/[1-9][0-9]*',path)) or
                   (method == 'DELETE' and re.fullmatch(r'/git/refs/heads/automation/publisher-check-[0-9]+-[0-9]+',path)))
        if (method not in {"GET", "POST"} and not cleanup) or not path.startswith("/") or ".." in path.split("/"):
            raise ValueError("unsupported GitHub operation")
        url = "https://api.github.com/repos/" + REPOSITORY + path
        request = urllib.request.Request(url, method=method,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Authorization":"Bearer " + self._token, "Accept":"application/vnd.github+json",
                     "Content-Type":"application/json", "X-GitHub-Api-Version":"2022-11-28",
                     "User-Agent":"LoonKit-beta-publisher"})
        try:
            with self._opener.open(request, timeout=45) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == "GET":
                return None
            raise GitHubError(error.code,method,path) from None
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("GitHub response too large")
        return json.loads(raw) if raw else None

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, payload):
        return self.request("POST", path, payload)

    def close_check_pr(self, number):
        if not isinstance(number,int) or number <= 0:
            raise ValueError('invalid check PR number')
        return self.request('PATCH','/pulls/' + str(number),{'state':'closed'})

    def delete_check_branch(self, branch):
        if not re.fullmatch(r'automation/publisher-check-[0-9]+-[0-9]+',branch):
            raise ValueError('only isolated publisher check branches can be deleted')
        return self.request('DELETE','/git/refs/heads/' + branch)

    def file(self, path: str, ref: str) -> bytes:
        if not re.fullmatch(r"[a-f0-9]{40}", ref) or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("file reads require an exact commit and safe repository path")
        value = self.get("/contents/" + urllib.parse.quote(path, safe="/") + "?ref=" + ref)
        if not value or value.get("encoding") != "base64" or value.get("size", 0) > 512 * 1024:
            raise ValueError("missing, unsupported or oversized GitHub text file: " + path)
        return base64.b64decode("".join(value["content"].split()), validate=True)
