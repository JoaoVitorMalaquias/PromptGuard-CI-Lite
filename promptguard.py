import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "data" / "eval_cases.json"
DEFAULT_PROMPT = ROOT / "prompts" / "system_prompt.txt"
DEFAULT_BASELINE = ROOT / "baseline.json"
DEFAULT_RESULTS = ROOT / "reports" / "results.json"
DEFAULT_DASHBOARD = ROOT / "reports" / "dashboard.html"


def normalize(text):
    without_accents = "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents).strip()


def load_policy(path):
    policy = {}
    current_label = None

    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_label = line[1:-1].strip()
            policy[current_label] = []
            continue
        if current_label:
            policy[current_label].extend(
                normalize(keyword.strip())
                for keyword in line.split(",")
                if keyword.strip()
            )

    if "FORA_ESCOPO" not in policy:
        policy["FORA_ESCOPO"] = []

    return policy


def classify(question, prompt_path=DEFAULT_PROMPT):
    normalized_question = normalize(question)
    policy = load_policy(prompt_path)
    scores = {}

    for label, keywords in policy.items():
        score = 0
        for keyword in keywords:
            if keyword and keyword in normalized_question:
                score += 2 if " " in keyword or "/" in keyword else 1
        scores[label] = score

    best_label = max(scores, key=scores.get)
    if scores[best_label] == 0:
        return "FORA_ESCOPO"
    return best_label


def expected_label(case):
    assertions = case.get("assert", [])
    for assertion in assertions:
        if assertion.get("type") == "equals":
            return assertion.get("value")
    raise ValueError(f"Caso sem assert equals: {case.get('description', 'sem descricao')}")


def evaluate(cases_path, baseline_path, output_path, dashboard_path, max_regression):
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    rows = []
    passed = 0

    for case in cases:
        question = case.get("vars", {}).get("question", "")
        expected = expected_label(case)
        actual = classify(question)
        ok = actual == expected
        passed += int(ok)
        rows.append({
            "id": case.get("description", ""),
            "question": question,
            "expected": expected,
            "actual": actual,
            "passed": ok,
        })

    total = len(cases)
    accuracy = passed / total if total else 0
    baseline_accuracy = float(baseline.get("accuracy", 0))
    regression = baseline_accuracy - accuracy
    status = "passed" if regression <= max_regression else "failed"

    result = {
        "project": "PromptGuard CI Lite",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_accuracy": baseline_accuracy,
        "current_accuracy": accuracy,
        "regression": regression,
        "max_regression": max_regression,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "status": status,
        "cases": rows,
    }

    output_path = Path(output_path)
    dashboard_path = Path(dashboard_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    dashboard_path.write_text(render_dashboard(result), encoding="utf-8")

    print(f"PromptGuard CI Lite: {passed}/{total} casos aprovados")
    print(f"Baseline: {baseline_accuracy:.0%} | Atual: {accuracy:.0%} | Regressao: {regression:.0%}")
    print(f"Status: {status.upper()}")

    return 0 if status == "passed" else 1


def render_dashboard(result):
    status_label = "APROVADO" if result["status"] == "passed" else "BLOQUEADO"
    status_class = "passed" if result["status"] == "passed" else "failed"
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(row['id'])}</td>"
        f"<td>{escape(row['question'])}</td>"
        f"<td>{escape(row['expected'])}</td>"
        f"<td>{escape(row['actual'])}</td>"
        f"<td>{'OK' if row['passed'] else 'REGRESSAO'}</td>"
        "</tr>"
        for row in result["cases"]
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PromptGuard CI Lite - Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; background: #f7f8fa; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #52616b; margin-top: 0; }}
    .summary {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 24px 0; }}
    .card {{ background: white; border: 1px solid #d8dee4; border-radius: 8px; padding: 16px; }}
    .label {{ color: #52616b; font-size: 13px; }}
    .value {{ font-size: 24px; font-weight: 700; margin-top: 6px; }}
    .passed {{ color: #146c43; }}
    .failed {{ color: #b42318; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8dee4; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f6; }}
    @media (max-width: 900px) {{ .summary {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <h1>PromptGuard CI Lite</h1>
    <p class="meta">Dashboard de regressao gerado em {escape(result['generated_at'])}</p>

    <section class="summary">
      <div class="card"><div class="label">Status</div><div class="value {status_class}">{status_label}</div></div>
      <div class="card"><div class="label">Acuracia atual</div><div class="value">{result['current_accuracy']:.0%}</div></div>
      <div class="card"><div class="label">Baseline</div><div class="value">{result['baseline_accuracy']:.0%}</div></div>
      <div class="card"><div class="label">Regressao</div><div class="value">{result['regression']:.0%}</div></div>
      <div class="card"><div class="label">Casos aprovados</div><div class="value">{result['passed']}/{result['total']}</div></div>
    </section>

    <table>
      <thead>
        <tr>
          <th>Caso</th>
          <th>Pergunta</th>
          <th>Esperado</th>
          <th>Obtido</th>
          <th>Resultado</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </main>
</body>
</html>
"""


def build_parser():
    parser = argparse.ArgumentParser(description="PromptGuard CI Lite")
    subparsers = parser.add_subparsers(dest="command", required=True)

    answer_parser = subparsers.add_parser("answer", help="classifica uma pergunta")
    answer_parser.add_argument("question")

    provider_parser = subparsers.add_parser("provider", help="provider local para Promptfoo")
    provider_parser.add_argument("args", nargs=argparse.REMAINDER)

    eval_parser = subparsers.add_parser("evaluate", help="executa regression eval")
    eval_parser.add_argument("--cases", default=str(DEFAULT_CASES))
    eval_parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    eval_parser.add_argument("--output", default=str(DEFAULT_RESULTS))
    eval_parser.add_argument("--dashboard", default=str(DEFAULT_DASHBOARD))
    eval_parser.add_argument("--max-regression", type=float, default=0.10)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "answer":
        print(classify(args.question))
        return 0

    if args.command == "provider":
        prompt = args.args[0] if args.args else ""
        print(classify(prompt))
        return 0

    if args.command == "evaluate":
        return evaluate(
            cases_path=args.cases,
            baseline_path=args.baseline,
            output_path=args.output,
            dashboard_path=args.dashboard,
            max_regression=args.max_regression,
        )

    return 2


if __name__ == "__main__":
    sys.exit(main())
