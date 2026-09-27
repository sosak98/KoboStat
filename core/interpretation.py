"""Génération de textes d'interprétation automatique, style rédaction de mémoire,
en français et en anglais."""


def p_to_text(p, lang="fr"):
    if lang == "fr":
        return "significatif (p < 0,05)" if p < 0.05 else "non significatif (p ≥ 0,05)"
    return "significant (p < .05)" if p < 0.05 else "not significant (p ≥ .05)"


def interpret_frequency(var_name, freq_df, lang="fr"):
    top = freq_df.sort_values("Effectif", ascending=False).iloc[0]
    n_total = freq_df["Effectif"].sum()
    if lang == "fr":
        return (
            f"L'analyse de la variable « {var_name} » (N = {n_total}) montre que la modalité "
            f"« {top['Modalité']} » est la plus représentée avec {int(top['Effectif'])} "
            f"observations, soit {top['Pourcentage valide (%)']} % des réponses valides."
        )
    return (
        f"The analysis of the variable '{var_name}' (N = {n_total}) shows that the category "
        f"'{top['Modalité']}' is the most represented with {int(top['Effectif'])} observations, "
        f"i.e. {top['Pourcentage valide (%)']}% of valid responses."
    )


def interpret_descriptive(var_name, desc_df, lang="fr"):
    d = dict(zip(desc_df["Indicateur"], desc_df["Valeur"]))
    if lang == "fr":
        return (
            f"La variable « {var_name} » présente une moyenne de {d['Moyenne']} "
            f"(écart-type = {d['Écart-type']}) sur {int(d['N'])} observations valides. "
            f"Les valeurs s'étendent de {d['Minimum']} à {d['Maximum']}."
        )
    return (
        f"The variable '{var_name}' has a mean of {d['Moyenne']} (SD = {d['Écart-type']}) "
        f"across {int(d['N'])} valid observations, ranging from {d['Minimum']} to {d['Maximum']}."
    )


def interpret_chi2(var1, var2, result, lang="fr"):
    p = result["p_value"]
    sig = p_to_text(p, lang)
    if lang == "fr":
        txt = (
            f"Le test du Khi-deux d'indépendance entre « {var1} » et « {var2} » donne "
            f"χ²({result['ddl']}) = {result['chi2']}, p = {p:.4f}, ce qui est {sig}. "
            f"Le V de Cramér, mesurant la force de l'association, est de {result['cramers_v']}."
        )
        if p < 0.05:
            txt += f" On peut donc conclure qu'il existe une association statistiquement significative entre « {var1} » et « {var2} »."
        else:
            txt += f" On ne peut donc pas conclure à une association statistiquement significative entre « {var1} » et « {var2} »."
        if not result["expected_ok"]:
            txt += " (Attention : certains effectifs théoriques sont inférieurs à 5, le test du Khi-deux peut être peu fiable.)"
        return txt
    else:
        txt = (
            f"A Chi-square test of independence between '{var1}' and '{var2}' shows "
            f"χ²({result['ddl']}) = {result['chi2']}, p = {p:.4f}, which is {sig}. "
            f"Cramér's V, measuring association strength, is {result['cramers_v']}."
        )
        return txt


def interpret_ttest(var_name, group_name, result, lang="fr"):
    p = result["p_value"]
    sig = p_to_text(p, lang)
    if lang == "fr":
        txt = (
            f"Le test t de Student comparant « {var_name} » entre les groupes "
            f"« {result['groupes'][0]} » (M = {result['moy1']}, ET = {result['sd1']}, n = {result['n1']}) "
            f"et « {result['groupes'][1]} » (M = {result['moy2']}, ET = {result['sd2']}, n = {result['n2']}) "
            f"donne t({result['ddl']}) = {result['t']}, p = {p:.4f}, résultat {sig}."
        )
        if p < 0.05:
            plus_haut = result["groupes"][0] if result["moy1"] > result["moy2"] else result["groupes"][1]
            txt += f" La différence de moyennes est statistiquement significative, en faveur du groupe « {plus_haut} »."
        else:
            txt += " La différence de moyennes observée n'est pas statistiquement significative."
        return txt
    else:
        return (
            f"Student's t-test comparing '{var_name}' between groups "
            f"'{result['groupes'][0]}' (M = {result['moy1']}, SD = {result['sd1']}) and "
            f"'{result['groupes'][1]}' (M = {result['moy2']}, SD = {result['sd2']}) "
            f"gives t({result['ddl']}) = {result['t']}, p = {p:.4f}, which is {sig}."
        )


def interpret_anova(var_name, group_name, result, lang="fr"):
    p = result["p_value"]
    sig = p_to_text(p, lang)
    if lang == "fr":
        return (
            f"L'ANOVA à un facteur comparant « {var_name} » selon « {group_name} » donne "
            f"F({result['ddl_entre']}, {result['ddl_intra']}) = {result['F']}, p = {p:.4f}, résultat {sig}. "
            + ("Il existe donc au moins une différence significative entre les groupes."
               if p < 0.05 else "Il n'existe donc pas de différence significative entre les groupes.")
        )
    return (
        f"A one-way ANOVA comparing '{var_name}' by '{group_name}' gives "
        f"F({result['ddl_entre']}, {result['ddl_intra']}) = {result['F']}, p = {p:.4f}, which is {sig}."
    )


def interpret_correlation(var1, var2, r, p, lang="fr"):
    if abs(r) < 0.1:
        force = "négligeable" if lang == "fr" else "negligible"
    elif abs(r) < 0.3:
        force = "faible" if lang == "fr" else "weak"
    elif abs(r) < 0.5:
        force = "modérée" if lang == "fr" else "moderate"
    else:
        force = "forte" if lang == "fr" else "strong"
    sens = ("positive" if r > 0 else "négative") if lang == "fr" else ("positive" if r > 0 else "negative")
    sig = p_to_text(p, lang)
    if lang == "fr":
        return (
            f"La corrélation entre « {var1} » et « {var2} » est {sens} et {force} "
            f"(r = {r}, p = {p:.4f}), résultat {sig}."
        )
    return f"The correlation between '{var1}' and '{var2}' is {sens} and {force} (r = {r}, p = {p:.4f}), which is {sig}."


def interpret_regression(y_col, x_cols, summary, lang="fr"):
    coef = summary["coef_table"]
    sig_vars = [v for v in x_cols if coef.loc[v, "p-value"] < 0.05]
    if lang == "fr":
        txt = (
            f"Le modèle de régression linéaire explique {summary['r2']*100:.1f} % de la variance de "
            f"« {y_col} » (R² = {summary['r2']}, R² ajusté = {summary['r2_ajuste']}), "
            f"F = {summary['f_stat']}, p = {summary['f_pvalue']:.4f}, sur {summary['n']} observations."
        )
        if sig_vars:
            txt += " Les variables suivantes ont un effet statistiquement significatif : " + ", ".join(
                f"« {v} » (B = {coef.loc[v, 'Coefficient (B)']}, p = {coef.loc[v, 'p-value']:.4f})" for v in sig_vars
            ) + "."
        else:
            txt += " Aucune variable explicative n'a d'effet statistiquement significatif au seuil de 5 %."
        return txt
    else:
        txt = (
            f"The linear regression model explains {summary['r2']*100:.1f}% of the variance in "
            f"'{y_col}' (R² = {summary['r2']}), F = {summary['f_stat']}, p = {summary['f_pvalue']:.4f}."
        )
        return txt


def interpret_alpha(items, result, lang="fr"):
    a = result["alpha"]
    if a >= 0.9:
        niveau = "excellente" if lang == "fr" else "excellent"
    elif a >= 0.8:
        niveau = "bonne" if lang == "fr" else "good"
    elif a >= 0.7:
        niveau = "acceptable" if lang == "fr" else "acceptable"
    elif a >= 0.6:
        niveau = "discutable" if lang == "fr" else "questionable"
    else:
        niveau = "faible" if lang == "fr" else "poor"
    if lang == "fr":
        return (
            f"L'échelle composée de {result['n_items']} items présente un coefficient Alpha de Cronbach "
            f"de {a}, ce qui traduit une fiabilité (cohérence interne) {niveau}."
        )
    return (
        f"The scale composed of {result['n_items']} items shows a Cronbach's Alpha of {a}, "
        f"indicating {niveau} internal consistency reliability."
    )
