from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """Un 'projet' = une enquête / un mémoire, connecté (ou non) à un formulaire Kobo."""

    SOURCE_CHOICES = [
        ("kobo", "KoboToolbox (API)"),
        ("upload", "Fichier importé (CSV/Excel/SPSS)"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField("Nom du projet", max_length=200)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="upload")

    # Connexion KoboToolbox
    kobo_base_url = models.CharField(
        "URL de base Kobo", max_length=200, blank=True,
        default="https://kf.kobotoolbox.org",
        help_text="ex: https://kf.kobotoolbox.org ou https://eu.kobotoolbox.org",
    )
    kobo_api_token = models.CharField("Token API Kobo", max_length=200, blank=True)
    kobo_asset_uid = models.CharField("UID du formulaire (asset)", max_length=100, blank=True)

    # Colonne utilisée pour détecter les doublons de répondants (ex: numéro de téléphone)
    dedup_key_column = models.CharField(
        "Colonne clé de dé-doublonnage (optionnel)", max_length=200, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Submission(models.Model):
    """Une soumission/réponse individuelle, stockée en JSON (souple, structure
    variable selon le questionnaire), avec la clé Kobo pour éviter les doublons."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="submissions")
    kobo_uuid = models.CharField(max_length=200, blank=True, db_index=True)
    data = models.JSONField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now_add=True)
    is_duplicate = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["project", "kobo_uuid"])]

    def __str__(self):
        return f"{self.project.name} — {self.kobo_uuid or self.pk}"


class VariableMeta(models.Model):
    """Métadonnées et règles de nettoyage/recodage par variable (colonne)."""

    TYPE_CHOICES = [
        ("numerique", "Numérique"),
        ("categorielle", "Catégorielle"),
        ("likert", "Likert / échelle"),
        ("date", "Date"),
        ("texte", "Texte libre"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="variables")
    name = models.CharField(max_length=200)
    label = models.CharField(max_length=300, blank=True)
    var_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="categorielle")
    recoding_map = models.JSONField(
        "Table de recodage (ex: {\"1\":\"Homme\",\"2\":\"Femme\"})", blank=True, null=True
    )
    is_filterable = models.BooleanField("Utilisable comme filtre du tableau de bord", default=False)

    class Meta:
        unique_together = ("project", "name")

    def __str__(self):
        return f"{self.project.name}.{self.name}"


class SavedReport(models.Model):
    """Rapport en cours de construction (contenu = liste de blocs JSON)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reports")
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, default="Résultats et analyses")
    blocks = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.project.name})"
