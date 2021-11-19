# Build and Deploy openshift-acct-mgt on CRC
#
# Requires prior `oc login` and running from root of repo.
#
# Deployment will be done in namespace named `onboarding`.
# To deploy to a different namespace, change the name in `project.yaml`
# and variable `NAMESPACE`.

set -e

if [ "$(uname)" == "Darwin" ]; then
  CMD="docker"
  INSECURE_FLAG=""
else
  CMD="sudo podman"
  INSECURE_FLAG="--tls-verify=false"
fi

INTERNAL_REGISTRY="default-route-openshift-image-registry.apps-crc.testing"

# yaml spec rather than new-project command for idempotency
NAMESPACE="onboarding"
oc apply -f tools/crc/project.yaml

$CMD login $INSECURE_FLAG -u kubeadmin -p "$(oc whoami -t)" "$INTERNAL_REGISTRY"
$CMD build . -t "$INTERNAL_REGISTRY/$NAMESPACE/openshift-acct-mgt:latest"
$CMD push $INSECURE_FLAG "$INTERNAL_REGISTRY/$NAMESPACE/openshift-acct-mgt:latest"

oc apply -k k8s/overlays/crc

# TODO: Check for error state
while [ "$(oc -n onboarding get pods | grep onboarding | grep -v deploy | grep -c Running)" == "0" ]; do
  echo "Waiting until pod is ready..."
  sleep 10
done
