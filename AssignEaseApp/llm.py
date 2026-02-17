import requests
import json
import re
import time


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3:8b-instruct-q4_0"

PROMPT_TEMPLATE = """
You are an automatic programming assignment grader.

Your job is to judge correctness, not to teach or improve the code.

Follow this procedure strictly:

Step 1: Understand what the question asks.
Step 2: Understand exactly what the student wrote.
Step 3: Decide whether the student's answer fully satisfies the question.

Rules:
- Do NOT assume anything that is not written.
- Do NOT imagine missing code.
- Do NOT suggest improvements.
- Do NOT change the student's solution.
- If the answer is correct, accept it even if it could be written better.
- If the answer is incorrect, identify the main reason.

Mistake types:
- "syntax"  → the code is invalid in its language
- "logic"   → the approach does not solve the problem
- "output"  → the approach is correct but the output is wrong
- "none"    → fully correct

Scoring:
- 10 → fully correct
- 7  → minor mistake
- 4  → partially correct
- 0  → wrong

Return ONLY valid JSON and nothing else.

Format:
{
  "mistake_type": "syntax|logic|output|none",
  "confidence": 0.0 to 1.0,
  "score": 0 to 10,
  "feedback": "short explanation"
}

Question:
{{QUESTION}}

Student answer:
{{ANSWER}}
"""


class AIGradingError(Exception):
    pass

def call_qwen(question: str, answer: str, retries: int = 1) -> dict:
    prompt = PROMPT_TEMPLATE.replace("{{QUESTION}}", question).replace("{{ANSWER}}", answer)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "top_p": 1,
            "repeat_penalty": 1,
            "num_predict": 256,
        },
    }

    last_error = None

    for attempt in range(retries + 1):
        try:
            res = requests.post(OLLAMA_URL, json=payload, timeout=180)

            if res.status_code != 200:
                raise AIGradingError(f"Ollama HTTP {res.status_code}: {res.text}")

            data = res.json()

            if "error" in data:
                raise AIGradingError(f"Ollama error: {data['error']}")

            raw = data.get("response", "").strip()

            if not raw:
                raise AIGradingError("AI returned empty response")

            # Extract JSON from the response safely
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise AIGradingError(f"No JSON found in AI response:\n{raw[:500]}")

            result = json.loads(match.group())

            return normalize_ai_result(result)

        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(1)
                continue
            raise AIGradingError(f"AI grading failed: {str(last_error)}") from last_error


def normalize_ai_result(result: dict) -> dict:
    """
    Enforces internal consistency and sanity of AI output.
    """

    required = {"mistake_type", "confidence", "score", "feedback"}
    if not required.issubset(result.keys()):
        raise AIGradingError(f"Incomplete AI response: {result}")

    if result["mistake_type"] not in ["syntax", "logic", "output", "none"]:
        result["mistake_type"] = "logic"

    try:
        result["confidence"] = float(result["confidence"])
    except Exception:
        result["confidence"] = 0.5
    result["confidence"] = max(0.0, min(1.0, result["confidence"]))

    try:
        result["score"] = int(float(result["score"]))
    except Exception:
        result["score"] = 0
    result["score"] = max(0, min(10, result["score"]))

    if result["mistake_type"] == "none":
        result["score"] = max(result["score"], 8)
    else:
        result["score"] = min(result["score"], 7)

    if result["mistake_type"] == "syntax" and result["score"] > 5:
        result["score"] = 4

    fb = result.get("feedback", "").lower()
    if "instead of" in fb and "instead of" in fb.split("instead of")[-1]:
        result["feedback"] = "The answer does not match the required format."

    if not result.get("feedback"):
        result["feedback"] = "No explanation provided."

    return result
