set -xe

python3 -m pytest tests/functional -v --cov=acct_mgt --cov-report=term \
    --admin-user admin --admin-password pass \
    --api-endpoint https://onboarding-onboarding.cluster.local
