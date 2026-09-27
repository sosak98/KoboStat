"""Construit un DataFrame pandas propre à partir des soumissions stockées en base,
applique le recodage des variables, détecte les doublons, et gère l'upload de
fichiers CSV/Excel/SPSS comme source alternative à l'API Kobo."""
import io
import pandas as pd
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Submission, VariableMeta
from . import kobo_client

IGNORED_KOBO_FIELDS = {
    "_id", "_uuid", "formhub/uuid", "meta/instanceID", "_xform_id_string",
    "_status", "_geolocation", "_notes", "_tags", "_validation_status",
    "__version__", "_submitted_by", "_attachments", "_submission_time",
}


def normalize_submission(raw: dict) -> dict:
    """Nettoie un enregistrement brut Kobo (retire les métadonnées techniques)."""
    return {k: v for k, v in raw.items() if k not in IGNORED_KOBO_FIELDS and not k.startswith("_")}


def sync_project_from_kobo(project) -> dict:
    """Récupère les soumissions Kobo (ou génère des données de démo si aucun
    token n'est configuré) et les enregistre en base. Utilisé à la fois par le
    bouton manuel "Synchroniser" et par le point d'accès de synchronisation
    automatique (cron externe)."""
    if project.kobo_api_token and project.kobo_asset_uid:
        raw = kobo_client.fetch_submissions(project.kobo_base_url, project.kobo_api_token, project.kobo_asset_uid)
        source_label = "KoboToolbox"
    else:
        raw = kobo_client.generate_demo_submissions(120)
        source_label = "démo (aucun token Kobo configuré)"

    created = 0
    for rec in raw:
        uuid = str(rec.get("_uuid") or rec.get("_id"))
        clean = normalize_submission(rec)
        submitted_at = None
        raw_date = rec.get("_submission_time")
        if raw_date:
            submitted_at = parse_datetime(raw_date)
            if submitted_at and timezone.is_naive(submitted_at):
                submitted_at = timezone.make_aware(submitted_at, timezone.get_default_timezone())
        _, was_created = Submission.objects.update_or_create(
            project=project, kobo_uuid=uuid,
            defaults={"data": clean, "submitted_at": submitted_at},
        )
        created += 1 if was_created else 0

    project.last_synced_at = timezone.now()
    project.save(update_fields=["last_synced_at"])

    df = build_dataframe(project, apply_recoding=False)
    sync_variable_meta(project, df)
    if project.dedup_key_column:
        detect_and_flag_duplicates(project)

    return {"source_label": source_label, "n_received": len(raw), "n_created": created}


def build_dataframe(project, apply_recoding=True, filters: dict | None = None) -> pd.DataFrame:
    qs = Submission.objects.filter(project=project, is_duplicate=False)
    rows = [s.data for s in qs]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)

    if apply_recoding:
        metas = {v.name: v for v in VariableMeta.objects.filter(project=project) if v.recoding_map}
        for name, meta in metas.items():
            if name in df.columns:
                mapping = {str(k): v for k, v in meta.recoding_map.items()}
                df[name] = df[name].astype(str).map(mapping).fillna(df[name])

    if filters:
        for col, val in filters.items():
            if val and col in df.columns:
                df = df[df[col].astype(str) == str(val)]

    return df.reset_index(drop=True)


def infer_variable_types(df: pd.DataFrame) -> dict:
    types = {}
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce")
        non_null_ratio = series.notna().mean() if len(df[col]) else 0
        if non_null_ratio > 0.9:
            uniq = series.dropna().unique()
            if len(uniq) <= 7 and set(uniq).issubset(set(range(-1, 12))):
                types[col] = "likert"
            else:
                types[col] = "numerique"
        else:
            types[col] = "categorielle"
    return types


def sync_variable_meta(project, df: pd.DataFrame):
    """Crée les VariableMeta manquantes pour les colonnes découvertes dans les données."""
    existing = set(VariableMeta.objects.filter(project=project).values_list("name", flat=True))
    inferred = infer_variable_types(df)
    to_create = []
    for col in df.columns:
        if col not in existing:
            to_create.append(VariableMeta(project=project, name=col, label=col, var_type=inferred.get(col, "categorielle")))
    if to_create:
        VariableMeta.objects.bulk_create(to_create)


def detect_and_flag_duplicates(project):
    """Marque comme doublons les soumissions ayant la même valeur sur la colonne clé
    définie (project.dedup_key_column), en gardant la plus récente."""
    key_col = project.dedup_key_column
    Submission.objects.filter(project=project).update(is_duplicate=False)
    if not key_col:
        return 0

    subs = list(Submission.objects.filter(project=project).order_by("synced_at"))
    seen = {}
    dup_ids = []
    for s in subs:
        key = s.data.get(key_col)
        if key in (None, ""):
            continue
        if key in seen:
            dup_ids.append(seen[key])  # l'ancienne devient le doublon, on garde la plus récente
        seen[key] = s.id

    if dup_ids:
        Submission.objects.filter(id__in=dup_ids).update(is_duplicate=True)
    return len(dup_ids)


def quality_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(df)
    for col in df.columns:
        missing = df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum()
        rows.append({
            "Variable": col,
            "N valide": n - missing,
            "Manquants": int(missing),
            "% manquants": round(100 * missing / n, 1) if n else 0,
            "Valeurs uniques": df[col].nunique(dropna=True),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Import fichier
def load_uploaded_file(django_file) -> pd.DataFrame:
    name = django_file.name.lower()
    if name.endswith(".csv"):
        raw = django_file.read()
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=sep)
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
        django_file.seek(0)
        return pd.read_csv(django_file)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(django_file)
    elif name.endswith(".sav"):
        import pyreadstat
        tmp_path = "/tmp/_upload_django.sav"
        with open(tmp_path, "wb") as f:
            f.write(django_file.read())
        df, _meta = pyreadstat.read_sav(tmp_path)
        return df
    else:
        raise ValueError("Format non supporté (CSV, XLSX ou SAV attendus).")
