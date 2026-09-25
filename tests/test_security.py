"""Security / permission layer tests."""

from __future__ import annotations

from jarvis.security.permissions import (
    AutoApprover,
    DenyAllApprover,
    PermissionRequest,
    RiskLevel,
    SecurityPolicy,
)


def request(risk: RiskLevel, tool: str = "demo") -> PermissionRequest:
    return PermissionRequest(tool=tool, action=f"do {tool}", risk=risk, params={})


def test_low_risk_auto_approved():
    policy = SecurityPolicy(auto_approve_risk=RiskLevel.LOW)
    decision = policy.check(request(RiskLevel.LOW))
    assert decision.allowed and not decision.asked_user


def test_medium_asks_by_default_and_can_be_denied():
    policy = SecurityPolicy(auto_approve_risk=RiskLevel.LOW, approver=DenyAllApprover())
    decision = policy.check(request(RiskLevel.MEDIUM))
    assert not decision.allowed
    assert decision.asked_user
    assert "denied" in decision.reason


def test_medium_approved_by_approver():
    policy = SecurityPolicy(auto_approve_risk=RiskLevel.LOW, approver=AutoApprover())
    assert policy.check(request(RiskLevel.MEDIUM)).allowed
    assert policy.check(request(RiskLevel.HIGH)).allowed


def test_assume_yes_covers_medium_but_not_high():
    policy = SecurityPolicy(auto_approve_risk=RiskLevel.LOW, assume_yes=True)
    assert policy.check(request(RiskLevel.MEDIUM)).allowed
    high = policy.check(request(RiskLevel.HIGH))
    assert not high.allowed  # no approver -> denied


def test_no_approver_denies_asking_actions():
    policy = SecurityPolicy(auto_approve_risk=RiskLevel.LOW)
    assert not policy.check(request(RiskLevel.HIGH)).allowed


def test_auto_approve_medium_lets_medium_run():
    policy = SecurityPolicy(auto_approve_risk=RiskLevel.MEDIUM)
    assert policy.check(request(RiskLevel.MEDIUM)).allowed
    assert not policy.check(request(RiskLevel.HIGH)).allowed


def test_risk_level_parsing():
    assert RiskLevel.parse("low") == RiskLevel.LOW
    assert RiskLevel.parse("HIGH") == RiskLevel.HIGH
    try:
        RiskLevel.parse("extreme")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_risk_ordering():
    assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH
