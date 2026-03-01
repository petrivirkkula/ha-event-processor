#!/bin/bash
# Setup script for HA Event Processor deployment

set -e

echo "=== HA Event Processor Deployment Setup ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl is not installed. Please install kubectl first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "WARNING: docker is not installed. You will need to build the image manually."
fi

echo "✓ kubectl found"

# Get cluster info
echo ""
echo "Current Kubernetes context: $(kubectl config current-context)"
echo "Available namespaces:"
kubectl get namespaces

# Ask for configuration
echo ""
read -p "Enter MQTT broker host [localhost]: " mqtt_host
mqtt_host=${mqtt_host:-localhost}

read -p "Enter MQTT broker port [1883]: " mqtt_port
mqtt_port=${mqtt_port:-1883}

read -p "Enter GCP project ID (optional): " gcp_project

# Ask about credentials
read -p "Do you have MQTT credentials? (y/n) [n]: " has_mqtt_creds
if [[ "$has_mqtt_creds" == "y" ]]; then
    read -p "Enter MQTT username: " mqtt_user
    read -sp "Enter MQTT password: " mqtt_pass
    echo ""
fi

# Update ConfigMap
echo ""
echo "Updating ConfigMap..."
kubectl patch configmap ha_event_processor-config -p \
  "{\"data\":{\"mqtt_broker_host\":\"$mqtt_host\",\"mqtt_broker_port\":\"$mqtt_port\",\"gcp_project_id\":\"$gcp_project\"}}" \
  --namespace=default || echo "ConfigMap not found, will be created during deploy"

# Update Secret if credentials provided
if [[ "$has_mqtt_creds" == "y" ]]; then
    echo "Updating Secret..."
    mqtt_user_b64=$(echo -n "$mqtt_user" | base64)
    mqtt_pass_b64=$(echo -n "$mqtt_pass" | base64)

    kubectl patch secret ha_event_processor-secrets -p \
      "{\"data\":{\"mqtt_username\":\"$mqtt_user_b64\",\"mqtt_password\":\"$mqtt_pass_b64\"}}" \
      --namespace=default || echo "Secret not found, will be created during deploy"
fi

# Handle GCP service account
if [ ! -z "$gcp_project" ]; then
    read -p "Do you have a GCP service account JSON file? (y/n) [n]: " has_gcp_file
    if [[ "$has_gcp_file" == "y" ]]; then
        read -p "Enter path to service account JSON file: " gcp_file
        if [ -f "$gcp_file" ]; then
            gcp_b64=$(cat "$gcp_file" | base64)
            kubectl patch secret ha_event_processor-secrets -p \
              "{\"data\":{\"gcp_service_account_json\":\"$gcp_b64\"}}" \
              --namespace=default || echo "Will be created during deploy"
            echo "✓ GCP credentials configured"
        else
            echo "ERROR: File not found: $gcp_file"
        fi
    fi
fi

# Deploy application
echo ""
read -p "Ready to deploy? (y/n) [y]: " deploy_now
if [[ "$deploy_now" != "n" ]]; then
    echo ""
    echo "Deploying HA Event Processor..."

    kubectl apply -f k3s/rbac.yaml
    echo "✓ RBAC configured"

    kubectl apply -f k3s/configmap.yaml
    echo "✓ ConfigMap created"

    kubectl apply -f k3s/secret.yaml
    echo "✓ Secret created"

    kubectl apply -f k3s/pvc.yaml
    echo "✓ PVC created"

    kubectl apply -f k3s/service.yaml
    echo "✓ Service created"

    kubectl apply -f k3s/deployment.yaml
    echo "✓ Deployment created"

    echo ""
    echo "Waiting for pod to be ready..."
    kubectl wait --for=condition=ready pod -l app=ha_event_processor --timeout=120s

    echo ""
    echo "=== Deployment Complete ==="
    echo ""
    echo "Next steps:"
    echo "1. Port-forward the service:"
    echo "   kubectl port-forward svc/ha-event-processor 8000:8000"
    echo ""
    echo "2. Check health:"
    echo "   curl http://localhost:8000/health"
    echo ""
    echo "3. View stats:"
    echo "   curl http://localhost:8000/stats"
    echo ""
    echo "4. View logs:"
    echo "   kubectl logs -f deployment/ha-event-processor"
fi

echo ""
echo "Done!"

