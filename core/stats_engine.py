"""Moteur statistique : équivalents des fonctions SPSS/R les plus utilisées
dans un mémoire (descriptif, tris croisés, comparaisons de moyennes,
corrélation, régression, fiabilité)."""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols


# ---------------------------------------------------------------- Descriptif
def describe_numeric(series: pd.Series) -> pd.DataFrame:
    s = series.dropna()
    out = {
        "N": int(s.count()),
        "Manquants": int(series.isna().sum()),
        "Moyenne": round(s.mean(), 2),
        "Médiane": round(s.median(), 2),
        "Mode": round(s.mode().iloc[0], 2) if not s.mode().empty else np.nan,
        "Écart-type": round(s.std(), 2),
        "Variance": round(s.var(), 2),
        "Minimum": round(s.min(), 2),
        "Maximum": round(s.max(), 2),
        "Étendue": round(s.max() - s.min(), 2),
        "Asymétrie (skewness)": round(stats.skew(s), 2),
        "Aplatissement (kurtosis)": round(stats.kurtosis(s), 2),
    }
    return pd.DataFrame(out.items(), columns=["Indicateur", "Valeur"])


def frequency_table(series: pd.Series) -> pd.DataFrame:
    s = series.dropna()
    n_total = len(series)
    counts = s.value_counts().sort_index()
    pct = (counts / n_total * 100).round(1)
    valid_pct = (counts / len(s) * 100).round(1)
    cum_pct = valid_pct.cumsum().round(1)
    df = pd.DataFrame({
        "Modalité": counts.index.astype(str),
        "Effectif": counts.values,
        "Pourcentage (%)": pct.values,
        "Pourcentage valide (%)": valid_pct.values,
        "Pourcentage cumulé (%)": cum_pct.values,
    })
    return df


# ---------------------------------------------------------------- Croisé / Chi2
def crosstab_chi2(var1: pd.Series, var2: pd.Series):
    ct = pd.crosstab(var1, var2)
    ct_pct = pd.crosstab(var1, var2, normalize="index") * 100
    chi2, p, dof, expected = stats.chi2_contingency(ct)
    n = ct.values.sum()
    min_dim = min(ct.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else np.nan
    return {
        "table_effectifs": ct,
        "table_pourcentages": ct_pct.round(1),
        "chi2": round(chi2, 3),
        "ddl": dof,
        "p_value": p,
        "cramers_v": round(cramers_v, 3),
        "expected_ok": (expected >= 5).all(),
    }


# ---------------------------------------------------------------- Comparaison de moyennes
def ttest_independent(numeric: pd.Series, group: pd.Series):
    data = pd.DataFrame({"y": numeric, "g": group}).dropna()
    groups = data["g"].unique()
    if len(groups) != 2:
        raise ValueError("Le test t nécessite exactement 2 groupes.")
    g1 = data[data["g"] == groups[0]]["y"]
    g2 = data[data["g"] == groups[1]]["y"]
    levene_stat, levene_p = stats.levene(g1, g2)
    equal_var = levene_p > 0.05
    t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=equal_var)
    return {
        "groupes": [str(groups[0]), str(groups[1])],
        "n1": len(g1), "n2": len(g2),
        "moy1": round(g1.mean(), 2), "moy2": round(g2.mean(), 2),
        "sd1": round(g1.std(), 2), "sd2": round(g2.std(), 2),
        "levene_p": round(levene_p, 4),
        "variances_egales": equal_var,
        "t": round(t_stat, 3),
        "ddl": len(g1) + len(g2) - 2,
        "p_value": p_val,
    }


def anova_oneway(numeric: pd.Series, group: pd.Series):
    data = pd.DataFrame({"y": numeric, "g": group}).dropna()
    model = ols("y ~ C(g)", data=data).fit()
    table = sm.stats.anova_lm(model, typ=2)
    groups_desc = data.groupby("g")["y"].agg(["count", "mean", "std"]).round(2)
    f_stat = table["F"].iloc[0]
    p_val = table["PR(>F)"].iloc[0]
    return {"table_groupes": groups_desc, "F": round(f_stat, 3), "p_value": p_val,
            "ddl_entre": int(table["df"].iloc[0]), "ddl_intra": int(table["df"].iloc[1])}


# ---------------------------------------------------------------- Corrélation
def correlation_matrix(df_num: pd.DataFrame, method="pearson"):
    corr = df_num.corr(method=method)
    n = len(df_num)
    pvals = pd.DataFrame(np.ones(corr.shape), columns=corr.columns, index=corr.index)
    for i in corr.columns:
        for j in corr.columns:
            if i != j:
                sub = df_num[[i, j]].dropna()
                if method == "pearson":
                    _, p = stats.pearsonr(sub[i], sub[j])
                else:
                    _, p = stats.spearmanr(sub[i], sub[j])
                pvals.loc[i, j] = p
    return corr.round(3), pvals.round(4)


# ---------------------------------------------------------------- Régression
def linear_regression(df: pd.DataFrame, y_col: str, x_cols: list):
    data = df[[y_col] + x_cols].dropna()
    X = sm.add_constant(data[x_cols])
    y = data[y_col]
    model = sm.OLS(y, X).fit()
    coef_table = pd.DataFrame({
        "Coefficient (B)": model.params.round(3),
        "Erreur std": model.bse.round(3),
        "t": model.tvalues.round(3),
        "p-value": model.pvalues,
        "IC 95% inf": model.conf_int()[0].round(3),
        "IC 95% sup": model.conf_int()[1].round(3),
    })
    summary = {
        "r2": round(model.rsquared, 3),
        "r2_ajuste": round(model.rsquared_adj, 3),
        "f_stat": round(model.fvalue, 3),
        "f_pvalue": model.f_pvalue,
        "n": int(model.nobs),
        "coef_table": coef_table,
    }
    return summary, model


# ---------------------------------------------------------------- Fiabilité
def cronbach_alpha(df_items: pd.DataFrame):
    df_items = df_items.dropna()
    k = df_items.shape[1]
    item_vars = df_items.var(axis=0, ddof=1)
    total_var = df_items.sum(axis=1).var(ddof=1)
    alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)

    item_total = {}
    for col in df_items.columns:
        rest = df_items.drop(columns=[col]).sum(axis=1)
        item_total[col] = round(df_items[col].corr(rest), 3)

    return {
        "alpha": round(alpha, 3),
        "n_items": k,
        "n_obs": len(df_items),
        "correlations_item_total": pd.DataFrame(
            item_total.items(), columns=["Item", "Corrélation item-total corrigée"]
        ),
    }
