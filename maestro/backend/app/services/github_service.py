"""
Servicio de integración con GitHub.

Usa la API REST v3 de GitHub con un Personal Access Token opcional.
Sin token: 60 req/h (rate limit público). Con token: 5000 req/h.

Scopes necesarios del token:
- repo (para repos privados)
- public_repo (solo para repos públicos)
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return h


def parse_repo(github_url: str) -> Optional[tuple[str, str]]:
    """
    Extrae (owner, repo) de una URL de GitHub.
    Acepta: https://github.com/owner/repo, github.com/owner/repo, owner/repo
    """
    if not github_url:
        return None
    url = github_url.strip().rstrip("/")
    # Forma corta: "owner/repo"
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", url):
        parts = url.split("/")
        return parts[0], parts[1]
    # URL completa
    parsed = urlparse(url if "://" in url else "https://" + url)
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) >= 2:
        return path_parts[0], path_parts[1]
    return None


def get_repo_stats(github_url: str) -> dict:
    """
    Devuelve estadísticas del repositorio: nombre, descripción, estrellas, forks,
    último commit, issues abiertos, PRs abiertos.
    """
    repo = parse_repo(github_url)
    if not repo:
        return {"error": f"URL de GitHub inválida: {github_url}"}

    owner, name = repo
    try:
        with httpx.Client(headers=_headers(), timeout=10) as client:
            r = client.get(f"{_GITHUB_API}/repos/{owner}/{name}")
            if r.status_code == 404:
                return {"error": f"Repositorio {owner}/{name} no encontrado"}
            if r.status_code == 401:
                return {"error": "Token de GitHub inválido o sin permisos"}
            r.raise_for_status()
            data = r.json()

            branch = data.get("default_branch", "main")
            commits_r = client.get(
                f"{_GITHUB_API}/repos/{owner}/{name}/commits",
                params={"sha": branch, "per_page": 1},
            )
            last_commit = {}
            if commits_r.is_success and commits_r.json():
                c = commits_r.json()[0]
                last_commit = {
                    "sha": c["sha"][:7],
                    "mensaje": c["commit"]["message"].split("\n")[0][:80],
                    "autor": c["commit"]["author"]["name"],
                    "fecha": c["commit"]["author"]["date"][:10],
                }

            prs_r = client.get(
                f"{_GITHUB_API}/repos/{owner}/{name}/pulls",
                params={"state": "open", "per_page": 5},
            )
            open_prs = []
            if prs_r.is_success:
                for pr in prs_r.json():
                    open_prs.append({
                        "numero": pr["number"],
                        "titulo": pr["title"][:60],
                        "autor": pr["user"]["login"],
                        "fecha": pr["created_at"][:10],
                    })

            return {
                "repo": f"{owner}/{name}",
                "descripcion": data.get("description") or "",
                "url": data.get("html_url"),
                "rama_default": branch,
                "estrellas": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "issues_abiertos": data.get("open_issues_count", 0),
                "lenguaje": data.get("language") or "—",
                "privado": data.get("private", False),
                "ultimo_push": data.get("pushed_at", "")[:10],
                "ultimo_commit": last_commit,
                "prs_abiertos": open_prs,
                "topics": data.get("topics", []),
            }

    except httpx.TimeoutException:
        return {"error": "Timeout al conectar con GitHub"}
    except Exception as exc:
        logger.warning("GitHub get_repo_stats error: %s", exc)
        return {"error": str(exc)}


def get_recent_commits(github_url: str, n: int = 10) -> list[dict]:
    """Devuelve los últimos N commits del repositorio."""
    repo = parse_repo(github_url)
    if not repo:
        return []

    owner, name = repo
    try:
        with httpx.Client(headers=_headers(), timeout=10) as client:
            r = client.get(
                f"{_GITHUB_API}/repos/{owner}/{name}/commits",
                params={"per_page": min(n, 30)},
            )
            r.raise_for_status()
            commits = []
            for c in r.json():
                commits.append({
                    "sha": c["sha"][:7],
                    "mensaje": c["commit"]["message"].split("\n")[0][:80],
                    "autor": c["commit"]["author"]["name"],
                    "fecha": c["commit"]["author"]["date"][:10],
                    "url": c.get("html_url", ""),
                })
            return commits
    except Exception as exc:
        logger.warning("GitHub get_recent_commits error: %s", exc)
        return []
