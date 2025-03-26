import os
import requests
import json
import time
from ruamel.yaml import YAML
from pathlib import Path
from io import StringIO

def yaml() -> YAML:
   yml = YAML()
   yml.indent(mapping=2, sequence=4, offset=2)
   yml.allow_unicode = True
   yml.default_flow_style = False
   yml.preserve_quotes = True
   return yml

def safe_load(content: str) -> dict:
   yml = yaml()
   return yml.load(StringIO(content))

def get_environment_urls(CLIENT_REALM):
    if CLIENT_REALM == "stackspot-dev":
        return {
            "auth": f"https://iam-auth-ssr.dev.stackspot.com/{CLIENT_REALM}/oidc/oauth/token",
            "deploy": "https://cloud-cloud-platform-horizon.dev.stackspot.com/v1/applications/deployments"
        }
    elif CLIENT_REALM == "stackspot-stg":
        return {
            "auth": f"https://iam-auth-ssr.stg.stackspot.com/{CLIENT_REALM}/oidc/oauth/token",
            "deploy": "https://cloud-cloud-platform-horizon.stg.stackspot.com/v1/applications/deployments"
        }
    elif CLIENT_REALM == "stackspot":
        return {
            "auth": f"https://idm.stackspot.com/{CLIENT_REALM}/oidc/oauth/token",
            "deploy": "https://cloud-platform-horizon.stackspot.com/v1/applications/deployments"
            # https://cloud-cloud-platform-horizon.prd.stackspot.com/v1/applications/deployments"
        }
    else:
        print(f"❌ Invalid CLIENT_REALM: {CLIENT_REALM}")
        exit(1)


def authentication(CLIENT_REALM, CLIENT_ID, CLIENT_KEY):
    urls = get_environment_urls(CLIENT_REALM)
    iam_url = urls["auth"]
    iam_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    iam_data = {
        "client_id": CLIENT_ID,
        "grant_type": "client_credentials",
        "client_secret": CLIENT_KEY
    }
    print(f"⚙️ Authenticating in {CLIENT_REALM}...")
    response = requests.post(url=iam_url, headers=iam_headers, data=iam_data)
    if response.status_code == 200:
        return response.json().get("access_token")
    print("❌ Authentication error")
    print(f"Status: {response.status_code}, Error: {response.text}")
    exit(1)

def check_deployment_status(application_name, runtime_name, deployment_id, application_id, deploy_headers):
    urls = get_environment_urls(CLIENT_REALM)
    stackspot_cloud_deployments_details_url = urls["deploy"]
    application_portal_url = "https://cloud.prd.stackspot.com/applications"

    i = 0
    while True:
        print(f'⚙️ Checking application "{application_name}" deployment status in runtime: "{runtime_name}" ({i}).')

        # Make the request to check the deployment status - CORRECTED URL
        r3 = requests.get(
            url=f"{stackspot_cloud_deployments_details_url}/{deployment_id}/status",  # Fixed string formatting
            headers=deploy_headers
        )

        if r3.status_code == 200:
            d3 = r3.json()
            deployment_status = d3.get("status")

            if deployment_status == "UP":
                print(f'✅ Deployment concluded ({deployment_status}) for application "{application_name}" in runtime: "{runtime_name}".')
                print(f"📊 Check the application status on {application_portal_url}/{application_id}/?tabIndex=0")
                break
            else:
                i = i+1
                print(f"⚙️ Current deployment status: {deployment_status}. Retrying in 5 seconds...")
        else:
            print("- Error getting deployment details")
            print("- Status:", r3.status_code)
            print("- Error:", r3.reason)
            print("- Response:", r3.text)
            exit(1)

        time.sleep(5)

def deployment(application_name, runtime_id, deploy_headers, data, CLIENT_REALM):
    urls = get_environment_urls(CLIENT_REALM)
    deploy_url = urls["deploy"]
    print(f'⚙️ Deploying "{application_name}" to {CLIENT_REALM}')
    response = requests.post(
        url=deploy_url,
        headers={
            "Authorization": deploy_headers["Authorization"],
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=data
    )
    if response.status_code == 200:
        return response.json().get("id")
    print("❌ Deployment error")
    print(f"Status: {response.status_code}, Error: {response.text}")
    exit(1)

# Environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_KEY = os.getenv("CLIENT_KEY")
CLIENT_REALM = os.getenv("CLIENT_REALM")
VERBOSE = os.getenv("VERBOSE")
APPLICATION_FILE = os.getenv("APPLICATION_FILE")
IMAGE_TAG = os.getenv("IMAGE_TAG")

if not all([CLIENT_ID, CLIENT_KEY, CLIENT_REALM, APPLICATION_FILE]):
   print("❌ Missing required environment variables!")
   exit(1)

with open(Path(APPLICATION_FILE), 'r') as file:
   yaml_data = safe_load(file.read())

print(yaml_data)

# Extract data from YAML
metadata = yaml_data.get('metadata', {})
spec = yaml_data.get('spec', {})

application_name = metadata.get('name')
application_id = metadata.get('id', metadata.get('stackspot', {}).get('applicationId'))
app_version = metadata.get('appVersion')
tags = metadata.get('tags', [])
labels = metadata.get('labels', [])
runtime_id = spec.get('runtimeId')
deploy_template = spec.get('deployTemplate')
deploy_template_values = spec.get('deployTemplateValues', {})

required_fields = {
    "application_name": application_name,
    "application_id": application_id,
    "app_version": app_version,
    "runtime_id": runtime_id,
    "deploy_template": deploy_template,
}

missing_fields = [field for field, value in required_fields.items() if not value]

if missing_fields:
    print("❌ Missing required fields in the YAML file:")
    for field in missing_fields:
        print(f"- {field}")
    exit(1)

if not IMAGE_TAG:
    print("❌ Image Tag to deploy not informed.")
    exit(1)

# Update the image tag in deployTemplateValues
if 'image' in deploy_template_values:
    deploy_template_values['image']['tag'] = IMAGE_TAG

# Prepare deployment data
data = {
    "apiVersion": yaml_data.get('apiVersion'),
    "kind": yaml_data.get('kind'),
    "metadata": {
        "id": application_id,
        "name": application_name,
        "appVersion": app_version,
        "tags": tags,
        "labels": labels,
    },
    "spec": {
        "deployTemplate": deploy_template,
        "runtimeId": runtime_id,
        "deployTemplateValues": deploy_template_values,
    }
}

if VERBOSE:
    print("🕵️ DEPLOYMENT REQUEST DATA:", json.dumps(data, indent=2))

# Execute deployment
access_token = authentication(CLIENT_REALM, CLIENT_ID, CLIENT_KEY)
deploy_headers = {"Authorization": f"Bearer {access_token}"}
deployment_id = deployment(application_name, runtime_id, deploy_headers, data, CLIENT_REALM)
check_deployment_status(application_name, runtime_id, deployment_id, application_id, deploy_headers)