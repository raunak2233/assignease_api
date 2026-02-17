from celery import shared_task
from django.utils import timezone
from .models import AIEvaluation
from .llm import call_qwen

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=20, retry_kwargs={'max_retries': 3})
def run_ai_evaluation(self, ai_eval_id):
    eval = AIEvaluation.objects.get(id=ai_eval_id)

    result = call_qwen(eval.question_text, eval.student_answer)

    eval.mistake_type = result.get("mistake_type")
    eval.ai_score = result.get("score")
    eval.confidence = result.get("confidence")
    eval.feedback = result.get("feedback")
    eval.raw_response = result
    eval.status = "done"
    eval.completed_at = timezone.now()
    eval.save()
