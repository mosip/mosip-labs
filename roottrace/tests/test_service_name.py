"""Each workload keeps its own name. Sidecar logs do not inherit the app label."""
from roottrace.loki import LogEntry
from roottrace.parser import parse


def one(labels, line="2026-11-19 10:00:00.000 ERROR 1 --- [t] log : boom"):
    return parse([LogEntry(1, labels, line)], "app")[0]


def main():
    app = one({"namespace": "ida", "app": "ida-internal", "container": "ida-internal", "pod": "ida-internal-abc"})
    assert app.service == "ida-internal", app.service

    proxy = one({"namespace": "ida", "app": "ida-internal", "container": "istio-proxy", "pod": "ida-internal-abc"})
    assert proxy.service == "ida-internal/istio-proxy", proxy.service

    # The real process container can differ from the app label (istiod's container is discovery).
    pilot = one({"namespace": "istio-system", "app": "istiod", "container": "discovery", "pod": "istiod-0"})
    assert pilot.service == "istiod", pilot.service

    # Two namespaces can share an app value and still stay distinct.
    a = one({"namespace": "esignet", "app": "esignet", "container": "esignet", "pod": "esignet-a"})
    b = one({"namespace": "esignet162", "app": "esignet", "container": "esignet", "pod": "esignet-b"})
    assert a.service == b.service == "esignet"
    assert a.namespace != b.namespace

    print("SERVICE NAME CHECKS PASSED")


if __name__ == "__main__":
    main()
