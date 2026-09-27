import base64
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
import pandas as pd

from . import kobo_client, data_pipeline, stats_engine, interpretation
from . import plotting_static, plotting_interactive as plt_i
from . import word_export, pdf_export
from .forms import ProjectForm, UploadFileForm, VariableMetaForm
from .models import Project, Submission, VariableMeta, SavedReport


# ----------------------------------------------------------------- helpers
def _get_project(request, pk):
    return get_object_or_404(Project, pk=pk, owner=request.user)


def _filterable_vars(project):
    return list(VariableMeta.objects.filter(project=project, is_filterable=True))


def _get_filters(request, project):
    filters = {}
    for v in _filterable_vars(project):
        val = request.GET.get(f"f_{v.name}")
        if val:
            filters[v.name] = val
    return filters


def _var_choices(df, var_types, kinds):
    return [c for c in df.columns if var_types.get(c) in kinds]


def _get_or_create_report(project, user):
    report, _ = SavedReport.objects.get_or_create(
        project=project, owner=user, defaults={"title": f"Résultats — {project.name}"}
    )
    return report


def _lang(request):
    return "en" if request.GET.get("lang") == "en" else "fr"


# ----------------------------------------------------------------- Projects
@login_required
def project_list(request):
    projects = Project.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "core/project_list.html", {"projects": projects})


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            messages.success(request, "Projet créé avec succès.")
            return redirect("project_detail", pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, "core/project_form.html", {"form": form})


@login_required
def project_detail(request, pk):
    project = _get_project(request, pk)
    n_submissions = Submission.objects.filter(project=project, is_duplicate=False).count()
    n_duplicates = Submission.objects.filter(project=project, is_duplicate=True).count()
    variables = VariableMeta.objects.filter(project=project).order_by("name")
    upload_form = UploadFileForm()
    return render(request, "core/project_detail.html", {
        "project": project, "n_submissions": n_submissions, "n_duplicates": n_duplicates,
        "variables": variables, "upload_form": upload_form,
    })


@login_required
def project_delete(request, pk):
    project = _get_project(request, pk)
    if request.method == "POST":
        name = project.name
        project.delete()
        messages.success(request, f"Projet « {name} » supprimé définitivement.")
        return redirect("project_list")
    return redirect("project_detail", pk=pk)


@login_required
def project_sync(request, pk):
    project = _get_project(request, pk)
    try:
        if project.kobo_api_token and project.kobo_asset_uid:
            raw = kobo_client.fetch_submissions(project.kobo_base_url, project.kobo_api_token, project.kobo_asset_uid)
            source_label = "KoboToolbox"
        else:
            raw = kobo_client.generate_demo_submissions(120)
            source_label = "démo (aucun token Kobo configuré)"

        from django.utils.dateparse import parse_datetime

        created = 0
        for rec in raw:
            uuid = str(rec.get("_uuid") or rec.get("_id"))
            clean = data_pipeline.normalize_submission(rec)
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

        df = data_pipeline.build_dataframe(project, apply_recoding=False)
        data_pipeline.sync_variable_meta(project, df)
        if project.dedup_key_column:
            data_pipeline.detect_and_flag_duplicates(project)

        messages.success(request, f"Synchronisation réussie ({source_label}) : {len(raw)} soumissions reçues, {created} nouvelles.")
    except kobo_client.KoboAPIError as e:
        messages.error(request, f"Échec de la synchronisation Kobo : {e}")
    except Exception as e:
        messages.error(request, f"Erreur inattendue : {e}")
    return redirect("project_detail", pk=pk)


@login_required
def project_upload(request, pk):
    project = _get_project(request, pk)
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                df = data_pipeline.load_uploaded_file(request.FILES["file"])
                for i, row in df.iterrows():
                    Submission.objects.create(
                        project=project, kobo_uuid=f"upload-{i}",
                        data=json.loads(row.to_json(force_ascii=False)),
                    )
                data_pipeline.sync_variable_meta(project, df)
                messages.success(request, f"{len(df)} lignes importées avec succès.")
            except Exception as e:
                messages.error(request, f"Erreur d'import : {e}")
    return redirect("project_detail", pk=pk)


@login_required
def project_variables(request, pk):
    project = _get_project(request, pk)
    variables = VariableMeta.objects.filter(project=project).order_by("name")
    if request.method == "POST":
        for v in variables:
            v.label = request.POST.get(f"label_{v.id}", v.label)
            v.var_type = request.POST.get(f"type_{v.id}", v.var_type)
            recoding_raw = request.POST.get(f"recoding_{v.id}", "").strip()
            if recoding_raw:
                try:
                    v.recoding_map = json.loads(recoding_raw)
                except json.JSONDecodeError:
                    messages.warning(request, f"Recodage invalide (JSON) pour {v.name}, ignoré.")
            v.is_filterable = request.POST.get(f"filterable_{v.id}") == "on"
            v.save()
        messages.success(request, "Variables mises à jour.")
        return redirect("project_variables", pk=pk)
    return render(request, "core/project_variables.html", {"project": project, "variables": variables})


@login_required
def project_duplicates(request, pk):
    project = _get_project(request, pk)
    n = data_pipeline.detect_and_flag_duplicates(project)
    messages.info(request, f"{n} doublon(s) détecté(s) et exclus des analyses (clé : {project.dedup_key_column or 'non définie'}).")
    return redirect("project_detail", pk=pk)


# ----------------------------------------------------------------- Analyses
@login_required
def descriptive_view(request, pk):
    project = _get_project(request, pk)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    variables = {v.name: v.var_type for v in VariableMeta.objects.filter(project=project)}
    lang = _lang(request)
    ctx = {"project": project, "columns": list(df.columns), "filterable": _filterable_vars(project),
           "filters": _get_filters(request, project), "lang": lang}

    var = request.GET.get("var")
    if var and var in df.columns:
        vtype = variables.get(var, "categorielle")
        ctx["var"] = var
        if vtype in ("numerique",):
            desc = stats_engine.describe_numeric(pd.to_numeric(df[var], errors="coerce"))
            fig = plt_i.histogram(pd.to_numeric(df[var], errors="coerce"), title=f"Distribution de {var}", xlabel=var)
            ctx["table_html"] = desc.to_html(index=False, classes="table table-sm table-striped")
            ctx["chart_html"] = plt_i.fig_to_html_div(fig)
            ctx["text"] = interpretation.interpret_descriptive(var, desc, lang)
            ctx["kind"] = "numeric"
        else:
            freq = stats_engine.frequency_table(df[var])
            fig = plt_i.bar_chart(freq, title=f"Répartition de {var}")
            ctx["table_html"] = freq.to_html(index=False, classes="table table-sm table-striped")
            ctx["chart_html"] = plt_i.fig_to_html_div(fig)
            ctx["text"] = interpretation.interpret_frequency(var, freq, lang)
            ctx["kind"] = "categorical"

    return render(request, "core/descriptive.html", ctx)


@login_required
def descriptive_add(request, pk):
    project = _get_project(request, pk)
    var = request.GET.get("var")
    lang = _lang(request)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    variables = {v.name: v.var_type for v in VariableMeta.objects.filter(project=project)}
    report = _get_or_create_report(project, request.user)
    vtype = variables.get(var, "categorielle")

    if vtype == "numerique":
        desc = stats_engine.describe_numeric(pd.to_numeric(df[var], errors="coerce"))
        fig = plotting_static_hist(df, var)
        text = interpretation.interpret_descriptive(var, desc, lang)
        _append_blocks(report, [
            {"type": "heading", "content": f"Statistiques descriptives — {var}"},
            _table_block(desc, f"Tableau. Statistiques descriptives de {var}"),
            _image_block(fig, f"Figure. Distribution de {var}"),
            {"type": "text", "content": text},
        ])
    else:
        freq = stats_engine.frequency_table(df[var])
        fig = plotting_static.bar_chart(freq, title=f"Répartition de {var}")
        text = interpretation.interpret_frequency(var, freq, lang)
        _append_blocks(report, [
            {"type": "heading", "content": f"Statistiques descriptives — {var}"},
            _table_block(freq, f"Tableau. Répartition de {var}"),
            _image_block(fig, f"Figure. Répartition de {var}"),
            {"type": "text", "content": text},
        ])
    messages.success(request, "Ajouté au rapport.")
    return redirect(f"{reverse('descriptive', args=[pk])}?var={var}")


def plotting_static_hist(df, var):
    return plotting_static.histogram(pd.to_numeric(df[var], errors="coerce"), title=f"Distribution de {var}", xlabel=var)


def _table_block(df, caption):
    return {"type": "table", "content": {"columns": list(df.columns), "data": df.astype(str).values.tolist()}, "caption": caption}


def _image_block(fig, caption):
    png_bytes = plotting_static.fig_to_bytes(fig).getvalue()
    return {"type": "image", "content": base64.b64encode(png_bytes).decode("ascii"), "caption": caption}


def _append_blocks(report, blocks):
    report.blocks = (report.blocks or []) + blocks
    report.save()


@login_required
def crosstab_view(request, pk):
    project = _get_project(request, pk)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    lang = _lang(request)
    ctx = {"project": project, "columns": list(df.columns), "filterable": _filterable_vars(project),
           "filters": _get_filters(request, project), "lang": lang}

    v1, v2 = request.GET.get("var1"), request.GET.get("var2")
    if v1 and v2 and v1 in df.columns and v2 in df.columns and v1 != v2:
        res = stats_engine.crosstab_chi2(df[v1], df[v2])
        long_df = res["table_effectifs"].reset_index().melt(id_vars=v1, var_name=v2, value_name="Effectif")
        fig = plt_i.crosstab_bar(long_df, v1, v2, title=f"{v1} selon {v2}")
        ctx.update({
            "var1": v1, "var2": v2,
            "table_html": res["table_effectifs"].to_html(classes="table table-sm table-striped"),
            "pct_html": res["table_pourcentages"].to_html(classes="table table-sm table-striped"),
            "chart_html": plt_i.fig_to_html_div(fig),
            "chi2": res["chi2"], "ddl": res["ddl"], "p_value": res["p_value"], "cramers_v": res["cramers_v"],
            "text": interpretation.interpret_chi2(v1, v2, res, lang),
        })
        request.session["_last_crosstab"] = {"v1": v1, "v2": v2}
    return render(request, "core/crosstab.html", ctx)


@login_required
def crosstab_add(request, pk):
    project = _get_project(request, pk)
    lang = _lang(request)
    v1, v2 = request.GET.get("var1"), request.GET.get("var2")
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    report = _get_or_create_report(project, request.user)
    res = stats_engine.crosstab_chi2(df[v1], df[v2])
    long_df = res["table_effectifs"].reset_index().melt(id_vars=v1, var_name=v2, value_name="Effectif")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    import seaborn as _sns
    fig, ax = _plt.subplots(figsize=(6.5, 4))
    _sns.barplot(data=long_df, x=v1, y="Effectif", hue=v2, ax=ax)
    ax.set_title(f"{v1} selon {v2}", fontsize=12, fontweight="bold")
    _plt.xticks(rotation=25, ha="right")
    fig.tight_layout()
    text = interpretation.interpret_chi2(v1, v2, res, lang)
    _append_blocks(report, [
        {"type": "heading", "content": f"Tableau croisé — {v1} × {v2}"},
        _table_block(res["table_effectifs"].reset_index(), f"Tableau. Croisement {v1}/{v2} (effectifs)"),
        {"type": "text", "content": text},
    ])
    messages.success(request, "Ajouté au rapport.")
    return redirect(f"{reverse('crosstab', args=[pk])}?var1={v1}&var2={v2}")


@login_required
def compare_means_view(request, pk):
    project = _get_project(request, pk)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    lang = _lang(request)
    ctx = {"project": project, "columns": list(df.columns), "filterable": _filterable_vars(project),
           "filters": _get_filters(request, project), "lang": lang}

    num_var, group_var = request.GET.get("num_var"), request.GET.get("group_var")
    if num_var and group_var and num_var in df.columns and group_var in df.columns:
        df["_num"] = pd.to_numeric(df[num_var], errors="coerce")
        n_groups = df[group_var].dropna().nunique()
        fig = plt_i.boxplot_groups(df, "_num", group_var, title=f"{num_var} selon {group_var}")
        ctx.update({"num_var": num_var, "group_var": group_var, "chart_html": plt_i.fig_to_html_div(fig)})
        if n_groups == 2:
            res = stats_engine.ttest_independent(df["_num"], df[group_var])
            ctx["result"] = res
            ctx["text"] = interpretation.interpret_ttest(num_var, group_var, res, lang)
            ctx["test_used"] = "t"
        elif n_groups > 2:
            res = stats_engine.anova_oneway(df["_num"], df[group_var])
            ctx["table_html"] = res["table_groupes"].to_html(classes="table table-sm table-striped")
            ctx["result"] = res
            ctx["text"] = interpretation.interpret_anova(num_var, group_var, res, lang)
            ctx["test_used"] = "anova"
    return render(request, "core/compare_means.html", ctx)


@login_required
def compare_means_add(request, pk):
    project = _get_project(request, pk)
    lang = _lang(request)
    num_var, group_var = request.GET.get("num_var"), request.GET.get("group_var")
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    df["_num"] = pd.to_numeric(df[num_var], errors="coerce")
    report = _get_or_create_report(project, request.user)
    fig = plotting_static.boxplot_groups(df["_num"], df[group_var], title=f"{num_var} selon {group_var}",
                                          xlabel=group_var, ylabel=num_var)
    n_groups = df[group_var].dropna().nunique()
    blocks = [{"type": "heading", "content": f"Comparaison de moyennes — {num_var} selon {group_var}"},
              _image_block(fig, f"Figure. {num_var} selon {group_var}")]
    if n_groups == 2:
        res = stats_engine.ttest_independent(df["_num"], df[group_var])
        blocks.append({"type": "text", "content": interpretation.interpret_ttest(num_var, group_var, res, lang)})
    else:
        res = stats_engine.anova_oneway(df["_num"], df[group_var])
        blocks.append(_table_block(res["table_groupes"].reset_index(), "Tableau. Moyennes par groupe"))
        blocks.append({"type": "text", "content": interpretation.interpret_anova(num_var, group_var, res, lang)})
    _append_blocks(report, blocks)
    messages.success(request, "Ajouté au rapport.")
    return redirect(f"{reverse('compare_means', args=[pk])}?num_var={num_var}&group_var={group_var}")


@login_required
def correlation_view(request, pk):
    project = _get_project(request, pk)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    lang = _lang(request)
    ctx = {"project": project, "columns": list(df.columns), "filterable": _filterable_vars(project),
           "filters": _get_filters(request, project), "lang": lang}

    chosen = request.GET.getlist("vars")
    if len(chosen) >= 2:
        num_df = df[chosen].apply(pd.to_numeric, errors="coerce")
        method = request.GET.get("method", "pearson")
        corr, pvals = stats_engine.correlation_matrix(num_df, method=method)
        fig = plt_i.heatmap_corr(corr, title=f"Matrice de corrélation ({method})")
        texts = []
        for i, v1 in enumerate(chosen):
            for v2 in chosen[i + 1:]:
                texts.append(interpretation.interpret_correlation(v1, v2, corr.loc[v1, v2], pvals.loc[v1, v2], lang))
        ctx.update({"chosen": chosen, "method": method, "table_html": corr.to_html(classes="table table-sm table-striped"),
                    "chart_html": plt_i.fig_to_html_div(fig), "texts": texts})
    return render(request, "core/correlation.html", ctx)


@login_required
def correlation_add(request, pk):
    project = _get_project(request, pk)
    lang = _lang(request)
    chosen = request.GET.getlist("vars")
    method = request.GET.get("method", "pearson")
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    num_df = df[chosen].apply(pd.to_numeric, errors="coerce")
    corr, pvals = stats_engine.correlation_matrix(num_df, method=method)
    report = _get_or_create_report(project, request.user)
    fig = plotting_static.heatmap_corr(corr, title=f"Matrice de corrélation ({method})")
    blocks = [{"type": "heading", "content": "Analyse de corrélation"},
              _table_block(corr.reset_index(), "Tableau. Matrice de corrélation"),
              _image_block(fig, "Figure. Matrice de corrélation")]
    for i, v1 in enumerate(chosen):
        for v2 in chosen[i + 1:]:
            blocks.append({"type": "text", "content": interpretation.interpret_correlation(
                v1, v2, corr.loc[v1, v2], pvals.loc[v1, v2], lang)})
    _append_blocks(report, blocks)
    messages.success(request, "Ajouté au rapport.")
    qs = "&".join([f"vars={v}" for v in chosen]) + f"&method={method}"
    return redirect(f"{reverse('correlation', args=[pk])}?{qs}")


@login_required
def regression_view(request, pk):
    project = _get_project(request, pk)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    lang = _lang(request)
    ctx = {"project": project, "columns": list(df.columns), "filterable": _filterable_vars(project),
           "filters": _get_filters(request, project), "lang": lang}

    y_col = request.GET.get("y")
    x_cols = request.GET.getlist("x")
    if y_col and x_cols:
        num_df = df[[y_col] + x_cols].apply(pd.to_numeric, errors="coerce")
        summary, model = stats_engine.linear_regression(num_df, y_col, x_cols)
        ctx.update({"y_col": y_col, "x_cols": x_cols, "summary": summary,
                    "coef_html": summary["coef_table"].to_html(classes="table table-sm table-striped"),
                    "text": interpretation.interpret_regression(y_col, x_cols, summary, lang)})
        if len(x_cols) == 1:
            fig = plt_i.scatter_with_fit(num_df, x_cols[0], y_col, title=f"{y_col} en fonction de {x_cols[0]}")
            ctx["chart_html"] = plt_i.fig_to_html_div(fig)
    return render(request, "core/regression.html", ctx)


@login_required
def regression_add(request, pk):
    project = _get_project(request, pk)
    lang = _lang(request)
    y_col = request.GET.get("y")
    x_cols = request.GET.getlist("x")
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    num_df = df[[y_col] + x_cols].apply(pd.to_numeric, errors="coerce")
    summary, model = stats_engine.linear_regression(num_df, y_col, x_cols)
    report = _get_or_create_report(project, request.user)
    blocks = [{"type": "heading", "content": f"Régression linéaire — {y_col} ~ {' + '.join(x_cols)}"},
              _table_block(summary["coef_table"].reset_index(), "Tableau. Coefficients de régression")]
    if len(x_cols) == 1:
        fig = plotting_static.scatter_with_fit(num_df[x_cols[0]], num_df[y_col],
                                                title=f"{y_col} en fonction de {x_cols[0]}", xlabel=x_cols[0], ylabel=y_col)
        blocks.append(_image_block(fig, f"Figure. {y_col} en fonction de {x_cols[0]}"))
    blocks.append({"type": "text", "content": interpretation.interpret_regression(y_col, x_cols, summary, lang)})
    _append_blocks(report, blocks)
    messages.success(request, "Ajouté au rapport.")
    qs = f"y={y_col}&" + "&".join([f"x={v}" for v in x_cols])
    return redirect(f"{reverse('regression', args=[pk])}?{qs}")


@login_required
def reliability_view(request, pk):
    project = _get_project(request, pk)
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    lang = _lang(request)
    ctx = {"project": project, "columns": list(df.columns), "filterable": _filterable_vars(project),
           "filters": _get_filters(request, project), "lang": lang}

    items = request.GET.getlist("items")
    if len(items) >= 2:
        num_df = df[items].apply(pd.to_numeric, errors="coerce")
        res = stats_engine.cronbach_alpha(num_df)
        ctx.update({"items": items, "result": res,
                    "table_html": res["correlations_item_total"].to_html(index=False, classes="table table-sm table-striped"),
                    "text": interpretation.interpret_alpha(items, res, lang)})
    return render(request, "core/reliability.html", ctx)


@login_required
def reliability_add(request, pk):
    project = _get_project(request, pk)
    lang = _lang(request)
    items = request.GET.getlist("items")
    df = data_pipeline.build_dataframe(project, filters=_get_filters(request, project))
    num_df = df[items].apply(pd.to_numeric, errors="coerce")
    res = stats_engine.cronbach_alpha(num_df)
    report = _get_or_create_report(project, request.user)
    _append_blocks(report, [
        {"type": "heading", "content": f"Fiabilité de l'échelle ({', '.join(items)})"},
        _table_block(res["correlations_item_total"], "Tableau. Corrélations item-total"),
        {"type": "text", "content": interpretation.interpret_alpha(items, res, lang)},
    ])
    messages.success(request, "Ajouté au rapport.")
    qs = "&".join([f"items={v}" for v in items])
    return redirect(f"{reverse('reliability', args=[pk])}?{qs}")


# ----------------------------------------------------------------- Rapport
@login_required
def report_view(request, pk):
    project = _get_project(request, pk)
    report = _get_or_create_report(project, request.user)
    blocks = []
    for b in report.blocks:
        if b["type"] == "table":
            df = pd.DataFrame(b["content"]["data"], columns=b["content"]["columns"])
            blocks.append({"type": "table", "html": df.to_html(index=False, classes="table table-sm table-striped"), "caption": b.get("caption")})
        elif b["type"] == "image":
            blocks.append({"type": "image", "b64": b["content"], "caption": b.get("caption")})
        else:
            blocks.append(b)
    return render(request, "core/report.html", {"project": project, "report": report, "blocks": blocks})


@login_required
def report_clear(request, pk):
    project = _get_project(request, pk)
    report = _get_or_create_report(project, request.user)
    report.blocks = []
    report.save()
    messages.info(request, "Rapport vidé.")
    return redirect("report", pk=pk)


def _blocks_for_export(report):
    out = []
    for b in report.blocks:
        if b["type"] == "table":
            df = pd.DataFrame(b["content"]["data"], columns=b["content"]["columns"])
            out.append({"type": "table", "content": df, "caption": b.get("caption")})
        elif b["type"] == "image":
            out.append({"type": "image", "content": base64.b64decode(b["content"]), "caption": b.get("caption")})
        else:
            out.append(b)
    return out


@login_required
def report_word(request, pk):
    project = _get_project(request, pk)
    report = _get_or_create_report(project, request.user)
    buf = word_export.build_docx(_blocks_for_export(report), title=report.title, author=request.user.get_full_name() or request.user.username)
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    resp["Content-Disposition"] = f'attachment; filename="rapport_{project.pk}.docx"'
    return resp


@login_required
def report_pdf(request, pk):
    project = _get_project(request, pk)
    report = _get_or_create_report(project, request.user)
    buf = pdf_export.build_pdf(_blocks_for_export(report), title=report.title, author=request.user.get_full_name() or request.user.username)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="rapport_{project.pk}.pdf"'
    return resp
