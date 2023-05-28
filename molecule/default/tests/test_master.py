"""Role testing files using testinfra."""
testinfra_hosts = ["master.osgiliath.test"]


def test_istio_system_pods_are_configured(host):
    command = r"""
    kubectl get pods -n istio-system | \
    wc -l"""
    with host.sudo():
        cmd = host.run(command)
        assert int(cmd.stdout) > 0
