# =============================================================
#  payment.py — Q-VAULT OS  |  Payment Integration (Simulated)
#
#  Features:
#    - Create checkout sessions
#    - Verify payments
#    - Activate licenses
# =============================================================

import os
import uuid
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


class Plan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PRICING = {
    "pro": {
        "monthly": 2.99,
        "yearly": 29.99,
        "features": [
            "cloud_sync",
            "telemetry_dashboard",
            "security_dashboard_advanced",
            "priority_updates",
            "plugin_api",
        ],
    },
    "enterprise": {
        "monthly": 9.99,
        "yearly": 99.99,
        "features": ["multi_user", "enterprise_support", "everything_in_pro"],
    },
}


@dataclass
class CheckoutSession:
    session_id: str
    plan: str
    billing_cycle: str
    amount: float
    currency: str
    status: str
    created_at: str
    expires_at: str
    checkout_url: str
    success_url: str


@dataclass
class PaymentResult:
    success: bool
    session_id: Optional[str]
    license_key: Optional[str]
    message: str
    plan: str


class PaymentSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._payments_dir = Path.home() / ".qvault" / "payments"
        self._payments_dir.mkdir(parents=True, exist_ok=True)

    def create_checkout_session(
        self, plan: str, billing_cycle: str = "yearly", customer_email: str = ""
    ) -> CheckoutSession:
        if plan not in PRICING:
            raise ValueError(f"Invalid plan: {plan}")

        if billing_cycle not in ["monthly", "yearly"]:
            raise ValueError(f"Invalid billing cycle: {billing_cycle}")

        pricing = PRICING[plan]
        amount = pricing[billing_cycle]

        session_id = f"cs_{uuid.uuid4().hex[:24]}"

        now = datetime.now()
        expires = now + timedelta(minutes=30)

        base_url = os.environ.get("APP_URL", "qvault://")

        checkout_url = f"{base_url}checkout/{session_id}"
        success_url = f"{base_url}payment/success?session_id={session_id}"

        session = CheckoutSession(
            session_id=session_id,
            plan=plan,
            billing_cycle=billing_cycle,
            amount=amount,
            currency="USD",
            status="pending",
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            checkout_url=checkout_url,
            success_url=success_url,
        )

        self._save_session(session)

        return session

    def _save_session(self, session: CheckoutSession):
        session_file = self._payments_dir / f"{session.session_id}.json"
        with open(session_file, "w") as f:
            json.dump(
                {
                    "session_id": session.session_id,
                    "plan": session.plan,
                    "billing_cycle": session.billing_cycle,
                    "amount": session.amount,
                    "currency": session.currency,
                    "status": session.status,
                    "created_at": session.created_at,
                    "expires_at": session.expires_at,
                },
                f,
                indent=2,
            )

    def _load_session(self, session_id: str) -> Optional[CheckoutSession]:
        session_file = self._payments_dir / f"{session_id}.json"
        if not session_file.exists():
            return None

        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                return CheckoutSession(**data)
        except Exception:
            return None

    def verify_payment(self, session_id: str) -> bool:
        session = self._load_session(session_id)
        if not session:
            return False

        if session.status == "completed":
            return True

        if datetime.fromisoformat(session.expires_at) < datetime.now():
            return False

        if SUPABASE_KEY:
            return self._verify_online(session_id)
        else:
            return self._simulate_payment(session_id)

    def _verify_online(self, session_id: str) -> bool:
        try:
            import requests

            url = f"{SUPABASE_URL}/rest/v1/payments"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
            params = {
                "select": "status",
                "session_id": f"eq.{session_id}",
                "status": "eq.completed",
                "limit": 1,
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200 and response.json():
                self._update_session_status(session_id, "completed")
                return True

        except Exception:
            pass

        return False

    def _simulate_payment(self, session_id: str) -> bool:
        time.sleep(1)

        self._update_session_status(session_id, "completed")
        return True

    def _update_session_status(self, session_id: str, status: str):
        session_file = self._payments_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                data["status"] = status
                with open(session_file, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

    def activate_license(self, session_id: str, user_email: str = "") -> PaymentResult:
        session = self._load_session(session_id)

        if not session:
            return PaymentResult(
                success=False,
                session_id=session_id,
                license_key=None,
                message="Session not found",
                plan="",
            )

        if session.status != "completed":
            if not self.verify_payment(session_id):
                return PaymentResult(
                    success=False,
                    session_id=session_id,
                    license_key=None,
                    message="Payment not completed",
                    plan=session.plan,
                )

        license_key = self._generate_license(session.plan)

        if SUPABASE_KEY:
            try:
                import requests

                url = f"{SUPABASE_URL}/rest/v1/licenses"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                }

                days = 365 if session.billing_cycle == "yearly" else 30
                expires_at = (datetime.now() + timedelta(days=days)).isoformat()

                license_data = {
                    "license_key": license_key,
                    "plan": session.plan,
                    "status": "active",
                    "expires_at": expires_at,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat(),
                }

                requests.post(url, headers=headers, json=license_data)

            except Exception:
                pass

        from system.license_manager import LICENSE_MGR

        LICENSE_MGR._activate_offline(license_key)

        return PaymentResult(
            success=True,
            session_id=session_id,
            license_key=license_key,
            message=f"{session.plan.title()} license activated!",
            plan=session.plan,
        )

    def _generate_license(self, plan: str) -> str:
        prefix = {"pro": "QVPRO", "enterprise": "QVEnt"}.get(plan, "QV")

        unique = f"{plan}-{uuid.uuid4().hex[:12]}-{int(time.time())}"
        key_hash = hashlib.sha256(unique.encode()).hexdigest()[:16]
        return f"{prefix}-{key_hash.upper()}"

    def get_subscription_status(self) -> Dict[str, Any]:
        from system.license_manager import LICENSE_MGR

        info = LICENSE_MGR.get_info()
        plan = info.plan

        if plan == "free":
            return {
                "plan": "free",
                "status": "active",
                "next_billing": None,
                "amount": 0,
            }

        days_remaining = 0
        if info.expires_at:
            expires = datetime.fromisoformat(info.expires_at.replace("Z", "+00:00"))
            days_remaining = max(0, (expires - datetime.now(expires.tzinfo)).days)

        return {
            "plan": plan,
            "status": info.status,
            "next_billing": info.expires_at,
            "days_remaining": days_remaining,
            "amount": PRICING.get(plan, {}).get("yearly", 0) if plan != "free" else 0,
        }

    def cancel_subscription(self) -> bool:
        from system.license_manager import LICENSE_MGR

        LICENSE_MGR.deactivate()
        return True


PAYMENT = PaymentSystem()
