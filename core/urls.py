from django.urls import path
from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("projects/<int:pk>/sync/", views.project_sync, name="project_sync"),
    path("projects/<int:pk>/upload/", views.project_upload, name="project_upload"),
    path("projects/<int:pk>/variables/", views.project_variables, name="project_variables"),
    path("projects/<int:pk>/duplicates/", views.project_duplicates, name="project_duplicates"),

    path("projects/<int:pk>/descriptive/", views.descriptive_view, name="descriptive"),
    path("projects/<int:pk>/descriptive/add/", views.descriptive_add, name="descriptive_add"),
    path("projects/<int:pk>/crosstab/", views.crosstab_view, name="crosstab"),
    path("projects/<int:pk>/crosstab/add/", views.crosstab_add, name="crosstab_add"),
    path("projects/<int:pk>/compare/", views.compare_means_view, name="compare_means"),
    path("projects/<int:pk>/compare/add/", views.compare_means_add, name="compare_means_add"),
    path("projects/<int:pk>/correlation/", views.correlation_view, name="correlation"),
    path("projects/<int:pk>/correlation/add/", views.correlation_add, name="correlation_add"),
    path("projects/<int:pk>/regression/", views.regression_view, name="regression"),
    path("projects/<int:pk>/regression/add/", views.regression_add, name="regression_add"),
    path("projects/<int:pk>/reliability/", views.reliability_view, name="reliability"),
    path("projects/<int:pk>/reliability/add/", views.reliability_add, name="reliability_add"),

    path("projects/<int:pk>/report/", views.report_view, name="report"),
    path("projects/<int:pk>/report/clear/", views.report_clear, name="report_clear"),
    path("projects/<int:pk>/report/word/", views.report_word, name="report_word"),
    path("projects/<int:pk>/report/pdf/", views.report_pdf, name="report_pdf"),
]
