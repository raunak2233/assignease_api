import threading
from django.utils import timezone
from .models import AIEvaluation
from .llm import call_qwen

def run_ai_background(ai_eval_id):
    def task():
        eval = AIEvaluation.objects.get(id=ai_eval_id)

        try:
            result = call_qwen(eval.question_text, eval.student_answer)

            eval.mistake_type = result.get("mistake_type")
            eval.ai_score = result.get("score")
            eval.confidence = result.get("confidence")
            eval.feedback = result.get("feedback")
            eval.raw_response = result
            eval.status = "done"
            eval.completed_at = timezone.now()

        except Exception as e:
            eval.status = "error"
            eval.error = str(e)

        eval.save()

    threading.Thread(target=task, daemon=True).start()
