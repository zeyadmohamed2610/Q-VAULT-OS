import logging
import re
from typing import List, Dict, Any
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

# ── Phase 13.9: Intelligence Alignment ──
# Ensure observation and automation layers are active and listening
from system.shadow_logger import SHADOW_LOGGER
from system.automation_engine import AUTOMATION_ENGINE

class RiskTier:
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class ReasoningEngine:
    """
    v1.0 Psychological Calibration.
    Implements Security Sovereignty, Directional Advice, and Professional Silence.
    """
    SENSITIVITY_MAP = {
        "auth": 1.1, "security": 1.0, "sandbox": 0.9, "core": 0.8, 
        "engine": 0.8, "config": 0.7, "plugin": 0.6, "api": 0.6, 
        "utils": 0.3, "tests": 0.1
    }

    SECRET_PATTERNS = [
        (r'sk_live_[0-9a-zA-Z]{24}', "Stripe Live Secret Key"),
        (r'sk_test_[0-9a-zA-Z]{24}', "Stripe Test Secret Key"),
        (r'sk-[a-zA-Z0-9]{20,60}', "OpenAI/Generic API Key"),
        (r'AIza[0-9A-Za-z\-_]{30,45}', "Google API Key"),
        (r'ghp_[0-9a-zA-Z]{30,45}', "GitHub Personal Access Token"),
        (r'xox[baprs]-[0-9a-zA-Z]{10,48}', "Slack Token"),
        (r'-----BEGIN PRIVATE KEY-----', "RSA/ECC Private Key"),
        (r'(SECRET_KEY|API_KEY|ACCESS_TOKEN)\s*=\s*[\'"][^\'"]{10,}[\'"]', "Sensitive Variable Assignment"),
        (r'Authorization:\s*Bearer\s*[a-zA-Z0-9\._\-]{20,}', "Bearer Token Header")
    ]

    def summarize_diff(self, diff: str, context: Dict[str, Any]) -> Dict[str, Any]:
        impact_eval = self._evaluate_impact(diff, context)
        risks = self._detect_risks(diff, context)
        
        added_lines = [line[1:].strip() for line in diff.split('\n') if line.startswith('+') and not line.startswith('+++')]
        
        # v1.0: Expanded Security & Intent Override
        is_security_fix = context.get('is_security') or any(kw in str(added_lines).lower() for kw in ['security', 'bypass', 'interdict', 'safe', 'guard', 'permission', 'forbidden', 'unauthorized'])
        
        # Determine Impact Label
        impact_level = impact_eval['level']
        
        # v1.0: Risk Sovereignty
        if any(r['tier'] == RiskTier.CRITICAL for r in risks):
            impact_level = 'HIGH'
        elif risks and impact_level == 'LOW':
            impact_level = 'MEDIUM'
            
        if is_security_fix: impact_level = "HIGH"
        
        # Professional Silence Check (v1.0: Final Calibration)
        # Threshold raised to 0.42 to safely silence doc-edits in core files
        is_silent = (impact_level == 'LOW' and not risks and impact_eval['score'] < 0.42)
        
        # v1.0 Logic Override: Never silent on new structure
        if any(kw in str(added_lines) for kw in ['def ', 'class ']):
            is_silent = False
            if impact_level == 'LOW': impact_level = 'MEDIUM'
            
        decision = {
            "impact": {"level": impact_level, "score": impact_eval['score']},
            "risks": risks,
            "silent": is_silent,
            "decision": "SILENT" if is_silent else "INTERVENE",
            "security_override": is_security_fix,
            "logic_ratio": impact_eval['logic_ratio'],
            "annoyance": impact_eval['annoyance'],
            "filenames": context.get('filenames', []),
            "reason": "Negligible change detected." if is_silent else "Actionable logic change."
        }

        if is_silent:
            EVENT_BUS.emit(SystemEvent.DECISION_MADE, decision, source="ReasoningEngine")
            return {
                **decision,
                "internal_score": impact_eval['score']
            }
        
        # Confidence Drop on Chaos
        base_confidence = 0.85
        if len(set([f.split('.')[-1] for f in context.get('filenames', [])])) > 3:
            base_confidence -= 0.15
        if impact_eval['score'] > 2.0:
            base_confidence -= 0.10

        # Determine Intent
        verb = "Update"
        if any(kw in str(added_lines) for kw in ['def ', 'class ']):
            verb = "Implement" if "class " in str(added_lines) else "Refactor"
        if any(kw in str(added_lines).lower() for kw in ['fix', 'bug', 'error', 'resolve']):
            verb = "Fix"
            
        # v1.0: Clean Message (No [IMPACT] prefix)
        filenames = context.get('filenames', [])
        msg = f"{verb} "
        if len(filenames) == 1: msg += f"{filenames[0]} logic"
        elif len(filenames) > 0: msg += f"{filenames[0]} and {len(filenames)-1} others"
        else: msg += "workspace"

        decision["message"] = msg
        decision["confidence"] = round(base_confidence, 2)
        
        EVENT_BUS.emit(SystemEvent.DECISION_MADE, decision, source="ReasoningEngine")

        return {
            **decision,
            "internal_score": impact_eval['score']
        }

    def _evaluate_impact(self, diff: str, context: Dict[str, Any]) -> Dict[str, Any]:
        score = 0.0
        filenames = context.get('filenames', [])
        score += (len(filenames) * 0.15) 
        
        for fname in filenames:
            for key, weight in self.SENSITIVITY_MAP.items():
                if key in fname.lower(): score += weight; break
        
        lines_changed = len(diff.split('\n'))
        size_impact = min(0.5, lines_changed / 500) 
        score += size_impact
        
        # v1.0 Refined Logic Filter (Exclude comments strictly)
        added_lines = [l for l in diff.split('\n') if l.startswith('+') and not re.match(r'^\+?\s*(#|//|\*|""")', l)]
        logic_lines = [l for l in added_lines if any(c in l for c in ['=', '(', ':', '{', 'def ', 'class '])]
        
        logic_ratio = len(logic_lines) / (len(added_lines) + 1)
        score *= (0.35 + logic_ratio * 0.4) # v1.0 Final Calibration

        # v1.0 Annoyance Calculation (Stable Refinement)
        # High impact intervention for low logic changes = High Annoyance
        annoyance = score * (1 - logic_ratio)

        level = "LOW"
        if score > 1.0: level = "HIGH"
        elif score > 0.5: level = "MEDIUM"
        return {"score": round(score, 2), "level": level, "annoyance": annoyance, "logic_ratio": logic_ratio}

    def _detect_risks(self, diff: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        risks = []
        for pattern, label in self.SECRET_PATTERNS:
            if re.search(pattern, diff):
                risks.append({
                    "tier": RiskTier.CRITICAL, "msg": f"Actionable Alert: {label} detected.",
                    "recommendation": "Consider moving sensitive keys to environment variables (.env)."
                })

        added_lines = [l for l in diff.split('\n') if l.startswith('+')]
        for line in added_lines:
            if re.search(r'(print|console\.log)\s*\(', line):
                if any(kw in line.lower() for kw in ['token', 'key', 'auth', 'password', 'secret', 'cred']):
                    risks.append({
                        "tier": RiskTier.WARNING, "msg": f"Debug Alert: Sensitive variable printed.",
                        "recommendation": "Review and remove debug prints containing credentials."
                    })

        # v1.0 Directional Structural Advice
        filenames = context.get('filenames', [])
        if any(f.endswith(('.py', '.js')) for f in filenames) and not any('test' in f.lower() for f in filenames):
            if len(added_lines) > 20:
                risks.append({
                    "tier": RiskTier.WARNING, "msg": f"Strategy Alert: Logic modified in {filenames[0]} without test updates.",
                    "recommendation": f"Verifying structural changes in {filenames[0]} via your test suite is recommended."
                })

        return risks

REASONING_ENGINE = ReasoningEngine()
