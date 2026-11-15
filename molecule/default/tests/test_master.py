"""Role tests for Istio and Calico application-layer policy."""
import json
import time

testinfra_hosts = ["master.osgiliath.test"]

ALP_NS = "alp-policy-test"
POLICY_SYNC_LOG = "Successfully connected to Policy Sync server"
POLL_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 5


def kubectl_json(host, command):
    with host.sudo():
        result = host.run(command)
    assert result.rc == 0, result.stderr
    return json.loads(result.stdout)


def kubectl(host, *args):
    with host.sudo():
        return host.run("kubectl " + " ".join(args))


def wait_until(description, check):
    """Poll check() until it reports success or the timeout expires."""
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    detail = None
    while time.monotonic() < deadline:
        ok, detail = check()
        if ok:
            return
        time.sleep(POLL_INTERVAL_SECONDS)
    raise AssertionError(f"Timed out waiting for {description}: {detail}")


def live_pods(host, namespace, selector):
    """Pods matching selector, excluding Terminating pods being replaced."""
    pods = kubectl_json(
        host,
        f"kubectl get pods -n {namespace} -l {selector} -o json",
    )["items"]
    return [
        pod
        for pod in pods
        if pod["metadata"].get("deletionTimestamp") is None
    ]


def dikastes_status(pod):
    for status in pod["status"].get("containerStatuses", []):
        if status["name"] == "dikastes":
            return status
    return None


def assert_dikastes_spec(pod):
    pod_spec = pod["spec"]
    containers = pod_spec["containers"]
    all_containers = containers + pod_spec.get("initContainers", [])
    dikastes = next(
        container
        for container in containers
        if container["name"] == "dikastes"
    )
    proxy = next(
        container
        for container in all_containers
        if container["name"] == "istio-proxy"
    )
    assert dikastes["image"] == "calico/calico:v3.33.0"
    assert {mount["mountPath"] for mount in dikastes["volumeMounts"]} >= {
        "/var/run/dikastes",
        "/var/run/felix",
    }
    assert "/var/run/dikastes" in {
        mount["mountPath"] for mount in proxy["volumeMounts"]
    }
    assert any(
        volume.get("csi", {}).get("driver") == "csi.tigera.io"
        for volume in pod_spec["volumes"]
    )


def pod_diagnostics(host, namespace, pod):
    """Failure detail: dikastes container state plus its recent logs."""
    name = pod["metadata"]["name"]
    detail = f"pod={name} dikastes_status={json.dumps(dikastes_status(pod))}"
    for previous in ([], ["--previous"]):
        result = kubectl(
            host,
            "logs",
            "-n",
            namespace,
            name,
            "-c",
            "dikastes",
            "--tail",
            "20",
            *previous,
        )
        label = " (previous)" if previous else ""
        detail += (
            f"\nkubectl logs{label} rc={result.rc}"
            f" stderr={result.stderr.strip()}\n{result.stdout.strip()}"
        )
    return detail


def test_istio_injector_has_both_dikastes_templates(host):
    configmap = kubectl_json(
        host,
        "kubectl get configmap istio-sidecar-injector "
        "-n istio-system -o json",
    )
    templates = "\n".join(configmap["data"].values())
    assert "dikastes:" in templates
    assert "dikastes-gateway:" in templates


def test_istio_gateways_have_ready_dikastes_containers(host):
    for app, template in (
        ("istio-ingressgateway", "sidecar,dikastes-gateway"),
        ("istio-egressgateway", "sidecar,dikastes-gateway"),
    ):
        deployment = kubectl_json(
            host,
            f"kubectl get deployment {app} -n istio-system -o json",
        )
        annotations = deployment["spec"]["template"]["metadata"][
            "annotations"
        ]
        assert annotations["inject.istio.io/templates"] == template

        def gateways_ready(app=app):
            pods = live_pods(host, "istio-system", f"app={app}")
            if not pods:
                return False, f"no live pods for {app}"
            not_ready = [
                pod["metadata"]["name"]
                for pod in pods
                if (dikastes_status(pod) or {}).get("ready") is not True
            ]
            if not_ready:
                return False, f"dikastes not ready on {not_ready}"
            return True, None

        wait_until(f"dikastes ready on {app}", gateways_ready)
        for pod in live_pods(host, "istio-system", f"app={app}"):
            assert_dikastes_spec(pod)


def test_application_layer_policy_allows_and_denies_http(host):
    deployment = kubectl_json(
        host,
        "kubectl get deployment alp-test-server "
        "-n alp-policy-test -o json",
    )
    annotations = deployment["spec"]["template"]["metadata"][
        "annotations"
    ]
    assert annotations["inject.istio.io/templates"] == "sidecar,dikastes"

    live = {}

    def server_ready():
        pods = live_pods(host, ALP_NS, "app=alp-test-server")
        if not pods:
            return False, "no live alp-test-server pods"
        pod = pods[0]
        status = dikastes_status(pod)
        if status is None or status["ready"] is not True:
            return False, pod_diagnostics(host, ALP_NS, pod)
        live["pod"] = pod
        return True, None

    wait_until("dikastes ready on the ALP test server", server_ready)
    for pod in live_pods(host, ALP_NS, "app=alp-test-server"):
        assert_dikastes_spec(pod)

    def dikastes_logging():
        result = kubectl(
            host,
            "logs",
            "-n",
            ALP_NS,
            live["pod"]["metadata"]["name"],
            "-c",
            "dikastes",
        )
        ok = result.rc == 0 and POLICY_SYNC_LOG in result.stdout
        detail = (
            f"rc={result.rc} stderr={result.stderr.strip()}"
            f"\n{result.stdout.strip()}"
        )
        return ok, detail

    wait_until("the dikastes policy sync log line", dikastes_logging)

    base = f"http://alp-test-server.{ALP_NS}.svc.cluster.local"

    def http_status(path, expected):
        def check():
            result = kubectl(
                host,
                "exec",
                "-n",
                ALP_NS,
                "deployment/alp-test-client",
                "-c",
                "client",
                "--",
                "curl",
                "--silent",
                "--show-error",
                "--output",
                "/dev/null",
                "--write-out",
                "%{http_code}",
                base + path,
            )
            ok = result.rc == 0 and result.stdout == expected
            detail = (
                f"rc={result.rc} code={result.stdout}"
                f" stderr={result.stderr.strip()}"
            )
            return ok, detail

        return check

    wait_until("HTTP 200 for GET /", http_status("/", "200"))
    wait_until(
        "HTTP 403 for GET /not-allowed",
        http_status("/not-allowed", "403"),
    )
