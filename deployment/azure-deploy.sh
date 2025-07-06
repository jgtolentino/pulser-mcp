#!/bin/bash

# Azure deployment script for Pulser MCP Server
# This script deploys the MCP server to Azure Container Instances

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-pulser-mcp-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-pulsermcpacr}"
CONTAINER_NAME="${CONTAINER_NAME:-pulser-mcp-server}"
IMAGE_NAME="pulser-mcp-server"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Azure deployment of Pulser MCP Server...${NC}"

# Check if logged in to Azure
echo -e "${YELLOW}Checking Azure login status...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}Not logged in to Azure. Please run 'az login' first.${NC}"
    exit 1
fi

# Create resource group if it doesn't exist
echo -e "${YELLOW}Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION --output table

# Create Azure Container Registry if it doesn't exist
echo -e "${YELLOW}Creating Azure Container Registry...${NC}"
if ! az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    az acr create --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME \
        --sku Basic \
        --admin-enabled true \
        --output table
fi

# Get ACR credentials
echo -e "${YELLOW}Getting ACR credentials...${NC}"
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t $IMAGE_NAME:$IMAGE_TAG ..

# Tag image for ACR
echo -e "${YELLOW}Tagging image for ACR...${NC}"
docker tag $IMAGE_NAME:$IMAGE_TAG $ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG

# Login to ACR
echo -e "${YELLOW}Logging in to ACR...${NC}"
echo $ACR_PASSWORD | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin

# Push image to ACR
echo -e "${YELLOW}Pushing image to ACR...${NC}"
docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG

# Create PostgreSQL database (optional)
if [ "${DEPLOY_DATABASE}" = "true" ]; then
    echo -e "${YELLOW}Creating Azure Database for PostgreSQL...${NC}"
    az postgres server create \
        --resource-group $RESOURCE_GROUP \
        --name ${CONTAINER_NAME}-db \
        --location $LOCATION \
        --admin-user mcp_admin \
        --admin-password "${DB_PASSWORD:-SecurePassword123!}" \
        --sku-name B_Gen5_1 \
        --version 11 \
        --output table
    
    # Enable pgvector extension
    az postgres server configuration set \
        --resource-group $RESOURCE_GROUP \
        --server-name ${CONTAINER_NAME}-db \
        --name shared_preload_libraries \
        --value "vector"
fi

# Deploy container instance
echo -e "${YELLOW}Deploying container instance...${NC}"
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --dns-name-label $CONTAINER_NAME \
    --ports 8000 \
    --cpu 1 \
    --memory 1.5 \
    --environment-variables \
        APP_NAME="Pulser MCP Server" \
        DEBUG=false \
        DATABASE_URL="${DATABASE_URL}" \
        AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}" \
        AZURE_OPENAI_KEY="${AZURE_OPENAI_KEY}" \
        OPENAI_API_KEY="${OPENAI_API_KEY}" \
        ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
        JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}" \
    --output table

# Get container details
echo -e "${YELLOW}Getting container details...${NC}"
FQDN=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --query ipAddress.fqdn \
    -o tsv)

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}MCP Server URL: http://$FQDN:8000${NC}"
echo -e "${GREEN}API Documentation: http://$FQDN:8000/docs${NC}"

# Optional: Set up Azure Application Gateway for HTTPS
if [ "${SETUP_HTTPS}" = "true" ]; then
    echo -e "${YELLOW}Setting up Application Gateway for HTTPS...${NC}"
    # ... Application Gateway setup commands ...
fi

# Optional: Set up monitoring
if [ "${SETUP_MONITORING}" = "true" ]; then
    echo -e "${YELLOW}Setting up Azure Monitor...${NC}"
    az monitor app-insights component create \
        --resource-group $RESOURCE_GROUP \
        --app ${CONTAINER_NAME}-insights \
        --location $LOCATION \
        --output table
fi

echo -e "${GREEN}To view logs:${NC}"
echo "az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"

echo -e "${GREEN}To delete all resources:${NC}"
echo "az group delete --name $RESOURCE_GROUP --yes"