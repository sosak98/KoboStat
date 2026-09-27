"""Client pour l'API REST de KoboToolbox.

Doc officielle : https://support.kobotoolbox.org/api.html
Deux usages principaux :
  - lister les formulaires ("assets") disponibles pour un token donné
  - récupérer les soumissions ("data") d'un formulaire précis, en JSON
"""
import requests


class KoboAPIError(Exception):
    pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Token {token}"}


def list_assets(base_url: str, token: str) -> list:
    """Retourne la liste des formulaires (uid, nom) accessibles avec ce token."""
    url = f"{base_url.rstrip('/')}/api/v2/assets.json"
    resp = requests.get(url, headers=_headers(token), timeout=30)
    if resp.status_code != 200:
        raise KoboAPIError(f"Erreur Kobo ({resp.status_code}) : {resp.text[:300]}")
    results = resp.json().get("results", [])
    return [
        {"uid": a["uid"], "name": a.get("name") or "(sans nom)", "deployed": a.get("has_deployment", False)}
        for a in results
    ]


def fetch_submissions(base_url: str, token: str, asset_uid: str, limit: int = 30000) -> list:
    """Récupère toutes les soumissions d'un formulaire Kobo (pagination gérée)."""
    url = f"{base_url.rstrip('/')}/api/v2/assets/{asset_uid}/data.json"
    all_results = []
    params = {"limit": min(limit, 3000)}
    next_url = url

    while next_url:
        resp = requests.get(next_url, headers=_headers(token), params=params if next_url == url else None, timeout=60)
        if resp.status_code != 200:
            raise KoboAPIError(f"Erreur Kobo ({resp.status_code}) : {resp.text[:300]}")
        payload = resp.json()
        all_results.extend(payload.get("results", []))
        next_url = payload.get("next")
        if len(all_results) >= limit:
            break

    return all_results[:limit]


def generate_demo_submissions(n: int = 120) -> list:
    """Génère de fausses soumissions au format Kobo, pour démonstration sans
    compte Kobo réel (mêmes noms de champs qu'un vrai questionnaire d'enquête)."""
    import random
    random.seed(42)
    centres = ["Cotonou", "Porto-Novo", "Parakou", "Abomey"]
    niveaux = ["Primaire", "Secondaire", "Superieur"]
    out = []
    for i in range(n):
        out.append({
            "_id": 1000 + i,
            "_uuid": f"demo-{i:04d}",
            "_submission_time": f"2026-0{random.randint(1,8)}-{random.randint(1,28):02d}T10:00:00",
            "centre": random.choice(centres),
            "sexe": random.choice([1, 2]),
            "age": random.randint(18, 55),
            "niveau_etude": random.choice(niveaux),
            "satisfaction": random.randint(1, 5),
            "q1_confiance": random.randint(1, 5),
            "q2_confiance": random.randint(1, 5),
            "q3_confiance": random.randint(1, 5),
            "revenu": round(random.gauss(150000, 40000), 0),
        })
    return out
