sudo docker build . -t "localhost:5000/cci-moc/openshift-acct-mgt:latest"
sudo docker push "localhost:5000/cci-moc/openshift-acct-mgt:latest"

oc delete -n onboarding deployment onboarding
oc apply -k k8s/overlays/crc
