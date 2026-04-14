# =============================================================
#  security_acl.py — Q-Vault OS  |  ACL Security System
#
#  Access Control List system with permission management
# =============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time


class ACLAction(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class ACLResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    DENY_LOG = "deny_log"


@dataclass
class ACLRule:
    """Single ACL rule entry."""

    rule_id: int
    subject: str  # user or group
    resource: str  # path or resource name
    actions: list[ACLAction]
    result: ACLResult
    priority: int = 100
    created_at: float = field(default_factory=time.time)


class ACLSystem:
    """Access Control List system."""

    def __init__(self):
        self._next_rule_id = 1
        self._rules: list[ACLRule] = []
        self._default_deny = True
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Set up default ACL rules."""
        default_rules = [
            ACLRule(
                self._next_rule_id,
                "root",
                "*",
                [
                    ACLAction.READ,
                    ACLAction.WRITE,
                    ACLAction.EXECUTE,
                    ACLAction.DELETE,
                    ACLAction.ADMIN,
                ],
                ACLResult.ALLOW,
                priority=1000,
            ),
            ACLRule(
                self._next_rule_id,
                "admin",
                "*",
                [ACLAction.READ, ACLAction.WRITE, ACLAction.EXECUTE, ACLAction.ADMIN],
                ACLResult.ALLOW,
                priority=900,
            ),
            ACLRule(
                self._next_rule_id,
                "user",
                "/home/*",
                [ACLAction.READ, ACLAction.WRITE, ACLAction.EXECUTE],
                ACLResult.ALLOW,
                priority=100,
            ),
            ACLRule(
                self._next_rule_id,
                "user",
                "/tmp/*",
                [ACLAction.READ, ACLAction.WRITE, ACLAction.DELETE],
                ACLResult.ALLOW,
                priority=100,
            ),
            ACLRule(
                self._next_rule_id,
                "guest",
                "/public/*",
                [ACLAction.READ],
                ACLResult.ALLOW,
                priority=50,
            ),
        ]
        for rule in default_rules:
            self._rules.append(rule)

    def add_rule(
        self,
        subject: str,
        resource: str,
        actions: list[ACLAction],
        result: ACLResult = ACLResult.ALLOW,
        priority: int = 100,
    ) -> int:
        """Add a new ACL rule."""
        rule = ACLRule(
            rule_id=self._next_rule_id,
            subject=subject,
            resource=resource,
            actions=actions,
            result=result,
            priority=priority,
        )
        self._next_rule_id += 1
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        return rule.rule_id

    def remove_rule(self, rule_id: int) -> bool:
        """Remove an ACL rule."""
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                self._rules.pop(i)
                return True
        return False

    def check_permission(
        self, subject: str, resource: str, action: ACLAction
    ) -> tuple[bool, Optional[ACLRule]]:
        """
        Check if subject has permission for action on resource.
        Returns (allowed, matched_rule).
        """
        matched_rule = None

        for rule in self._rules:
            if not self._matches_subject(rule.subject, subject):
                continue
            if not self._matches_resource(rule.resource, resource):
                continue
            if action not in rule.actions:
                continue

            matched_rule = rule
            if rule.result == ACLResult.ALLOW:
                return True, rule
            elif rule.result == ACLResult.DENY:
                return False, rule
            elif rule.result == ACLResult.DENY_LOG:
                return False, rule

        if self._default_deny:
            return False, matched_rule
        return True, matched_rule

    def _matches_subject(self, pattern: str, subject: str) -> bool:
        """Check if subject matches pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern == subject:
            return True
        if pattern.endswith("*"):
            return subject.startswith(pattern[:-1])
        return False

    def _matches_resource(self, pattern: str, resource: str) -> bool:
        """Check if resource matches pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern == resource:
            return True
        if pattern.endswith("*"):
            return resource.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return resource.endswith(pattern[1:])
        return False

    def get_rules_for_subject(self, subject: str) -> list[ACLRule]:
        """Get all rules for a subject."""
        return [r for r in self._rules if self._matches_subject(r.subject, subject)]

    def get_rules_for_resource(self, resource: str) -> list[ACLRule]:
        """Get all rules for a resource."""
        return [r for r in self._rules if self._matches_resource(r.resource, resource)]

    def list_rules(self) -> list[ACLRule]:
        """List all ACL rules."""
        return self._rules.copy()

    def clear_rules(self):
        """Clear all non-default rules."""
        self._rules = [r for r in self._rules if r.priority >= 900]


ACL = ACLSystem()
