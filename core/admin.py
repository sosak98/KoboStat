from django.contrib import admin
from .models import Project, Submission, VariableMeta, SavedReport


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "source", "last_synced_at", "created_at")
    list_filter = ("source",)
    search_fields = ("name",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("project", "kobo_uuid", "submitted_at", "is_duplicate", "synced_at")
    list_filter = ("project", "is_duplicate")


@admin.register(VariableMeta)
class VariableMetaAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "label", "var_type", "is_filterable")
    list_filter = ("project", "var_type")


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "owner", "updated_at")
