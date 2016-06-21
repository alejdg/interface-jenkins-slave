from testtools.testcase import TestCase

from fixtures import (
    EnvironmentVariable,
    TempDir,
    MonkeyPatch,
)

from jenkins import JenkinsException

from stubs.hookenv import HookenvStub
from stubs.jenkins import JenkinsStub

from master import Master


class MasterTest(TestCase):

    def setUp(self):
        super(MasterTest, self).setUp()
        self.charm_dir = self.useFixture(TempDir())
        self.useFixture(EnvironmentVariable("CHARM_DIR", self.charm_dir.path))
        self.hookenv = HookenvStub(self.charm_dir.path)
        self.hookenv.config()["username"] = "admin"
        self.jenkins = JenkinsStub()
        self.master = Master(hookenv=self.hookenv, jenkins=self.jenkins)

    def test_username(self):
        """
        The username matches then one set in the service configuration.
        """
        self.assertEqual("admin", self.master.username())

    def test_password_from_config(self):
        """
        If set, the password matches the one set in the service configuration.
        """
        self.hookenv.config()["password"] = "sekret"
        self.assertEqual("sekret", self.master.password())

    def test_password_from_local_state(self):
        """
        If not set, the password is retrieved from the local state.
        """
        self.hookenv.config()["password"] = ""
        self.hookenv.config()["_generated-password"] = "aodlaod"
        self.assertEqual("aodlaod", self.master.password())

    def test_add(self):
        """
        A slave node can be added by specifying executors and labels.
        """
        self.hookenv.config()["password"] = "sekret"
        self.master.add_node("slave-0", 1, labels=["python"])
        [node] = self.jenkins.nodes
        self.assertEqual("slave-0", node.host)
        self.assertEqual(2, node.executors)
        self.assertEqual("slave-0", node.description)
        self.assertEqual(["python"], node.labels)

    def test_add_exists(self):
        """
        If a node already exists, nothing is done.
        """
        self.jenkins.create_node("slave-0", 1, "slave-0")
        self.hookenv.config()["password"] = "sekret"
        self.master.add_node("slave-0", 1, labels=["python"])
        self.assertEqual(1, len(self.jenkins.nodes))

    def test_add_transient_failure(self):
        """
        Transient failures get retried.
        """
        self.useFixture(MonkeyPatch("time.sleep", lambda _: None))

        create_node = self.jenkins.create_node
        tries = []

        def transient_failure(*args, **kwargs):
            try:
                if not tries:
                    raise JenkinsException("error")
                create_node(*args, **kwargs)
            finally:
                tries.append(True)

        self.jenkins.create_node = transient_failure
        self.hookenv.config()["password"] = "sekret"
        self.master.add_node("slave-0", 1, labels=["python"])
        self.assertEqual(1, len(self.jenkins.nodes))

    def test_add_retry_give_up(self):
        """
        If errors persist, we give up.
        """
        self.useFixture(MonkeyPatch("time.sleep", lambda _: None))

        def failure(*args, **kwargs):
            raise JenkinsException("error")

        self.jenkins.create_node = failure
        self.hookenv.config()["password"] = "sekret"
        self.assertRaises(
            JenkinsException, self.master.add_node, "slave-0", 1)

    def test_add_spurious(self):
        """
        If adding a node apparently succeeds, but actually didn't then we
        log an error.
        """
        self.jenkins.create_node = lambda *args, **kwargs: None
        self.hookenv.config()["password"] = "sekret"
        self.master.add_node("slave-0", 1, labels=["python"])
        self.assertEqual(
            ("Failed to create node 'slave-0'", "WARNING"),
            self.hookenv.messages[-1])

    def test_deleted(self):
        """
        A slave node can be deleted by specifyng its host name.
        """
        self.hookenv.config()["password"] = "sekret"
        self.master.add_node("slave-0", 1, labels=["python"])
        self.master.delete_node("slave-0")
        self.assertEqual([], self.jenkins.nodes)

    def test_deleted_no_present(self):
        """
        If a slave node doesn't exists, deleting it is a no-op.
        """
        self.hookenv.config()["password"] = "sekret"
        self.master.delete_node("slave-0")
        self.assertEqual([], self.jenkins.nodes)
