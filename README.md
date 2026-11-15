Ansible Servicemesh
=========

* Galaxy: [![Ansible Galaxy](https://img.shields.io/badge/galaxy-tcharl.servicemesh-660198.svg?style=flat)](https://galaxy.ansible.com/tcharl/servicemesh)
* Lint & requirements: ![Molecule](https://github.com/OsgiliathEnterprise/servicemesh/workflows/Molecule/badge.svg)
* Tests: [![Build Status](https://travis-ci.com/OsgiliathEnterprise/servicemesh.svg?branch=master)](https://travis-ci.com/OsgiliathEnterprise/servicemesh)
* Chat: [![Join the chat at https://gitter.im/OsgiliathEnterprise/platform](https://badges.gitter.im/OsgiliathEnterprise/platform.svg)](https://gitter.im/OsgiliathEnterprise/platform?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Deploys Istio mesh on a kubernetes cluster

Calico application-layer policy integration
-------------------------------------------

The role defaults to Calico `v3.33.0` and its recommended Istio version `1.28.1`.
The Istio download uses the configured `istio_version`; overriding that variable
selects the same version for both the downloaded tools and the installed mesh.
The role installs and waits for the Calico CSI driver and configures Felix Policy
Sync at `/var/run/nodeagent`. Application-layer policy uses Istio sidecars with
Calico Dikastes. Ambient mode is not used because Calico application-layer
policies are not compatible with it.

To opt application workloads into Istio and Calico application-layer policy,
label their namespace with `istio-injection=enabled` and annotate the workload
pod template with `inject.istio.io/templates: sidecar,dikastes`. The annotation
for Istio gateway pod templates is
`inject.istio.io/templates: sidecar,dikastes-gateway`; this role applies it to
both its ingress and egress gateways. Both templates add the Calico-versioned
Dikastes container and share the required sockets with Envoy. Without a
matching Calico allow policy, HTTP requests to an opted-in workload are denied
with HTTP 403.

Requirements
------------

Like any other platform role, executing `tox -e pipdep` and `tox -e dependency` 

Role Variables
--------------

Take a look at the [molecule tests](./molecule/default/converge.yml) tests and the [default variables](./defaults/main.yml)

Dependencies
------------

* [Collections](./requirements-collections.yml)
* [Roles](./requirements-standalone.yml)


License
-------

[Apache-2](https://www.apache.org/licenses/LICENSE-2.0)

Author Information
------------------

* Twitter [@tcharl](https://twitter.com/Tcharl)
* Github [@tcharl](https://github.com/Tcharl)
* LinkedIn [Charlie Mordant](https://www.linkedin.com/in/charlie-mordant-51796a97/)
