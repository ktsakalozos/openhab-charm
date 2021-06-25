#!/usr/bin/env python3
# Copyright 2021 jackal
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus
from kubernetes_wrapper import Kubernetes

logger = logging.getLogger(__name__)


class OpenhabCharmCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        logging.info("Namespace is {}".format(self.model.name))
        self.kubernetes = Kubernetes(self.model.name)
        self.framework.observe(self.on.install, self.install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    @property
    def _external_hostname(self):
        """
        Check if hostname has been configured. If not, generate one.
        """
        if self.config["external-hostname"] and self.config["external-hostname"] != "":
            return self.config["external-hostname"]
        else:
            return "{}.127.0.0.1.nip.io".format(self.app.name)

    def install(self, event):
        self.kubernetes.apply_object(self.service_object)

    @property
    def service_object(self):
        app_name = self.model.app.name
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": app_name + "-web",
                "namespace": self.model.name,
            },
            "spec": {
                "selector": {
                    "app.kubernetes.io/name": app_name
                },
                "type": "NodePort",
                "ports": [{
                    "port": 8443,
                    "targetPort": 8443,
                    "nodePort": 31443,
                    "protocol": "TCP"
                }]
            }
        }

    def _on_config_changed(self, event):
        """Handle the config-changed event"""
        # Get the gosherve container so we can configure/manipulate it
        # Create a new config layer
        layer = {
            "summary": "openhab layer",
            "description": "pebble config layer for openhab",
            "services": {
                "openhab": {
                    "override": "replace",
                    "summary": "openhab",
                    "environment": {
                        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                        "CRYPTO_POLICY": "limited",
                        "EXTRA_JAVA_OPTS": "",
                        "GROUP_ID": "9001",
                        "JAVA_VERSION": "11",
                        "KARAF_EXEC": "exec",
                        "LC_ALL": "en_US.UTF-8",
                        "LANG": "en_US.UTF-8",
                        "LANGUAGE": "en_US.UTF-8",
                        "OPENHAB_BACKUPS": "/openhab/userdata/backup",
                        "OPENHAB_CONF": "/openhab/conf",
                        "OPENHAB_HOME": "/openhab",
                        "OPENHAB_HTTP_PORT": "8080",
                        "OPENHAB_HTTPS_PORT": "8443",
                        "OPENHAB_LOGDIR": "/openhab/userdata/logs",
                        "OPENHAB_USERDATA": "/openhab/userdata",
                        "OPENHAB_VERSION": "3.0.2",
                        "USER_ID": "9001",
                        "JAVA_HOME": "/usr/lib/jvm/default-jvm",
                    },
                    "command": "/entrypoint gosu openhab tini -s ./start.sh",
                    "startup": "enabled",
                    "user": "openhab",
                    "group": "openhab",
                }
            },
        }

        # Getting KARAF_ETC is not valid: /openhab/userdata/etc
        # https://community.openhab.org/t/docker-restarting-karaf-etc-is-not-valid-openhab-userdata-etc/91399
        container = self.unit.get_container("openhab")
        try:
            # Get the current config
            services = container.get_plan().to_dict().get("services", {})
            if services != layer["services"]:
                # Changes were made, add the new layer
                container.add_layer("openhab", layer, combine=True)
                logging.info("Added updated layer 'openhab' to Pebble plan")
                # Stop the service if it is already running
                if container.get_service("openhab").is_running():
                    container.stop("openhab")
                # Restart it and report a new status to Juju
                container.start("openhab")
                logging.info("Restarted openhab service")
        except ConnectionError:
            # Since this is a config-changed handler and that hook can execute
            # before pebble is ready, we may get a connection error here. Let's
            # defer the event, meaning it will be retried the next time any
            # hook is executed. We don't have an explicit handler for
            # `self.on.gosherve_pebble_ready` but this method will be rerun
            # when that condition is met (because of `event.defer()`), and so
            # the `get_container` call will succeed and we'll continue to the
            # subsequent steps.
            logging.info("Pebble not ready (connection error).")
            event.defer()
            return
        except FileNotFoundError:
            logging.info("Pebble not ready (file not found).")
            event.defer()
            return
        except:
            logging.info("Pebble not ready (some other error).")
            event.defer()
            return

        # Check if there are any changes to services
        # All is well, set an ActiveStatus
        self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(OpenhabCharmCharm)
