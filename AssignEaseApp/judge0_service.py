import requests
import time
from django.conf import settings

JUDGE0_BASE_URL = "https://tcase.assignease.io"

class Judge0Service:
    @staticmethod
    def get_language_id(language_name_or_id):
        """Map language names to Judge0 language IDs, or return ID if already numeric"""
        # If it's already a number (language ID), return it
        if isinstance(language_name_or_id, int):
            return language_name_or_id
        
        # Try to convert to int if it's a string number
        try:
            return int(language_name_or_id)
        except (ValueError, TypeError):
            pass
        
        # Otherwise, map language name to ID
        language_map = {
            'python': 71,      # Python 3.8.1
            'javascript': 63,  # JavaScript (Node.js 12.14.0)
            'java': 62,        # Java (OpenJDK 13.0.1)
            'cpp': 54,         # C++ (GCC 9.2.0)
            'c': 50,           # C (GCC 9.2.0)
            'csharp': 51,      # C# (Mono 6.6.0.161)
            'php': 68,         # PHP (7.4.1)
            'typescript': 74,  # TypeScript (3.7.4)
        }
        return language_map.get(str(language_name_or_id).lower(), 71)
    
    @staticmethod
    def submit_code(source_code, language_id, stdin, expected_output, timeout=2, memory_limit=128000):
        """Submit code to Judge0 for execution"""
        url = f"{JUDGE0_BASE_URL}/submissions?base64_encoded=false&wait=true"
        
        # Ensure language_id is an integer
        if not isinstance(language_id, int):
            language_id = Judge0Service.get_language_id(language_id)
        
        payload = {
            "source_code": source_code,
            "language_id": language_id,
            "stdin": stdin,
            "cpu_time_limit": timeout,
            "memory_limit": memory_limit,
        }
         
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_submission_result(token):
        """Get submission result by token"""
        url = f"{JUDGE0_BASE_URL}/submissions/{token}?base64_encoded=false"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    @staticmethod
    def evaluate_testcase(source_code, language_id, testcase):
        """Evaluate a single test case"""
        result = Judge0Service.submit_code(
            source_code=source_code,
            language_id=language_id,
            stdin=testcase.input,
            expected_output=testcase.expected_output,
            timeout=testcase.timeout,
            memory_limit=testcase.memory_limit
        )
        
        if "error" in result:
            return {
                "status": "error",
                "error_message": result["error"],
                "passed": False,
                "actual_output": ""
            }
        
        status_id = result.get("status", {}).get("id")
        status_desc = result.get("status", {}).get("description", "Unknown")
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        compile_output = result.get("compile_output", "")
        
        # Trim outputs for comparison
        actual_output_trimmed = stdout.strip() if stdout else ""
        expected_output_trimmed = testcase.expected_output.strip() if testcase.expected_output else ""
        
        # Status IDs: 3=Accepted, 4=Wrong Answer, 5=Time Limit Exceeded, 6=Compilation Error, etc.
        # Mark as passed only if status is Accepted AND outputs match
        passed = (status_id == 3) and (actual_output_trimmed == expected_output_trimmed)
        
        # Build meaningful error message
        error_message = ""
        if stderr:
            error_message = stderr
        elif compile_output:
            error_message = compile_output
        elif status_id != 3:
            error_message = status_desc
        
        return {
            "status": "passed" if passed else "failed",
            "passed": passed,
            "actual_output": stdout,
            "execution_time": result.get("time"),
            "memory_used": result.get("memory"),
            "error_message": error_message,
            "judge0_token": result.get("token")
        }
