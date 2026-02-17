import requests

PISTON_EXECUTE_URL = "https://execute.assignease.io/api/v2/execute"


class PistonService:
    @staticmethod
    def run_code(source_code: str, language: str, version: str, stdin: str = ""):
        """
        Call Piston API to execute code.

        :param source_code: The code to run
        :param language: Piston language name (e.g. 'python', 'javascript')
        :param version: Piston version (e.g. '3.10.0', '18.15.0')
        :param stdin: Input to pass to the program (single test case input)
        :return: dict with stdout, stderr, exit_code or error
        """
        payload = {
            "language": language,
            "version": version,
            "files": [
                {
                    "content": source_code
                }
            ],
            "stdin": stdin or ""
        }

        try:
            response = requests.post(PISTON_EXECUTE_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            run = data.get("run", {}) or {}

            return {
                "stdout": (run.get("stdout") or ""),
                "stderr": (run.get("stderr") or ""),
                "exit_code": run.get("code", -1),
            }
        except requests.exceptions.RequestException as e:
            # Network / API error
            return {
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }
