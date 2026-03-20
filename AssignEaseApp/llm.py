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

class AIGenerationError(Exception):
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


def generate_database_assignment(questions_list: list) -> dict:
    """
    Generate database schema and questions from natural language descriptions using AI.
    
    Args:
        questions_list: List of question descriptions in natural language
        
    Returns:
        dict with keys:
        - schema_sql: CREATE TABLE statements
        - sample_data_sql: INSERT statements
        - questions: List of generated questions with expected results
    """

    # Create simple, direct prompt
    q_list = "\n".join([f"- {q}" for q in questions_list])
    
    prompt = f"""Generate a database assignment. Return ONLY valid JSON.

Questions to create:
{q_list}

Return this JSON structure:
{{"schema_sql":"CREATE TABLE...; CREATE TABLE...;","sample_data_sql":"INSERT INTO...;","questions":[{{"question_text":"What is...","question_type":"select","expected_query":"SELECT...","expected_result":[{{"col":"val"}}]}}]}}

Create realistic SQL schemas with sample data. Each question must have question_text, question_type (select), expected_query, and expected_result array.
All SQL must work in SQLite. Return ONLY JSON, no explanation."""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 1,
            "repeat_penalty": 1.1,
            "num_predict": 4000,  # Increased to allow more tokens for complete response
        },
    }

    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=120)

        if res.status_code != 200:
            raise AIGradingError(f"Ollama HTTP {res.status_code}: {res.text[:200]}")

        data = res.json()

        if "error" in data:
            raise AIGradingError(f"Ollama error: {data['error']}")

        raw = data.get("response", "").strip()

        if not raw:
            raise AIGradingError("AI returned empty response")

        # Find the first { and try to parse from there
        start_idx = raw.find('{')
        if start_idx == -1:
            raise AIGradingError(f"No JSON found. Response starts with: {raw[:100]}")

        # Extract from first { to the end, but try to parse valid JSON
        remaining = raw[start_idx:]
        result = None
        best_result = None
        best_keys = 0
        last_error = None
        
        # Try to parse by finding matching closing brace
        # Prepare field mappings for normalization
        field_mappings = {
            "schemas_sql": "schema_sql",      # Handle plural typo
            "schema": "schema_sql",            # Handle shorthand
            "ddl": "schema_sql",               # Handle alternate naming
            "sample_data": "sample_data_sql",  # Handle shorthand
            "test_data": "sample_data_sql",    # Handle alternate naming
            "data_sql": "sample_data_sql",     # Handle alternate naming
            "question": "questions",           # Handle singular typo
            "question_list": "questions",      # Handle alternate naming
        }

        brace_count = 0
        for i, char in enumerate(remaining):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found matching brace, try to parse
                    json_str = remaining[:i+1]
                    try:
                        candidate = json.loads(json_str)
                        
                        # Normalize field names immediately after parsing
                        for old_key, new_key in field_mappings.items():
                            if old_key in candidate and new_key not in candidate:
                                candidate[new_key] = candidate.pop(old_key)
                        
                        # Count how many required keys it has
                        keys_found = sum(1 for k in ["schema_sql", "sample_data_sql", "questions"] if k in candidate)
                        if keys_found > best_keys:
                            best_keys = keys_found
                            best_result = candidate
                        if keys_found == 3:  # All required keys found
                            result = candidate
                            break
                    except json.JSONDecodeError as e:
                        last_error = f"Parse failed at char {i}: {str(e)[:50]}"
                        continue

        if not result and best_result:
            # Use the best partial result, but warn about it
            result = best_result
            missing = [k for k in ["schema_sql", "sample_data_sql", "questions"] if k not in result]
            raise AIGradingError(f"Incomplete response - missing: {missing}. Found {list(result.keys())}")

        if not result:
            # Try to repair incomplete JSON
            attempt_repair = remaining.rstrip()
            
            # If response ends with an unclosed string, close it
            in_string = False
            escape_next = False
            last_quote_pos = -1
            
            for i, char in enumerate(attempt_repair):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"':
                    in_string = not in_string
                    last_quote_pos = i
            
            # If we ended while in a string, close it
            if in_string:
                attempt_repair += '"'
            
            # Now add missing closing braces and brackets
            open_braces = attempt_repair.count('{') - attempt_repair.count('}')
            open_brackets = attempt_repair.count('[') - attempt_repair.count(']')
            
            if open_braces > 0 or open_brackets > 0:
                repair_str = ']' * open_brackets + '}' * open_braces
                attempt_repair += repair_str
                
                try:
                    result = json.loads(attempt_repair)
                    
                    # Normalize field names
                    for old_key, new_key in field_mappings.items():
                        if old_key in result and new_key not in result:
                            result[new_key] = result.pop(old_key)
                    
                except json.JSONDecodeError:
                    pass  # Fall through to error below
            
            if not result:
                raise AIGradingError(f"Could not parse JSON. Response too short or malformed. Response chars 0-300: {remaining[:300]}")



        # Validate result structure (normalization already happened above)
        if not all(key in result for key in ["schema_sql", "sample_data_sql", "questions"]):
            missing = [k for k in ["schema_sql", "sample_data_sql", "questions"] if k not in result]
            raise AIGradingError(f"Missing keys: {missing}. Has: {list(result.keys())}")

        if not isinstance(result.get("questions"), list) or len(result["questions"]) == 0:
            raise AIGradingError("Questions not a non-empty list")

        return result

    except json.JSONDecodeError as e:
        raise AIGradingError(f"JSON parse error: {str(e)}")
    except Exception as e:
        raise AIGradingError(f"Database assignment generation failed: {str(e)}") from e
