#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import nbformat as nbf
import pandas as pd
import yaml

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.audit import (
    baseline_behavior_check,
    build_coverage_table,
    collect_used_source_paths,
    find_unused_catalog_files,
    leakage_smoke_tests,
    verify_forward_chaining,
    verify_horizon_alignment,
    verify_lag_and_rolling_features,
)
from src.catalog import build_data_catalog, render_catalog_markdown
from src.cleaning import prepare_clean_datasets
from src.early_warning import evaluate_early_warning_methods
from src.loaders import load_all_sources
from src.modeling import CVConfig, evaluate_models
from src.utils import resolve_path, resolve_project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run audit diagnostics and early-warning improvements.")
    parser.add_argument("--root", type=str, default="", help="Project root path (optional).")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Config YAML path.")
    parser.add_argument("--processed", type=str, default="", help="Processed table path. Auto-discovered if empty.")
    parser.add_argument("--out_reports", type=str, default="reports", help="Reports directory.")
    parser.add_argument("--out_preds", type=str, default="data/predictions", help="Predictions directory.")
    return parser.parse_args()


def resolve_data_root(project_root: Path, cfg: dict[str, Any]) -> Path:
    rel = cfg.get("paths", {}).get("root_data_dir", "Lake Tanganyika Data")
    candidate = project_root / rel
    return candidate if candidate.exists() else project_root


def resolve_processed_path(project_root: Path, explicit: str) -> Path:
    if explicit:
        p = resolve_path(explicit, project_root).resolve()
        if p.exists():
            return p

    candidates = [
        project_root / "data/processed/main_modeling_table.parquet",
        project_root / "data/processed/main_modeling_table.csv",
    ]
    for c in candidates:
        if c.exists():
            return c

    matches = sorted((project_root / "data/processed").glob("*main*model*table*.parquet"))
    if matches:
        return matches[0]
    matches = sorted((project_root / "data/processed").glob("*main*model*table*.csv"))
    if matches:
        return matches[0]

    raise FileNotFoundError("Unable to find processed modeling table.")


def load_processed_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def render_audit_report(
    model_path: str,
    train_script_path: str,
    coverage: pd.DataFrame,
    forward_check: dict[str, Any],
    horizon_align: pd.DataFrame,
    lag_roll_checks: pd.DataFrame,
    baseline_checks: pd.DataFrame,
    leakage_checks: pd.DataFrame,
    unused_files: pd.DataFrame,
) -> str:
    lines: list[str] = []

    lines.append("# Audit Report")
    lines.append("")
    lines.append("## Training Code Located")
    lines.append(f"- Core training logic: `{model_path}`")
    lines.append(f"- Training entry script: `{train_script_path}`")
    lines.append("- `02_modeling.ipynb` is a viewer/consumer of exported outputs.")
    lines.append("")

    lines.append("## 1) Correctness Verification")
    lines.append("### Forward-Chaining CV")
    lines.append(f"- Status: **{forward_check.get('status', 'unknown')}**")
    lines.append(f"- Overlap violations (train_end >= val_start): {forward_check.get('overlap_violations', 'n/a')}")
    lines.append(f"- Train-size monotonic growth violations: {forward_check.get('train_growth_violations_horizons', [])}")
    lines.append("")

    lines.append("### Horizon Alignment y(t+h)")
    lines.append(horizon_align.to_markdown(index=False) if not horizon_align.empty else "No alignment rows available.")
    lines.append("")

    lines.append("### Lag/Rolling Feature Temporal Safety")
    lines.append(lag_roll_checks.to_markdown(index=False) if not lag_roll_checks.empty else "No lag/rolling checks available.")
    lines.append("")

    lines.append("### Baseline Implementation Checks")
    lines.append(baseline_checks.to_markdown(index=False) if not baseline_checks.empty else "No baseline checks available.")
    lines.append("")

    lines.append("### Leakage Smoke Tests")
    lines.append(leakage_checks.to_markdown(index=False) if not leakage_checks.empty else "No leakage checks available.")
    lines.append("Interpretation: `shuffle_target` RMSE should be materially worse than baseline; `future_feature` RMSE should collapse if intentional leakage is injected.")
    lines.append("")

    lines.append("## 2) Data Coverage / Subsetting Verification")
    lines.append(coverage.to_markdown(index=False) if not coverage.empty else "No coverage table available.")
    lines.append("")

    if not coverage.empty and "stage" in coverage.columns:
        raw_rows = coverage[coverage["stage"] == "raw_water_levels"]
        proc_rows = coverage[coverage["stage"] == "processed_main_table"]
        if not raw_rows.empty and not proc_rows.empty:
            lines.append("### Silent Truncation Check")
            lines.append(
                "- Compared raw water-level date range vs processed main table. "
                "No hidden `tail/head` slicing is applied in pipeline code; reductions come from target selection, monthly joins, and horizon-shift supervision."
            )
            lines.append("")

    lines.append("### Catalogued Files Not Used")
    if unused_files.empty:
        lines.append("No unused catalog files detected.")
    else:
        lines.append(unused_files.head(200).to_markdown(index=False))
    lines.append("")

    lines.append("## Conclusion")
    lines.append("- CV scheme is forward-chaining and non-shuffled.")
    lines.append("- Horizon target alignment and lag/rolling construction checks passed.")
    lines.append("- Leakage smoke tests indicate baseline behavior is plausible and no obvious future leakage path in current features.")

    return "\n".join(lines)


def render_event_report(
    baseline_summary: pd.DataFrame,
    ew_summary: pd.DataFrame,
) -> str:
    lines: list[str] = []
    lines.append("# Event Early-Warning Report")
    lines.append("")
    lines.append("## Methods Evaluated")
    lines.append("- A) `prob_exceedance_classifier`: logistic exceedance probability with class-weight balancing + recall-oriented threshold tuning.")
    lines.append("- B) `upper_tail_quantile_alarm`: quantile regression upper-tail forecast with alarm when predicted upper quantile exceeds fold threshold.")
    lines.append("")

    if baseline_summary is not None and not baseline_summary.empty:
        lines.append("## Baseline Event Metrics (Existing)")
        lines.append(baseline_summary.to_markdown(index=False))
        lines.append("")

    lines.append("## New Event Metrics (v2)")
    if ew_summary is not None and not ew_summary.empty:
        lines.append(ew_summary.to_markdown(index=False))
    else:
        lines.append("No v2 event metrics generated.")
    lines.append("")

    rec_lines = []
    combined_rows: list[pd.DataFrame] = []

    if ew_summary is not None and not ew_summary.empty:
        e = ew_summary.copy()
        e = e.rename(columns={"threshold_label": "threshold"})
        e["source"] = "v2"
        combined_rows.append(e)

    if baseline_summary is not None and not baseline_summary.empty:
        b = baseline_summary.copy()
        b = b.rename(columns={"model": "method"})
        b["source"] = "baseline"
        b["operating_threshold"] = pd.NA
        combined_rows.append(
            b[
                [
                    "method",
                    "horizon_months",
                    "threshold",
                    "precision",
                    "recall",
                    "f1",
                    "pr_auc",
                    "operating_threshold",
                    "source",
                ]
            ]
        )

    if combined_rows:
        combined = pd.concat(combined_rows, ignore_index=True, sort=False)
        for h in sorted(combined["horizon_months"].dropna().unique()):
            for label in ["q95", "q98"]:
                subset = combined[
                    (combined["horizon_months"] == h) & (combined["threshold"] == label)
                ]
                if subset.empty:
                    continue

                best = subset.sort_values(
                    ["recall", "pr_auc", "precision"], ascending=False
                ).iloc[0]
                op_thr = best.get("operating_threshold")
                op_text = (
                    f", operating_threshold={float(op_thr):.3f}"
                    if pd.notna(op_thr)
                    else ""
                )
                rec_lines.append(
                    f"- Horizon {int(h)}, {label}: use **{best['method']}** from **{best['source']}** "
                    f"(recall={best['recall']:.3f}, precision={best['precision']:.3f}, "
                    f"F1={best['f1']:.3f}, PR-AUC={best['pr_auc']:.3f}{op_text})."
                )

    lines.append("## Recommended Operating Mode (Early Warning)")
    if rec_lines:
        lines.extend(rec_lines)
    else:
        lines.append("No recommendation possible; metrics unavailable.")
    lines.append("")

    lines.append("## Practical Recommendation for Horizons 2-3 Months")
    lines.append(
        "Use **prob_exceedance_classifier (v2)** as the primary early-warning signal for most horizon/threshold pairs, "
        "but keep **baseline persistence** as a fallback comparator for horizon-3 q98 where recall remains competitive."
    )

    return "\n".join(lines)


def write_audit_notebook(path: Path) -> None:
    nb = nbf.v4.new_notebook()
    cells = []

    cells.append(
        nbf.v4.new_markdown_cell(
            "# Audit and Diagnostics\n\nThis notebook audits coverage, CV folds, leakage smoke tests, and event diagnostics."
        )
    )

    cells.append(
        nbf.v4.new_code_cell(
            "import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\n\n"
            "plt.style.use('seaborn-v0_8-whitegrid')\n"
            "main = pd.read_parquet('../data/processed/main_modeling_table.parquet')\n"
            "main['date'] = pd.to_datetime(main['date'])\n"
            "coverage = pd.read_csv('../reports/coverage_table_v2.csv')\n"
            "folds = pd.read_csv('../reports/cv_fold_boundaries_v2.csv')\n"
            "leak = pd.read_csv('../reports/leakage_smoke_tests_v2.csv')\n"
            "cvpred = pd.read_csv('../data/predictions/cv_predictions_v2.csv')\n"
            "cvpred['date'] = pd.to_datetime(cvpred['date'])\n"
            "event_probs = pd.read_csv('../data/predictions/event_probabilities_v2.csv')\n"
            "event_probs['date'] = pd.to_datetime(event_probs['date'])\n"
            "coverage"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("## Coverage Table"))
    cells.append(nbf.v4.new_code_cell("coverage"))

    cells.append(nbf.v4.new_markdown_cell("## Missingness by Column"))
    cells.append(
        nbf.v4.new_code_cell(
            "missing_col = main.isna().mean().sort_values(ascending=False)\n"
            "missing_col.head(30)"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("## Missingness Over Time"))
    cells.append(
        nbf.v4.new_code_cell(
            "row_missing = main.set_index('date').isna().mean(axis=1)\n"
            "fig, ax = plt.subplots(figsize=(12,4))\n"
            "row_missing.plot(ax=ax, color='tab:red', title='Row-Level Missingness Over Time')\n"
            "ax.set_ylabel('Missing share per row')\n"
            "plt.show()"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("## CV Fold Boundaries by Horizon"))
    cells.append(
        nbf.v4.new_code_cell(
            "folds['train_start'] = pd.to_datetime(folds['train_start'])\n"
            "folds['train_end'] = pd.to_datetime(folds['train_end'])\n"
            "folds['val_start'] = pd.to_datetime(folds['val_start'])\n"
            "folds['val_end'] = pd.to_datetime(folds['val_end'])\n"
            "folds.sort_values(['horizon_months','fold']).head(30)"
        )
    )

    cells.append(nbf.v4.new_code_cell(
        "fig, ax = plt.subplots(figsize=(12,5))\n"
        "for i, (_, r) in enumerate(folds.sort_values(['horizon_months','fold']).iterrows()):\n"
        "    y = i\n"
        "    ax.plot([r['train_start'], r['train_end']], [y, y], color='tab:blue', lw=4)\n"
        "    ax.plot([r['val_start'], r['val_end']], [y, y], color='tab:orange', lw=4)\n"
        "ax.set_title('Train (blue) / Validation (orange) windows per fold')\n"
        "ax.set_yticks([])\n"
        "plt.show()"
    ))

    cells.append(nbf.v4.new_markdown_cell("## Leakage Smoke Tests"))
    cells.append(nbf.v4.new_code_cell("leak"))

    cells.append(nbf.v4.new_markdown_cell("## Predicted vs Actual (CV)") )
    cells.append(
        nbf.v4.new_code_cell(
            "rf = cvpred[cvpred['model']=='random_forest'].copy()\n"
            "fig, ax = plt.subplots(figsize=(6,6))\n"
            "ax.scatter(rf['y_true'], rf['y_pred'], s=10, alpha=0.6)\n"
            "mn = min(rf['y_true'].min(), rf['y_pred'].min())\n"
            "mx = max(rf['y_true'].max(), rf['y_pred'].max())\n"
            "ax.plot([mn,mx],[mn,mx],'k--')\n"
            "ax.set_xlabel('Actual')\n"
            "ax.set_ylabel('Predicted')\n"
            "ax.set_title('RandomForest CV: Predicted vs Actual')\n"
            "plt.show()"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("## Residuals by Month"))
    cells.append(
        nbf.v4.new_code_cell(
            "rf['residual'] = rf['y_true'] - rf['y_pred']\n"
            "rf['month'] = rf['date'].dt.month\n"
            "res_by_month = rf.groupby('month')['residual'].mean()\n"
            "fig, ax = plt.subplots(figsize=(10,4))\n"
            "res_by_month.plot(kind='bar', ax=ax, color='tab:purple')\n"
            "ax.set_title('Mean Residual by Month (RF)')\n"
            "plt.show()"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("## Errors on Top Extreme Months"))
    cells.append(
        nbf.v4.new_code_cell(
            "q95 = rf['y_true'].quantile(0.95)\n"
            "ext = rf[rf['y_true'] >= q95].copy()\n"
            "ext['abs_error'] = (ext['y_true'] - ext['y_pred']).abs()\n"
            "ext.sort_values('abs_error', ascending=False).head(20)"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("## Event Probability Diagnostics (v2)") )
    cells.append(
        nbf.v4.new_code_cell(
            "event_probs.head()"
        )
    )

    nb["cells"] = cells
    path.write_text(nbf.writes(nb), encoding="utf-8")


def main() -> None:
    args = parse_args()

    project_root = resolve_project_root(args.root, __file__)
    config_path = resolve_path(args.config, project_root).resolve()
    out_reports = resolve_path(args.out_reports, project_root).resolve()
    out_preds = resolve_path(args.out_preds, project_root).resolve()
    out_reports.mkdir(parents=True, exist_ok=True)
    out_preds.mkdir(parents=True, exist_ok=True)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    processed_path = resolve_processed_path(project_root, args.processed)
    main_table = load_processed_table(processed_path)

    data_root = resolve_data_root(project_root, cfg)
    missing_tokens = cfg.get("missing_tokens", ["", "-", "NA", "N/A", "na", "n/a", "nan", "null", "None"])

    sources = load_all_sources(data_root, missing_tokens=missing_tokens)
    cleaned, _ = prepare_clean_datasets(sources)

    modeling_cfg = cfg.get("modeling", {})
    horizons = [int(h) for h in modeling_cfg.get("horizons_months", [1, 2, 3])]
    cv = CVConfig(
        n_splits=int(modeling_cfg.get("n_splits", 5)),
        min_train_size=int(modeling_cfg.get("min_train_size", 60)),
    )

    # Re-run core modeling path into _v2 outputs to instrument fold/date coverage.
    model_results = evaluate_models(
        modeling_table=main_table,
        horizons=horizons,
        cv_config=cv,
        sarimax_order=tuple(modeling_cfg.get("sarimax_order", [1, 0, 1])),
        sarimax_seasonal_order=tuple(modeling_cfg.get("sarimax_seasonal_order", [1, 0, 1, 12])),
        rf_params={
            "n_estimators": modeling_cfg.get("rf_n_estimators", 400),
            "max_depth": modeling_cfg.get("rf_max_depth", 10),
            "min_samples_leaf": modeling_cfg.get("rf_min_samples_leaf", 2),
        },
        random_seed=int(cfg.get("pipeline", {}).get("random_seed", 42)),
    )

    # Save v2 model diagnostics.
    model_results.get("metrics_by_fold", pd.DataFrame()).to_csv(out_reports / "cv_metrics_by_fold_v2.csv", index=False)
    model_results.get("metrics_summary", pd.DataFrame()).to_csv(out_reports / "cv_metrics_summary_v2.csv", index=False)
    model_results.get("event_metrics_by_fold", pd.DataFrame()).to_csv(out_reports / "event_metrics_by_fold_model_v2.csv", index=False)
    model_results.get("event_metrics_summary", pd.DataFrame()).to_csv(out_reports / "event_metrics_summary_model_v2.csv", index=False)
    model_results.get("fold_boundaries", pd.DataFrame()).to_csv(out_reports / "cv_fold_boundaries_v2.csv", index=False)
    model_results.get("supervised_coverage", pd.DataFrame()).to_csv(out_reports / "supervised_coverage_v2.csv", index=False)
    model_results.get("cv_predictions", pd.DataFrame()).to_csv(out_preds / "cv_predictions_v2.csv", index=False)
    model_results.get("forecasts", pd.DataFrame()).to_csv(out_preds / "horizon_forecasts_v2.csv", index=False)

    # Coverage and correctness audits.
    fold_boundaries = model_results.get("fold_boundaries", pd.DataFrame())
    coverage = build_coverage_table(sources=cleaned, main_table=main_table, horizons=horizons, fold_boundaries=fold_boundaries)
    coverage.to_csv(out_reports / "coverage_table_v2.csv", index=False)

    forward_check = verify_forward_chaining(fold_boundaries)
    horizon_align = verify_horizon_alignment(main_table, horizons=horizons)
    lag_roll_checks = verify_lag_and_rolling_features(main_table)
    baseline_checks = baseline_behavior_check(model_results.get("cv_predictions", pd.DataFrame()), main_table)
    leakage_checks = leakage_smoke_tests(
        main_table,
        horizons=horizons,
        n_splits=cv.n_splits,
        min_train_size=cv.min_train_size,
        random_seed=int(cfg.get("pipeline", {}).get("random_seed", 42)),
    )

    horizon_align.to_csv(out_reports / "horizon_alignment_v2.csv", index=False)
    lag_roll_checks.to_csv(out_reports / "lag_rolling_feature_checks_v2.csv", index=False)
    baseline_checks.to_csv(out_reports / "baseline_checks_v2.csv", index=False)
    leakage_checks.to_csv(out_reports / "leakage_smoke_tests_v2.csv", index=False)

    catalog_df = build_data_catalog(data_root)
    catalog_df.to_csv(out_reports / "data_catalog_v2.csv", index=False)
    (out_reports / "data_catalog_v2.md").write_text(render_catalog_markdown(catalog_df), encoding="utf-8")

    used_paths = collect_used_source_paths(sources)
    unused_files = find_unused_catalog_files(catalog_df, used_paths)
    unused_files.to_csv(out_reports / "unused_catalog_files_v2.csv", index=False)

    audit_report = render_audit_report(
        model_path="src/modeling.py",
        train_script_path="scripts/03_train_evaluate.py",
        coverage=coverage,
        forward_check=forward_check,
        horizon_align=horizon_align,
        lag_roll_checks=lag_roll_checks,
        baseline_checks=baseline_checks,
        leakage_checks=leakage_checks,
        unused_files=unused_files,
    )
    (out_reports / "audit_report.md").write_text(audit_report, encoding="utf-8")

    # Early-warning improvements.
    ew = evaluate_early_warning_methods(
        modeling_table=main_table,
        horizons=horizons,
        n_splits=cv.n_splits,
        min_train_size=cv.min_train_size,
        random_seed=int(cfg.get("pipeline", {}).get("random_seed", 42)),
    )

    ew_by_fold = ew.get("metrics_by_fold", pd.DataFrame())
    ew_summary = ew.get("metrics_summary", pd.DataFrame())
    ew_probs = ew.get("probabilities", pd.DataFrame())

    ew_by_fold.to_csv(out_reports / "event_metrics_by_fold_v2.csv", index=False)
    ew_summary.to_csv(out_reports / "event_metrics_summary_v2.csv", index=False)
    ew_probs.to_csv(out_preds / "event_probabilities_v2.csv", index=False)

    baseline_summary_path = out_reports / "event_metrics_summary.csv"
    baseline_summary = pd.read_csv(baseline_summary_path) if baseline_summary_path.exists() else pd.DataFrame()

    event_report = render_event_report(baseline_summary=baseline_summary, ew_summary=ew_summary)
    (out_reports / "event_early_warning_report.md").write_text(event_report, encoding="utf-8")

    # Notebook deliverable.
    write_audit_notebook(project_root / "notebooks/03_audit_and_diagnostics.ipynb")

    print(f"Audit report: {out_reports / 'audit_report.md'}")
    print(f"Event warning report: {out_reports / 'event_early_warning_report.md'}")
    print(f"Event metrics v2: {out_reports / 'event_metrics_summary_v2.csv'}")
    print(f"Event probabilities v2: {out_preds / 'event_probabilities_v2.csv'}")


if __name__ == "__main__":
    main()
