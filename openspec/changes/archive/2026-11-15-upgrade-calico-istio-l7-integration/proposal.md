# Proposal

## Why

The `tcharl.servicemesh` upgrade pins Calico 3.33 but retains its older Istio injector ConfigMap patch, which does not match Calico's current documented Dikastes integration. Updating the role to the supported sidecar-based setup will keep Calico application-layer policy working across Istio upgrades and make installed versions reproducible.

## What Changes

- Align the role's Istio pin with Calico 3.33's recommended Istio version, `1.28.1`, and ensure the downloaded Istio release uses that exact pin.
- Replace legacy injector ConfigMap patching with Calico's documented IstioOperator Dikastes templates for application and gateway workloads, including the CSI-backed Felix Policy Sync socket.
- Preserve the current sidecar-based Istio deployment and Calico L7 policy enforcement; do not adopt Istio Ambient Mode.
- Extend role verification to cover the Calico CSI driver, Dikastes injection and readiness, and an application-layer policy allow/deny case.

## Capabilities

### New Capabilities

- `servicemesh-l7-policy-enforcement`: Define the role's sidecar-based integration contract between Istio Envoy, Calico Dikastes, and Felix Policy Sync.

### Modified Capabilities

None.

## Impact

- `ansible/roles/tcharl.servicemesh/defaults/main.yml` and `tasks/service-mesh.yml`: version pin and Istio/Calico integration configuration.
- `ansible/roles/tcharl.servicemesh/molecule/`: integration verification for CSI, injection, and policy behavior.
- `ansible/roles/tcharl.servicemesh/README.md`: document supported versions and the L7 integration behavior.
- No change to `tcharl.ansible_orchestration` or the separate `calico-native-v3-cleanup` change.
