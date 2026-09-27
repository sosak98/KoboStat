from django import forms
from .models import Project, VariableMeta


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "source", "kobo_base_url", "kobo_api_token", "kobo_asset_uid", "dedup_key_column"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Mémoire - Enquête ménages 2026"}),
            "source": forms.Select(attrs={"class": "form-select"}),
            "kobo_base_url": forms.TextInput(attrs={"class": "form-control"}),
            "kobo_api_token": forms.TextInput(attrs={"class": "form-control", "placeholder": "Token API Kobo (Compte > Paramètres > API)"}),
            "kobo_asset_uid": forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: aAbBcCdDeE123456"}),
            "dedup_key_column": forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: telephone (optionnel)"}),
        }


class UploadFileForm(forms.Form):
    file = forms.FileField(
        label="Fichier de données (CSV, Excel, SPSS .sav)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )


class VariableMetaForm(forms.ModelForm):
    class Meta:
        model = VariableMeta
        fields = ["label", "var_type", "recoding_map", "is_filterable"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "var_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "recoding_map": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 1,
                                                    "placeholder": '{"1": "Homme", "2": "Femme"}'}),
            "is_filterable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
