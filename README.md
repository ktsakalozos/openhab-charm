# OpenHAB charm
Kubernetes charm for installing [openhab](https://www.openhab.org/) `v3.0.2`.


## Description

  [open Home Automation Bus](https://www.openhab.org/) is an open source home automation software.
  It is deployed on premises and connects to devices and services from different vendors.
  This charm deploys OpenHab on a Kubernetes cluster.


## Usage

Deply the charm with:
```dtd
juju deploy openhab --channel=edge
```

The charm exposes the OpenHAB https interface on NodePort `31443` this means you can point your browser to the IP
of any of you Kubernetes nodes on port `31443` to start interacting with OpenHAB. If you are doing a local deployment
with [MicroK8s](https://microk8s.io) just navigate to https://127.0.0.1:31443.


## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

    ./run_tests
