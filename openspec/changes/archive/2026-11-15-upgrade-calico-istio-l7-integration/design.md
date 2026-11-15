# Design

## Context

See `proposal.md` for motivation and `specs/servicemesh-l7-policy-enforcement/spec.md` for the behavior contract.

The role currently patches Felix `policySyncPathPrefix`, downloads Istio without setting `ISTIO_VERSION`, installs base, discovery, ingress, and egress Helm charts from the locally extracted `istio_version` archive, patches the legacy injector ConfigMap, and applies Calico's Envoy external-authorization resources. Calico 3.33's guide instead configures Dikastes injection through IstioOperator templates and requires Kubernetes native sidecars (Kubernetes 1.29+). The orchestration role currently pins Kubernetes 1.36 and Calico `v3.33.0`, satisfying that Kubernetes prerequisite.

## Goals / Non-Goals

**Goals:**
- Keep one versioned Istio installation owner and use the exact Calico-documented Dikastes templates.
- Preserve the current ingress and egress gateway capabilities while migrating installation management.
- Ensure application and gateway workloads can opt into Dikastes, with Felix Policy Sync available through the Calico CSI socket.
- Verify the integration through role-level tests, including an observable application-layer policy decision.

**Non-Goals:**
- Deploy Calico-managed Ambient Mode; it is tech preview and incompatible with application-layer policy.
- Change Calico CNI installation or the orchestration role's Calico version.
- Enable L7 policy injection for every workload by default; workloads opt in using the documented template annotation.

## Decisions

**Render an IstioOperator configuration with `istioctl manifest generate` and apply the result declaratively.** Calico's current guide supplies this path for loading the custom injection templates, and `istioctl` is already included in the downloaded release. Applying the generated manifest through the Kubernetes module avoids competing Helm ownership, supports idempotent convergence, and removes imperative post-install ConfigMap patches. Configure the selected profile and gateway components explicitly so ingress and egress behavior from the current role is not accidentally dropped. Keep the Calico Envoy external-authorization resources as a separately applied manifest, since the current Calico guide continues to require them.

Alternative considered: use `istioctl install -f` directly. This is also documented, but its command output does not provide Ansible with a reliable changed/no-change signal for the second-converge integration check.

**Pin the installer and installed resources to `istio_version: 1.28.1`.** Pass `ISTIO_VERSION` to the official download script and use the extracted archive's `istioctl`; keep Calico manifest and image references derived from `calico_version: v3.33.0`. This prevents the unpinned installer from producing a directory that disagrees with the chart or CLI paths.

Alternative considered: let the download script choose its latest release. Rejected because it makes a role run non-reproducible and can fail when the role expects a different extracted directory.

**Use opt-in `sidecar,dikastes` and `sidecar,dikastes-gateway` templates.** Add both templates to IstioOperator values based on Calico's application-layer policy guide. Use a Calico-versioned Dikastes image, the documented Policy Sync socket arguments and CSI volume, non-root security context for application pods, and root context for gateway pods. Apply the documented Envoy external-authorization manifest after Istio is installed. Document the required workload annotation and namespace injection label.

Alternative considered: inject Dikastes into every workload through the default sidecar template. Rejected because current guidance exposes explicit opt-in templates and blanket injection would change the role's workload behavior beyond the L7-policy use case.

**Treat CSI and Policy Sync as hard prerequisites for successful enforcement. Gate convergence on the Tigera-operator-managed CSI driver instead of installing a manifest.** Calico on this platform is installed through the Tigera operator (see `tcharl.ansible_orchestration`), and the operator itself creates the `csi-node-driver` DaemonSet in `calico-system` and the `csi.tigera.io` CSIDriver (Ephemeral mode) — exactly what the Dikastes volume template requires. The role therefore only waits (with retries) for the `csi.tigera.io` CSIDriver and the ready `csi-node-driver` DaemonSet, and keeps Felix's Policy Sync prefix configured. Applying Calico's standalone `csi-driver.yaml` manifest on top of the operator-managed DaemonSet fails with `422 spec.selector: field is immutable` (the manifest selector adds `name` next to `k8s-app`), as observed during the molecule gate on 2026-11-11. A workload is not considered correctly integrated solely because an `istio-system` pod exists.

Alternative considered: only check for Istio control-plane pods. Rejected because that would not exercise the Dikastes-to-Felix path that provides L7 decisions.

**Inject Dikastes into the gateways with a direct strategic-merge patch instead of relying on the sidecar injector.** The IstioOperator chart renders the ingress/egress gateway Deployments with `sidecar.istio.io/inject: "false"` and a complete router proxy template, so the injector never processes gateway pods (and forcing it would fight the chart's router proxy). The role therefore patches both gateway Deployments in `tasks/service-mesh.yml` with an idempotent `kubernetes.core.k8s` strategic-merge patch adding the `dikastes` container (root security context, `calico/calico:{{ calico_version }}`, Policy Sync socket args) and the shared socket volume mounts, mirroring the `dikastes-gateway` injector template. The gateway pod annotations keep `inject.istio.io/templates: sidecar,dikastes-gateway` so the intent remains declarative for any pod that does flow through the injector, and the molecule test asserts both the annotation and the running container.

Alternative considered: flip `sidecar.istio.io/inject` to `"true"` on the gateway Deployments. Rejected because the injector would then re-render the gateway's complete router proxy from the sidecar template, diverging from the chart-managed gateway configuration.

**Use the `calico` CLI exec probes for Dikastes liveness/readiness in both injector templates.** The unified `calico/calico:v3.33.0` image is scratch-like: it has no shell and no HTTP endpoint, so the historically documented `GET /healthz` probes (and any `sh -c` wrapper) cannot work — verified by inspecting the image with `ctr run` on the molecule node. Both `dikastes` and `dikastes-gateway` templates use `exec` probes running `/usr/bin/calico component dikastes health liveness|readiness`, the upstream v3.33 health subcommands.

Alternative considered: keep HTTP `/healthz` probes from the older Calico Istio integration docs. Rejected after gate runs showed the probes could never pass against the unified image, leaving dikastes containers permanently unready.

**Restart the ALP test server Deployment in `side_effect.yml` so fixture pods re-inject on every gate run.** `kubectl apply` of an unchanged fixture does not re-trigger sidecar injection, so a template fix (e.g. the probe change above) would not reach long-lived fixture pods. The rollout restart task carries the documented shell exception (no native module performs a deployment rollout) and a truthful `changed_when` on the `restarted` output.

**Cluster-wide `kubectl exec`/`kubectl logs` required a fix in `tcharl.ansible_orchestration` (change `kubelet-x509-client-auth`).** The L7 allow/deny verification reaches workloads through API-server-proxied subresources; after the platform's IPA PKI swap the kubelets rejected the API server's CA #2-issued kubelet client certificate with 401 (master pinned `clientCAFile` to CA #1 only; the worker's minimal kubelet config had no authenticator at all). Per monorepo convention the fix is an openspec change on that role (master: point `clientCAFile` at the merged `ca-bundle.crt`; worker: install the CA bundle and the standard `authentication`/`authorization` blocks), not an edit from this role.

## Risks / Trade-offs

- [Switching installation managers can leave old Helm releases or resources behind on existing clusters] → Make the migration steps explicit; remove or upgrade legacy releases in a safe order and verify the resulting Istio control plane and gateways before enabling workload injection.
- [Gateway chart behavior may differ from the selected IstioOperator profile] → Model ingress and egress components explicitly and test both deployments before considering the migration complete.
- [Workloads may not receive Dikastes without the opt-in annotation] → Document the namespace label and workload/gateway template annotations; include them in the policy test fixture.
- [CSI readiness or Policy Sync configuration may be missing on a node] → Gate verification on CSI availability and Dikastes readiness, and report the failing prerequisite rather than relying on a pod-count check.
- [L7 policy defaults to deny when there is no applicable allow policy] → Include both an explicitly allowed and denied request in the test scenario and document the expected 403 response.

## Migration Plan

1. Download the pinned Istio 1.28.1 distribution, render the IstioOperator configuration containing Dikastes templates, and apply the generated Istio resources while preserving ingress/egress gateway components.
2. Remove the old Helm releases and legacy injector ConfigMap patch from the role's managed path, avoiding simultaneous Helm and `istioctl` ownership.
3. Keep the Felix Policy Sync configuration and Calico Envoy authorization resources; ensure the Calico CSI driver is ready before workload verification.
4. Document how workload namespaces and pods opt into Istio and Dikastes. Existing Istio-enabled workloads must be annotated/restarted to receive Dikastes after the transition.
5. Verify the control plane, gateways, CSI driver, injected application and Dikastes containers, and policy allow/deny behavior. Roll back by restoring the prior role version and its Helm releases if the new installation fails before workloads are migrated.

## Open Questions

None.
