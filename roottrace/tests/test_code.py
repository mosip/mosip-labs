"""A pattern keeps one row, a throw site, and the services that shared its transaction id."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fake_loki import FakeLoki  # noqa: E402

from roottrace import engine  # noqa: E402
from roottrace.config import Config  # noqa: E402
from roottrace.loki import LogEntry  # noqa: E402
from roottrace.parser import app_frame, code_location, parse  # noqa: E402


def test_frames():
    line = ("2026-11-19 08:55:42,518 [http] ERROR "
            "[io.mosip.kernel.auth.service.TokenValidator].validate.188 : token rejected")
    ev = parse([LogEntry(1, {"namespace": "kernel", "app": "authmanager", "container": "authmanager", "pod": "p"}, line)])[0]
    assert ev.log_method == "validate" and ev.log_line == 188, (ev.log_method, ev.log_line)
    loc = code_location(ev)
    assert loc["class"] == "io.mosip.kernel.auth.service.TokenValidator"
    assert loc["line"] == 188 and loc["file"] is None

    stack = "\n".join([
        "io.mosip.authentication.service.AuthService: IDA-MLC-019 sign failed",
        "at org.springframework.web.client.RestTemplate.exchange(RestTemplate.java:40)",
        "at io.mosip.authentication.service.AuthService.authenticate(AuthService.java:210)",
        "Caused by: java.sql.SQLException: connection refused",
        "at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:12)",
        "at io.mosip.kernel.auth.service.TokenValidator.validate(TokenValidator.java:188)",
        "at io.mosip.authentication.controller.AuthController.auth(AuthController.java:40)",
    ])
    frame = app_frame(stack)
    assert frame["class"] == "io.mosip.kernel.auth.service.TokenValidator", frame
    assert frame["file"] == "TokenValidator.java" and frame["line"] == 188


def test_scan():
    now = time.time_ns()
    ida = {"namespace": "ida", "app": "ida-auth", "container": "ida-auth", "pod": "ida-auth-0"}
    km = {"namespace": "keymanager", "app": "keymanager", "container": "keymanager", "pod": "keymanager-0"}
    header = ("2026-11-19 10:00:00.000 ERROR 1 --- [t] io.mosip.authentication.service.AuthService : "
              "IDA-MLC-019 sign failed transactionId=TXN10042")
    rows = [
        (now - 3_000_000_000, km, "2026-11-19 10:00:00.000 ERROR 1 --- [t] i.m.k.Key : KER-KMS-012 failed transactionId=TXN10042"),
        (now - 2_000_000_000, ida, header),
        (now - 1_900_000_000, ida, "\tat org.springframework.web.client.RestTemplate.exchange(RestTemplate.java:40)"),
        (now - 1_800_000_000, ida, "\tat io.mosip.authentication.service.AuthService.authenticate(AuthService.java:210)"),
        (now - 1_000_000_000, ida, "2026-11-19 10:00:01.000 WARN 1 --- [t] i.m.a.AuthService : OTP retry scheduled"),
        (now - 900_000_000, ida, "2026-11-19 10:00:02.000 WARN 1 --- [t] i.m.a.AuthService : OTP retry scheduled"),
    ]
    fake = FakeLoki(rows)
    url = fake.start()
    try:
        cfg = Config()
        cfg.loki.url = url
        cfg.k8s.enabled = False
        result = engine.scan(cfg, now - 3600 * 10**9, now)
    finally:
        fake.stop()
    by_level = {i["level"]: i for i in result["issues"]}
    warn = by_level["WARN"]
    assert warn["count"] == 2 and warn["service"] == "ida-auth", warn
    err = next(i for i in result["issues"] if i["level"] == "ERROR" and i["service"] == "ida-auth")
    assert err["code"]["class"] == "io.mosip.authentication.service.AuthService", err["code"]
    assert err["code"]["file"] == "AuthService.java" and err["code"]["line"] == 210
    assert err["code"]["repo"].endswith("/id-authentication"), err["code"]
    assert err["path"] == ["keymanager", "ida-auth"], err["path"]
    assert err["code"]["snippet_note"] == "running commit was not read from the pod"
    assert warn["code"] is None and warn["code_note"] == "no stack in this window", warn


def main():
    test_frames()
    test_scan()
    print("CODE CHECKS PASSED")


if __name__ == "__main__":
    main()
