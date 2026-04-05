"""
Safety and Governance Framework
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class ActionCategory(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"
    DATABASE = "database"


@dataclass
class SafetyRule:
    """A safety rule for validating actions."""
    name: str
    description: str
    pattern: str = ""
    action_categories: list[ActionCategory] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    blocked_tools: list[str] = field(default_factory=list)
    max_file_size: int = 0  # 0 = unlimited
    requires_approval: bool = False
    severity: SafetyLevel = SafetyLevel.BLOCKED


@dataclass
class ValidationResult:
    """Result of safety validation."""
    allowed: bool
    safety_level: SafetyLevel = SafetyLevel.SAFE
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    requires_approval: bool = False
    metadata: dict = field(default_factory=dict)


class SafetyValidator:
    """
    Safety validation and governance framework.
    
    Features:
    - Pre-execution action validation
    - Permission system
    - Audit logging
    - Circuit breakers
    - Human-in-the-loop checkpoints
    """
    
    def __init__(self):
        self._rules = []
        self._audit_log = []
        self._circuit_breaker_triggered = False
        self._failure_count = 0
        self._max_failures = 10
        self._window_seconds = 300  # 5 minute window
        
        # Register default safety rules
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default safety rules."""
        
        # Block dangerous commands
        self.add_rule(SafetyRule(
            name="block_dangerous_commands",
            description="Block potentially dangerous shell commands",
            pattern=r"(rm\s+-rf|mkfs|dd\s+if|chmod\s+777|>\s*/dev/sd)",
            action_categories=[ActionCategory.SYSTEM],
            severity=SafetyLevel.BLOCKED,
            blocked_tools=["execute_command"]
        ))
        
        # Require approval for file deletion
        self.add_rule(SafetyRule(
            name="file_deletion_approval",
            description="Require approval for file deletion operations",
            pattern=r"(rm\s+|del\s+|unlink)",
            action_categories=[ActionCategory.WRITE],
            requires_approval=True,
            severity=SafetyLevel.WARNING
        ))
        
        # Limit database writes
        self.add_rule(SafetyRule(
            name="limit_db_writes",
            description="Limit direct database write operations",
            pattern=r"(DROP\s+TABLE|TRUNCATE|ALTER\s+TABLE)",
            action_categories=[ActionCategory.DATABASE],
            severity=SafetyLevel.BLOCKED
        ))
        
        # Network restrictions
        self.add_rule(SafetyRule(
            name="network_safety",
            description="Validate network requests",
            action_categories=[ActionCategory.NETWORK],
            severity=SafetyLevel.WARNING
        ))
        
        # File size limits
        self.add_rule(SafetyRule(
            name="file_size_limit",
            description="Limit file operation sizes",
            max_file_size=100 * 1024 * 1024,  # 100MB
            severity=SafetyLevel.WARNING
        ))
    
    def add_rule(self, rule: SafetyRule):
        """Add a safety rule."""
        self._rules.append(rule)
        logger.info(f"Added safety rule: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """Remove a safety rule."""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                return True
        return False
    
    async def validate_action(self, step, context: dict) -> ValidationResult:
        """Validate an action before execution."""
        
        # Check circuit breaker
        if self._circuit_breaker_triggered:
            return ValidationResult(
                allowed=False,
                safety_level=SafetyLevel.BLOCKED,
                message="Circuit breaker triggered - too many failures"
            )
        
        action = step.action
        parameters = step.parameters
        
        warnings = []
        requires_approval = False
        safety_level = SafetyLevel.SAFE
        blocked = False
        
        # Check each rule
        for rule in self._rules:
            # Pattern matching
            if rule.pattern:
                action_str = f"{action} {json.dumps(parameters)}"
                if re.search(rule.pattern, action_str, re.IGNORECASE):
                    if rule.severity == SafetyLevel.BLOCKED:
                        blocked = True
                        logger.warning(f"Action blocked by rule: {rule.name}")
                    elif rule.severity == SafetyLevel.DANGEROUS:
                        safety_level = SafetyLevel.DANGEROUS
                    elif rule.severity == SafetyLevel.WARNING:
                        warnings.append(rule.description)
                        if safety_level != SafetyLevel.DANGEROUS:
                            safety_level = SafetyLevel.WARNING
                    
                    if rule.requires_approval:
                        requires_approval = True
            
            # Blocked tools
            if action in rule.blocked_tools:
                blocked = True
                logger.warning(f"Tool blocked: {action}")
            
            # File size check
            if rule.max_file_size > 0:
                if "content" in parameters and len(parameters["content"]) > rule.max_file_size:
                    blocked = True
                    logger.warning(f"File size exceeds limit: {rule.max_file_size}")
        
        # Log the validation
        self._log_audit(action, parameters, safety_level, blocked)
        
        # Update circuit breaker on failure
        if not blocked:
            self._failure_count = max(0, self._failure_count - 1)
        
        return ValidationResult(
            allowed=not blocked,
            safety_level=safety_level,
            message="Action allowed" if not blocked else "Action blocked by safety rules",
            warnings=warnings,
            requires_approval=requires_approval,
            metadata={"action": action, "rule_count": len(self._rules)}
        )
    
    def _log_audit(self, action: str, parameters: dict, safety_level: SafetyLevel, blocked: bool):
        """Log action to audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "parameters": self._sanitize_parameters(parameters),
            "safety_level": safety_level.value,
            "blocked": blocked
        }
        self._audit_log.append(entry)
        
        if blocked:
            self._failure_count += 1
            if self._failure_count >= self._max_failures:
                self._circuit_breaker_triggered = True
                logger.error("Circuit breaker triggered!")
    
    def _sanitize_parameters(self, parameters: dict) -> dict:
        """Sanitize parameters for logging (remove sensitive data)."""
        sensitive_keys = ["password", "token", "secret", "api_key", "key"]
        sanitized = {}
        
        for key, value in parameters.items():
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]
    
    def get_statistics(self) -> dict:
        """Get safety statistics."""
        total = len(self._audit_log)
        blocked = sum(1 for e in self._audit_log if e["blocked"])
        
        return {
            "total_actions": total,
            "blocked_actions": blocked,
            "block_rate": blocked / total if total > 0 else 0,
            "circuit_breaker_active": self._circuit_breaker_triggered,
            "failure_count": self._failure_count,
            "rules_count": len(self._rules)
        }
    
    def reset_circuit_breaker(self):
        """Reset the circuit breaker."""
        self._circuit_breaker_triggered = False
        self._failure_count = 0
        logger.info("Circuit breaker reset")
    
    def clear_audit_log(self):
        """Clear the audit log."""
        self._audit_log = []
