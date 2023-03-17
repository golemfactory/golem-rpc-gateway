#!/bin/bash
set -x
export PATH=".:$PATH"

poetry run python main.py \
  --check-for-yagna true \
  --subnet-tag ${SUBNET:-bor_proxy_subnet} \
  --num-instances ${NUM_INSTANCES:-2} \
  --service ${SERVICE_NAME:-bor-service}


