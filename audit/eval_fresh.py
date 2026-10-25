from code.main import run_pipeline
from code.evaluation.main import evaluate_predictions

run_pipeline('dataset/sample_deletion_requests.csv', 'audit/test_eval_output.csv')
res = evaluate_predictions('audit/test_eval_output.csv', 'dataset/sample_output.csv')
print("\n=== FRESH EVALUATION RESULTS ===")
for k, v in res.items():
    print(f"  {k}: {v}")
