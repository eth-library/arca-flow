"""Kubernetes commands: up, down, restart, status, logs, shell."""

import secrets
import string
import time
from pathlib import Path

import typer
from rich.status import Status

from arca_flow_cli.theme import ARROW, DASH, FAIL, OK, WARN, console
from arca_flow_cli.utils.run import run_capture, run_interactive, run_passthrough

app = typer.Typer(no_args_is_help=True)

# Deployment constants
NAMESPACE = "dagster"
RELEASE = "dagster"
IMAGE = "arca-flow:local"
HELM_CHART = "dagster/dagster"
HELM_VERSION = "1.10.14"
PG_SECRET_NAME = "dagster-postgresql"
DAGSTER_UI_URL = "http://localhost:8080"
K8S_CONTEXT = "docker-desktop"
ROLLOUT_TIMEOUT = "120s"
READY_TIMEOUT = 180  # seconds to wait for all pods to be ready
READY_POLL_INTERVAL = 3  # seconds between readiness checks


def _generate_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _check_k8s() -> bool:
    with Status("  Checking Kubernetes connectivity...", console=console):
        run_capture(["kubectl", "config", "use-context", K8S_CONTEXT], timeout=5)
        code, _ = run_capture(["kubectl", "cluster-info"], timeout=10)
    if code != 0:
        console.print(f"  {FAIL} Kubernetes not available. Enable it in Docker Desktop.")
        return False
    console.print(f"  {OK} Cluster connected ({K8S_CONTEXT})")
    return True


def _run_quiet_step(label: str, cmd: list[str]) -> bool:
    """Run a command with a spinner. Returns True on success."""
    with Status(f"  {label}...", console=console):
        code = run_passthrough(cmd)
    return code == 0


def _get_pending_pods() -> list[str]:
    """Return a list of human-readable statuses for pods that are not yet ready."""
    code, output = run_capture(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            NAMESPACE,
            "-o",
            "jsonpath="
            + "{range .items[*]}"
            + '{.metadata.name}{"|"}{.status.phase}{"|"}'
            + "{range .status.containerStatuses[*]}{.ready}{end}"
            + "{range .status.initContainerStatuses[*]}{.ready}{end}"
            + '{"\\n"}{end}',
        ]
    )
    if code != 0 or not output.strip():
        return ["unable to query pods"]
    pending: list[str] = []
    for line in output.strip().splitlines():
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        name, phase, readiness = parts
        # Short name: strip the "dagster-" prefix for readability
        short = name.removeprefix("dagster-")
        if phase != "Running" or not readiness or "false" in readiness:
            pending.append(f"{short} ({phase})")
    return pending


def _wait_for_pods(status_obj: Status) -> bool:
    """Wait for all pods in the namespace to be ready. Returns True on success."""
    start = time.monotonic()
    deadline = start + READY_TIMEOUT
    while time.monotonic() < deadline:
        pending = _get_pending_pods()
        if not pending:
            return True
        waiting_on = ", ".join(pending)
        elapsed = int(time.monotonic() - start)
        status_obj.update(f"  Waiting for pods ({elapsed}s): {waiting_on}")
        time.sleep(READY_POLL_INTERVAL)
    return False


@app.command()
def up() -> None:
    """Build and deploy to local Kubernetes."""
    console.print()
    console.print("  [title]Deploying to Kubernetes[/]")
    console.print()

    if not _check_k8s():
        raise typer.Exit(1)

    # Build Docker image
    console.print(f"  {ARROW} Building Docker image...")
    console.print()
    code = run_passthrough(["docker", "build", "-t", IMAGE, "."])
    console.print()
    if code != 0:
        console.print(f"  {FAIL} Docker build failed")
        raise typer.Exit(1)
    console.print(f"  {OK} Docker image built ({IMAGE})")

    # Create namespace (dry-run → apply)
    _, ns_yaml = run_capture(
        ["kubectl", "create", "namespace", NAMESPACE, "--dry-run=client", "-o", "yaml"]
    )
    run_capture(["kubectl", "apply", "-f", "-"], input=ns_yaml)
    console.print(f"  {OK} Namespace ready ({NAMESPACE})")

    # Create PostgreSQL secret if it doesn't exist
    code, _ = run_capture(["kubectl", "get", "secret", PG_SECRET_NAME, "-n", NAMESPACE])
    if code != 0:
        password = _generate_password()
        run_capture(
            [
                "kubectl",
                "create",
                "secret",
                "generic",
                PG_SECRET_NAME,
                f"--from-literal=postgresql-password={password}",
                "-n",
                NAMESPACE,
            ]
        )
        console.print(f"  {OK} PostgreSQL secret created")
    else:
        console.print(f"  {OK} PostgreSQL secret exists")

    # Helm repo
    run_capture(["helm", "repo", "add", "dagster", "https://dagster-io.github.io/helm"])
    run_capture(["helm", "repo", "update", "dagster"])
    console.print(f"  {OK} Helm repo updated")

    # Apply PVC
    code, _ = run_capture(["kubectl", "apply", "-n", NAMESPACE, "-f", "helm/pvc.yaml"])
    if code != 0:
        console.print(f"  {FAIL} Failed to apply PVC")
        raise typer.Exit(1)
    console.print(f"  {OK} PVC applied")

    # Create test data ConfigMap if test data exists
    if Path("arca_flow_tests/test_data").is_dir():
        _, cm_yaml = run_capture(
            [
                "kubectl",
                "create",
                "configmap",
                "test-data-xml",
                "--from-file=arca_flow_tests/test_data/",
                "-n",
                NAMESPACE,
                "--dry-run=client",
                "-o",
                "yaml",
            ]
        )
        run_capture(["kubectl", "apply", "-f", "-"], input=cm_yaml)
        console.print(f"  {OK} Test data ConfigMap created")

    # Deploy with Helm
    with Status(f"  Deploying with Helm v{HELM_VERSION}...", console=console):
        code, _ = run_capture(
            [
                "helm",
                "upgrade",
                "--install",
                RELEASE,
                HELM_CHART,
                "-f",
                "helm/values.yaml",
                "-f",
                "helm/values-local.yaml",
                "-n",
                NAMESPACE,
                "--version",
                HELM_VERSION,
                "--skip-schema-validation",
            ]
        )
    if code != 0:
        console.print(f"  {FAIL} Helm deployment failed")
        raise typer.Exit(1)
    console.print(f"  {OK} Dagster deployed")

    # Wait for all pods to become ready
    with Status("  Waiting for pods...", console=console) as wait_status:
        pods_ready = _wait_for_pods(wait_status)
    if pods_ready:
        console.print(f"  {OK} All pods ready")
    else:
        console.print(f"  {WARN} Some pods are not ready after {READY_TIMEOUT}s")

    console.print()
    status()
    console.print()
    console.print(f"  UI available at {DAGSTER_UI_URL}")
    console.print()

    if not pods_ready:
        raise typer.Exit(1)


@app.command()
def down(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Tear down Kubernetes deployment."""
    if not yes:
        typer.confirm("Tear down Kubernetes deployment?", abort=True)
    console.print()
    console.print("  [title]Tearing down Kubernetes deployment[/]")
    console.print()

    code, _ = run_capture(["helm", "uninstall", RELEASE, "-n", NAMESPACE, "--wait=false"])
    if code == 0:
        console.print(f"  {OK} Helm release uninstalled")
    else:
        console.print(f"  {DASH} Helm release not found")

    code, _ = run_capture(
        ["kubectl", "delete", "jobs", "-n", NAMESPACE, "-l", "dagster/run-id", "--timeout=10s"]
    )
    if code == 0:
        console.print(f"  {OK} Jobs cleaned up")
    else:
        console.print(f"  {DASH} Jobs not found")

    code, _ = run_capture(
        [
            "kubectl",
            "delete",
            "pods",
            "-n",
            NAMESPACE,
            "-l",
            "dagster/run-id",
            "--grace-period=0",
            "--force",
            "--timeout=10s",
        ]
    )
    if code == 0:
        console.print(f"  {OK} Pods cleaned up")
    else:
        console.print(f"  {DASH} Pods not found")

    code, _ = run_capture(
        ["kubectl", "delete", "pvc", "dagster-storage", "-n", NAMESPACE, "--timeout=10s"]
    )
    if code == 0:
        console.print(f"  {OK} PVC removed")
    else:
        console.print(f"  {DASH} PVC not found")

    code, _ = run_capture(
        ["kubectl", "delete", "configmap", "test-data-xml", "-n", NAMESPACE, "--timeout=10s"]
    )
    if code == 0:
        console.print(f"  {OK} ConfigMap removed")
    else:
        console.print(f"  {DASH} ConfigMap not found")

    console.print(f"\n  {OK} Teardown complete")
    console.print()


@app.command()
def restart() -> None:
    """Rebuild image and rollout restart."""
    if not _check_k8s():
        raise typer.Exit(1)

    with Status("  Building Docker image...", console=console):
        code = run_passthrough(["docker", "build", "-t", IMAGE, "-q", "."])
    if code != 0:
        console.print(f"  {FAIL} Docker build failed")
        raise typer.Exit(1)
    console.print(f"  {OK} Image built ({IMAGE})")

    with Status("  Restarting user code deployment...", console=console):
        code = run_passthrough(
            [
                "kubectl",
                "rollout",
                "restart",
                "deployment",
                "-n",
                NAMESPACE,
                "-l",
                "app.kubernetes.io/name=dagster-user-deployments",
            ]
        )
    if code != 0:
        console.print(f"  {FAIL} Restart failed")
        raise typer.Exit(1)

    with Status("  Waiting for rollout...", console=console):
        code = run_passthrough(
            [
                "kubectl",
                "rollout",
                "status",
                "deployment",
                "-n",
                NAMESPACE,
                "-l",
                "app.kubernetes.io/name=dagster-user-deployments",
                f"--timeout={ROLLOUT_TIMEOUT}",
            ]
        )
    if code != 0:
        console.print(f"  {FAIL} Rollout failed")
        raise typer.Exit(1)
    console.print(f"  {OK} Restart complete")
    console.print()


@app.command()
def status() -> None:
    """Show pods and services."""
    code, _ = run_capture(["kubectl", "get", "namespace", NAMESPACE])
    if code != 0:
        console.print(f"  {WARN} Deployment not running")
        console.print("  [hint]Run 'dap k8s up' to deploy[/]")
        console.print()
        return

    console.print("  [title]Pods[/]")
    code, pods = run_capture(["kubectl", "get", "pods", "-n", NAMESPACE, "-o", "wide"])
    if code != 0 or not pods or f"No resources found in {NAMESPACE}" in pods:
        console.print("  [hint]no pods running[/]")
    else:
        for line in pods.splitlines():
            console.print(f"  {line}")

    console.print()
    console.print("  [title]Services[/]")
    code, svcs = run_capture(["kubectl", "get", "svc", "-n", NAMESPACE])
    if code != 0 or not svcs:
        console.print("  [hint]no services running[/]")
    else:
        for line in svcs.splitlines():
            console.print(f"  {line}")
    console.print()


@app.command()
def logs() -> None:
    """Stream user code pod logs."""
    console.print(f"  {ARROW} Streaming logs from user code pod...")
    console.print()
    run_interactive(
        [
            "kubectl",
            "logs",
            "-n",
            NAMESPACE,
            "-l",
            "app.kubernetes.io/name=dagster-user-deployments",
            "--tail=100",
            "-f",
        ]
    )


@app.command()
def shell() -> None:
    """Interactive shell in user code pod."""
    code, pod_name = run_capture(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            NAMESPACE,
            "-l",
            "app.kubernetes.io/name=dagster-user-deployments",
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ]
    )
    if code != 0 or not pod_name:
        console.print(f"  {FAIL} No user code pod found. Is Dagster deployed?")
        raise typer.Exit(1)

    console.print(f"  {ARROW} Opening shell in {pod_name}...")
    console.print()
    run_interactive(["kubectl", "exec", "-it", "-n", NAMESPACE, pod_name, "--", "/bin/bash"])
