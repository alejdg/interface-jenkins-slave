from jenkins import Jenkins, JenkinsException

from charmhelpers.core import hookenv
from charmhelpers.core.decorators import (
    retry_on_exception,
)

from charmhelpers.core.hookenv import (
    WARNING,
    INFO,
    DEBUG,
)

URL = "http://localhost:8080/"


class Master(object):
    """Encapsulate operations on the Jenkins master."""

    def __init__(self, hookenv=hookenv, jenkins=Jenkins):
        """
        @param hookenv: An object implementing the charmhelpers.core.hookenv
            API from charmhelpers (for testing).
        @param jenkins: A client factory for driving the Jenkins API.
        """
        self._hookenv = hookenv
        self._jenkins = jenkins

    def username(self):
        """Get the username of the admin user, as set in the config."""
        return self._hookenv.config()["username"]

    def password(self):
        """Get the admin password from the config or from the local state."""
        password = self._hookenv.config()["password"]
        if not password:
            password = self._hookenv.config()["_generated-password"]
        return password

    def add_node(self, host, executors, labels=()):
        """Add a slave node with the given host name."""
        client = self._make_client()

        @retry_on_exception(2, 2, exc_type=JenkinsException)
        def _add_node(*args, **kwargs):

            if client.node_exists(host):
                self._hookenv.log("Node exists - not adding", level=DEBUG)
                return

            self._hookenv.log(
                "Adding node '%s' to Jenkins master" % host, level=INFO)

            client.create_node(host, int(executors) * 2, host, labels=labels)

            if not client.node_exists(host):
                self._hookenv.log(
                    "Failed to create node '%s'" % host, level=WARNING)

        return _add_node()

    def delete_node(self, host):
        """Delete the slave node with the given host name."""
        client = self._make_client()
        if client.node_exists(host):
            self._hookenv.log("Node '%s' exists" % host, level=DEBUG)
            client.delete_node(host)
        else:
            self._hookenv.log(
                "Node '%s' does not exist - not deleting" % host, level=INFO)

    def _make_client(self):
        """Build a Jenkins client instance."""
        return self._jenkins(URL, self.username(), self.password())
