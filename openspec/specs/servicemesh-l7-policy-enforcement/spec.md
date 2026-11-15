# servicemesh-l7-policy-enforcement Specification

## Purpose

Defines how the service-mesh role integrates Istio sidecars with Calico's Dikastes authorization service so workloads can enforce Calico application-layer network policies.

## Requirements

### Requirement: Reproducible supported version pairing
The role SHALL install the configured Istio release and a Calico-supported application-layer policy integration for the configured Calico release.

#### Scenario: Configured Istio version is installed
- **WHEN** the role is configured with an Istio version
- **THEN** the downloaded release artifacts and installed Istio components use that exact version

#### Scenario: Supported version pairing is selected
- **WHEN** the role is configured with Calico `v3.33.0`
- **THEN** its default Istio version is Calico's documented recommended version `1.28.1`

### Requirement: Opt-in Dikastes injection
The role SHALL make the documented Dikastes integration available to opted-in Istio sidecar workloads and gateways, with the required Unix socket shared between Envoy and Dikastes.

#### Scenario: Application workload requests Dikastes
- **WHEN** a workload opts into the documented Istio sidecar and Dikastes injection templates
- **THEN** its pod receives Envoy and Dikastes containers with the required shared socket mounts

#### Scenario: Gateway workload requests Dikastes
- **WHEN** an Istio gateway opts into the documented Dikastes gateway template
- **THEN** its pod receives the gateway-compatible Dikastes configuration and shared socket mounts

### Requirement: Felix Policy Sync connectivity
The role SHALL provide the CSI-backed connection required for Dikastes to query Felix Policy Sync and SHALL configure Felix to expose the Policy Sync socket at the path expected by Dikastes.

#### Scenario: Policy Sync is available to Dikastes
- **WHEN** an opted-in workload starts with the Calico CSI driver available
- **THEN** Dikastes can connect to Felix Policy Sync through the mounted socket

#### Scenario: CSI prerequisite is unavailable
- **WHEN** the Calico CSI driver cannot provide the requested volume
- **THEN** the workload does not report successful Dikastes readiness

### Requirement: Application-layer policy enforcement
The integration SHALL enforce Calico application-layer policy decisions for HTTP requests handled by an opted-in workload.

#### Scenario: Request matches an allow policy
- **WHEN** an HTTP request matches an applicable Calico allow policy
- **THEN** the request is permitted

#### Scenario: Request has no applicable allow policy
- **WHEN** an HTTP request is evaluated without an applicable allow policy
- **THEN** Dikastes denies the request with HTTP 403
