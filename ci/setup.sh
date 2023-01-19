set -xe

sudo apt-get update
sudo apt-get upgrade -y

echo '127.0.0.1  onboarding-onboarding.cluster.local' | sudo tee -a /etc/hosts

sudo docker run -d --rm --name microshift --privileged \
    --network host \
    -v microshift-data:/var/lib \
    quay.io/microshift/microshift-aio:latest

sudo docker run -d --rm --name registry --network host registry:2

sleep 30

curl -O https://mirror.openshift.com/pub/openshift-v4/$(uname -m)/clients/ocp/stable/openshift-client-linux.tar.gz
sudo tar -xf openshift-client-linux.tar.gz -C /usr/local/bin oc kubectl

mkdir -p ~/.kube
sudo docker cp microshift:/var/lib/microshift/resources/kubeadmin/kubeconfig ~/.kube/config
oc get all

sudo docker build . -t "localhost:5000/cci-moc/openshift-acct-mgt:latest"
sudo docker push "localhost:5000/cci-moc/openshift-acct-mgt:latest"

oc apply -k k8s/overlays/crc
oc wait -n onboarding --for=condition=available --timeout=800s deployment/onboarding

sleep 90

curl -u admin:pass https://onboarding-onboarding.cluster.local/users/test -k
