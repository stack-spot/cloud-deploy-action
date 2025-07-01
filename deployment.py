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
            "auth": f"https://iam-auth-ssr.dev.stackspot.com/stackspot-dev/oidc/oauth/token",
            "deploy": "https://cloud-platform-horizon.dev.stackspot.com/v1/applications/deployments" # INTERNAL
        }
    elif CLIENT_REALM == "stackspot-stg":
        return {
            "auth": f"https://iam-auth-ssr.stg.stackspot.com/stackspot-dev/oidc/oauth/token",
            "deploy": "https://cloud-platform-horizon.stg.stackspot.com/v1/applications/deployments" # INTERNAL
        }
    else:
        return {
            "auth": f"https://idm.stackspot.com/{CLIENT_REALM}/oidc/oauth/token",
            "deploy": "https://cloud-platform-horizon.stackspot.com/v1/applications/deployments"
        }


def authentication(CLIENT_REALM, CLIENT_ID, CLIENT_KEY):
    urls = get_environment_urls(CLIENT_REALM)
    iam_url = urls["auth"]
    iam_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    iam_data = {
        "client_id": CLIENT_ID,
        "grant_type": "client_credentials",
        "client_secret": CLIENT_KEY
    }
    print(f"⚙️  Authenticating in {CLIENT_REALM}...")
    response = requests.post(url=iam_url, headers=iam_headers, data=iam_data)
    if response.status_code == 200:
        print("✅ Authentication successful")
        return response.json().get("access_token")
    print("❌ Authentication error")
    print(f"Status: {response.status_code}, Error: {response.text}")
    exit(1)

def deployment(application_name, runtime_id, deploy_headers, yaml_file_path, CLIENT_REALM, VERBOSE):
    urls = get_environment_urls(CLIENT_REALM)
    deploy_url = urls["deploy"]
    print(f'⚙️  Deploying "{application_name}" to {CLIENT_REALM} in runtime {runtime_id}')
    
    with open(yaml_file_path, 'r') as file:
        yaml_content = file.read()
    
    headers = {
        "Authorization": deploy_headers["Authorization"],
        "Content-Type": "application/yaml",
        "Accept": "application/json"
    }
    
    response = requests.post(
        url=deploy_url,
        headers=headers,
        data=yaml_content
    )
    
    if response.status_code == 200:
        print(f"✅ Application Deployment started successfully (ID: {response.json().get('metadata').get('id')})")
        if VERBOSE:
            print("🕵️  DEPLOYMENT RESPONSE DATA:", response.json())
        return response.json().get("metadata").get("id")  # This is the deploymentId
    else:
        print("❌ Application Deployment failed!")
        print(f"Status: {response.status_code}, Error: {response.reason}")
        if VERBOSE:
            print("🕵️  ERROR RESPONSE DATA:", response.text)
        exit(1)

def check_deployment_status(application_name, runtime_name, deployment_id, application_id, deploy_headers, VERBOSE, first_check, backoff_initial, backoff_max, backoff_factor, backoff_max_retries):
    urls = get_environment_urls(CLIENT_REALM)
    stackspot_cloud_deployments_details_url = urls["deploy"]
    application_portal_url = "https://stackspot.com/applications"

    # Configuração do backoff via env
    initial = int(os.getenv("BACKOFF_INITIAL", 5))
    max_backoff = int(os.getenv("BACKOFF_MAX", 60))
    factor = float(os.getenv("BACKOFF_FACTOR", 2))
    max_retries = int(os.getenv("BACKOFF_MAX_RETRIES", 10))

    i = 0
    backoff = initial
    while True:
        print(f'⚙️  Checking application "{application_name}" deployment status in runtime: "{runtime_name}" ({i}).')

        response = requests.get(
            url=f"{stackspot_cloud_deployments_details_url}/{deployment_id}/health",
            headers=deploy_headers
        )

        if response.status_code == 200:
            data = response.json()
            if VERBOSE:
                print(f"🕵️  CHECK DEPLOYMENT STATUS DATA ({i}):", data)

            pods = data.get("status", {}).get("pods", [])
            health_statuses = [pod.get("healthStatus") for pod in pods]

            if any(status == "Healthy" for status in health_statuses):
                print(f'✅ Deployment concluded (Healthy) for application "{application_name}" in runtime: "{runtime_name}".')
                print(f"📊 Check the application status on {application_portal_url}/{application_id}/?tabIndex=0")
                break
            elif all(status in ["Unknown", "Progressing", "Degraded"] for status in health_statuses):
                i += 1
                print(f"⚙️  Deployment is still in progress. Current pod statuses: {health_statuses}. Retrying in {backoff} seconds...")
            elif all(status in ["Suspended", "Missing"] for status in health_statuses):
                print(f'❌ Deployment failed for application "{application_name}" in runtime: "{runtime_name}".')
                print(f"📊 Check the application status on {application_portal_url}/{application_id}/?tabIndex=0")
                exit(1)
            else:
                print(f"⚙️  Mixed pod statuses detected: {health_statuses}. Retrying in {backoff} seconds...")
        else:
            print("❌ Error getting deployment details")
            print(f"Status: {response.status_code}, Error: {response.reason}")
            exit(1)

        if first_check:
            break

        if i >= max_retries:
            print(f"❌ Max retries ({max_retries}) reached. Exiting.")
            exit(1)

        time.sleep(backoff)
        backoff = min(max_backoff, int(backoff * factor))
        i += 1

# Environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_KEY = os.getenv("CLIENT_KEY")
CLIENT_REALM = os.getenv("CLIENT_REALM")
VERBOSE = os.getenv("VERBOSE")
APPLICATION_FILE = os.getenv("APPLICATION_FILE")

# Backoff configuration
BACKOFF_INITIAL = int(os.getenv("BACKOFF_INITIAL", 5))
BACKOFF_MAX = int(os.getenv("BACKOFF_MAX", 60))
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", 2))
BACKOFF_MAX_RETRIES = int(os.getenv("BACKOFF_MAX_RETRIES", 10))

if not all([CLIENT_ID, CLIENT_KEY, CLIENT_REALM, APPLICATION_FILE]):
    print("❌  Missing required environment variables!")
    exit(1)

# Load the YAML file to extract metadata for logging purposes
with open(Path(APPLICATION_FILE), 'r') as file:
    yaml_data = safe_load(file.read())

# Extract data from YAML
metadata = yaml_data.get('metadata', {})
spec = yaml_data.get('spec', {})

application_name = metadata.get('name')
app_version = metadata.get('version')
runtime_id = spec.get('runtimeId')
application_id = spec.get('applicationId')

required_fields = {
    "application_name": application_name,
    "runtime_id": runtime_id,
}

missing_fields = [field for field, value in required_fields.items() if not value]

if missing_fields:
    print("❌  Missing required fields in the YAML file:")
    for field in missing_fields:
        print(f"- {field}")
    exit(1)

# Authenticate
access_token = authentication(CLIENT_REALM, CLIENT_ID, CLIENT_KEY)
deploy_headers = {"Authorization": f"Bearer {access_token}"}

# Start deployment by sending the YAML file directly
deployment_id = deployment(application_name, runtime_id, deploy_headers, APPLICATION_FILE, CLIENT_REALM, VERBOSE)
# Wait 5s to guarantee async process
time.sleep(5)
# Check deployment status
check_deployment_status(
    application_name, runtime_id, deployment_id, application_id, deploy_headers, VERBOSE, False,
    BACKOFF_INITIAL, BACKOFF_MAX, BACKOFF_FACTOR, BACKOFF_MAX_RETRIES
)