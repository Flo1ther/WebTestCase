from django.core.management.base import BaseCommand
from apps.ai_assistant.benchmark import run_benchmark
from apps.ai_assistant.models import AIBenchmarkRun


class Command(BaseCommand):
    help="Runs the versioned deterministic AI QA benchmark and persists metrics."
    def handle(self,*args,**kwargs):
        metrics,details=run_benchmark()
        run=AIBenchmarkRun.objects.create(provider="deterministic",model_name="qa-review-rules-v1",metrics=metrics,details=details)
        self.stdout.write(self.style.SUCCESS(f"Benchmark #{run.id}: precision={metrics['precision']} recall={metrics['recall']} f1={metrics['f1']}"))
