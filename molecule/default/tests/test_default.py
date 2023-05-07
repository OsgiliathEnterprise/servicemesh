"""Role testing files using testinfra."""


def test_user_exists(host):
    command = r"""set -o pipefail && echo '123ADMin'| \
    kinit admin > /dev/null && \
    ipa user-find admin | \
    grep -c 'First name: Admin'"""
    cmd = host.run(command)
    assert '1' in cmd.stdout

