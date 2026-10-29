"""Machine-readable validator result model (Blueprint §6).

Every validator returns a Result. Exit codes: 0 = PASS, 1 = FAIL, 2 = NOT_RUN (tool error or
missing prerequisite). NOT_RUN is never treated as PASS by the quality gate.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

BLOCK, WARN, INFO = "BLOCK", "WARN", "INFO"
EXIT = {"PASS": 0, "FAIL": 1, "NOT_RUN": 2}


@dataclass
class Finding:
    rule_id: str
    severity: str
    message: str
    path: str = ""
    line: int | None = None
    evidence: str = ""
    remediation: str = ""
    approved_by: str | None = None


@dataclass
class Result:
    validator: str
    status: str = "PASS"
    summary: str = ""
    findings: list[Finding] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)

    def add(self, *args, **kwargs) -> Finding:
        f = Finding(*args, **kwargs)
        self.findings.append(f)
        return f

    def finish(self) -> "Result":
        if self.status != "NOT_RUN":
            blocking = [f for f in self.findings if f.severity == BLOCK and not f.approved_by]
            self.status = "FAIL" if blocking else "PASS"
        counts = {s: sum(1 for f in self.findings if f.severity == s and not f.approved_by)
                  for s in (BLOCK, WARN, INFO)}
        approved = sum(1 for f in self.findings if f.approved_by)
        if not self.summary:
            self.summary = (f"{counts[BLOCK]} blocking, {counts[WARN]} warning(s), "
                            f"{counts[INFO]} info, {approved} approved")
        return self

    @classmethod
    def not_run(cls, validator: str, reason: str, **inputs) -> "Result":
        return cls(validator, status="NOT_RUN", summary=reason, inputs=inputs)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    def to_text(self) -> str:
        lines = [f"[{self.status}] {self.validator}: {self.summary}"]
        for f in self.findings:
            where = f"{f.path}:{f.line}" if f.line else f.path
            tag = f"APPROVED by {f.approved_by}" if f.approved_by else f.severity
            lines.append(f"  {tag:<8} {f.rule_id}  {where}  {f.message}")
        return "\n".join(lines)
