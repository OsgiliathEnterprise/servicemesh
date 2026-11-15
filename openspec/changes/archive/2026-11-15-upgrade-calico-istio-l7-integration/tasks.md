# Tasks

## 1. Pin the supported versions

- [x] 1.1 Set the role's Istio default to `1.28.1`, pass `ISTIO_VERSION` to the download script, and remove the obsolete injector ConfigMap version variable; verify the downloaded archive path and installed CLI use the configured version.
- [x] 1.2 Update the role README with the Calico/Istio supported version pairing and deterministic download behavior; verify documented defaults match `defaults/main.yml`.

## 2. Migrate Istio installation and injection

- [x] 2.1 Replace the four Helm chart installs and legacy injector ConfigMap patch with a versioned IstioOperator configuration rendered by `istioctl manifest generate` and applied declaratively; include Calico's Dikastes application and gateway templates and preserve ingress/egress gateway behavior; verify the rendered resources and expected control-plane/gateway resources.
- [x] 2.2 Extend Molecule verification to assert both Dikastes templates are installed and opted-in application and gateway pods receive the expected Dikastes container, Calico-versioned image, shared socket mounts, and readiness; document the namespace labels and workload/gateway template annotations in the README and verify names match the templates.

## 3. Verify Calico Policy Sync and L7 decisions

- [x] 3.1 Keep Felix `policySyncPathPrefix` and the Calico Envoy authorization resources, and add a readiness check for the CSI driver on target nodes; verify a Dikastes workload connects to Policy Sync and failures are surfaced when CSI is unavailable.
- [x] 3.2 Add a Molecule workload and Calico policy fixtures proving an explicitly allowed HTTP request succeeds and a request without an applicable allow policy receives HTTP 403; document the default-deny behavior and verify both outcomes.

## 4. Integration gate

- [x] 4.1 Run the service-mesh Molecule scenario from a clean cluster and verify control-plane and gateway readiness, CSI availability, Dikastes injection, L7 allow/deny behavior, and a second converge with no unintended changes.

## Workflow follow-up

- Archive the change after review and implementation requirements are satisfied.
- Verify the archived result.
