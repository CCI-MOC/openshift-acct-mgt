# Develop

## Installing OpenShift (CodeReady Containers)
If you already have a working OpenShift environment to deploy to, this step
is not necessary. If however you are interested in creating a local
development environment to develop and test for, read along.

[CodeReady Containers](https://code-ready.github.io/crc/) is a tool to create
a local installation of OpenShift 4.x. It supports Windows, Linux, and Mac but
for the purposes of this we're only focusing on the latter two.

Unfortunately, it needs to be [registered with Red Hat](https://cloud.redhat.com/openshift/create/local)
to receive a secret necessary for installation.

Place the secret in `tools/crc/pullstring.json` and run:

```bash
./tools/crc/setup_crc.sh tools/crc/pullstring.json
```

## Deploying to CRC
First, start building the docker image and pushing it to the [internal
CodeReady Containers registry](
https://code-ready.github.io/crc/#accessing-the-internal-openshift-registry_gsg).

For that, we first need to log in to the registry. If you're using RHEL/CentOS,
substitute `docker` for `podman` in the command below.

```bash
docker login -u kubeadmin -p $(oc whoami -t) default-route-openshift-image-registry.apps-crc.testing
docker build . -t default-route-openshift-image-registry.apps-crc.testing/onboarding/openshift-acct-mgt:latest
docker push default-route-openshift-image-registry.apps-crc.testing/onboarding/openshift-acct-mgt:latest
```

After the image has been build and pushed, we can apply the kustomization specs.
This will install all the necessities for deploying and running the service,
including a service account and cluster role binding.

```bash
oc new-project onboarding

cd k8s/overlays/crc
oc apply -k .
```

Of particular note is the ImageStream to point to a local image via the
`lookupPolicy` `local` attribute.

```yaml
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: openshift-acct-mgt
spec:
  lookupPolicy:
    local: true
```

The above commands are part of the script located in `tools/crc/deploy.sh`.

## Testing

Running the tests requires passing `--amurl` as an argument with the URL endpoint
for the OpenShift API. For CodeReady containers, that is
`https://openshift-onboarding.apps-crc.testing`

```bash
pip install -r test-requirements
python3 -m pytest acct-mgt-test.py --amurl https://openshift-onboarding.apps-crc.testing
```
