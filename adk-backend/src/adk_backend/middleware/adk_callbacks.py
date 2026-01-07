import re
from typing import Dict, Any, Optional

class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass

class CostError(Exception):
    """Raised when cost or step limits are exceeded."""
    pass

class SensitivityCallback:
    """
    ADK Policy Injection Implementation.
    Acts as a middleware/guardrail for Agent actions.
    """
    
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self.current_steps = 0

    def on_tool_start(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """
        Policy 1: Security Check (Path Traversal)
        Triggered before any tool execution.
        """
        # File System Access Check
        if tool_name in ["read_file", "write_file", "analyze_file"]:
            file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
            
            # Prevent accessing parent directories (Path Traversal)
            if ".." in file_path or file_path.startswith("/"):
                # Allow strictly defined safe directories if needed, otherwise block absolute/relative paths
                if not file_path.startswith("evidence/"): # Hypothetical safe verification
                    raise SecurityError(f"Access denied: restricted path '{file_path}' detected.")

    def on_agent_finish(self, response: str) -> str:
        """
        Policy 2: Privacy Check (PII Masking)
        Triggered before sending response to user.
        """
        # Regex for phone numbers (010-XXXX-XXXX or 010-XXX-XXXX or 010XXXXXXXX)
        phone_pattern = r"010[-.\s]?\d{3,4}[-.\s]?\d{4}"
        
        # Regex for resident registration numbers (XXXXXX-XXXXXXX) - Simplified
        rrn_pattern = r"\d{6}[-][1-4]\d{6}"

        masked_response = response
        
        # Apply Masking
        masked_response = re.sub(phone_pattern, "***-****-****", masked_response)
        masked_response = re.sub(rrn_pattern, "******-*******", masked_response)
        
        return masked_response

    def on_step_end(self, step_output: Any) -> None:
        """
        Policy 3: Cost Control (Infinite Loop Prevention)
        Triggered after each reasoning step.
        """
        self.current_steps += 1
        
        if self.current_steps > self.max_steps:
            raise CostError(
                f"Cost limit exceeded: Agent took more than {self.max_steps} steps. "
                "Halting to prevent billing explosion."
            )
