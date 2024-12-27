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

def authentication(CLIENT_REALM, CLIENT_ID, CLIENT_KEY):
    iam_url = f"https://idm.stackspot.com/{CLIENT_REALM}/oidc/oauth/token"
    iam_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    iam_data = {
        "client_id": CLIENT_ID,
        "grant_type": "client_credentials",
        "client_secret": CLIENT_KEY
    }
    print("⚙️ Authenticating...")
    response = requests.post(url=iam_url, headers=iam_headers, data=iam_data)
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        print("✅ Successfully authenticated!")
        return access_token
    else:
        print("❌ Error during IAM authentication")
        print("- Status:", response.status_code)
        print("- Error:", response.reason)
        print("- Response:", response.text)
        exit(1)

def deployment(application_name, runtime_id, deploy_headers, json_data):
    print(f'⚙️ Deploying application "{application_name}" in runtime: "{runtime_id}".')
    deploy_url = "https://cloud-cloud-runtime-api.prd.stackspot.com/v1/deployments"
    response = requests.post(url=deploy_url, headers=deploy_headers, data=json_data)
    if response.status_code == 200:
        deployment_id = response.json().get("deploymentId")
        print(f"✅ DEPLOYMENT successfully started with ID: {deployment_id}")
        return deployment_id
    else:
        print("❌ Error starting cloud deployment")
        print("- Status:", response.status_code)
        print("- Error:", response.reason)
        print("- Response:", response.text)
        exit(1)

def check_deployment_status(application_name, runtime_id, deployment_id, application_id, deploy_headers):
    status_url = f"https://cloud-cloud-platform-api.prd.stackspot.com/v1/deployments/details/{deployment_id}"
    application_portal_url = "https://cloud.prd.stackspot.com/applications"
    i = 0
    while True:
        print(f'⚙️ Checking application "{application_name}" deployment status in runtime: "{runtime_id}" ({i}).')
        response = requests.get(url=status_url, headers=deploy_headers)
        if response.status_code == 200:
            deployment_status = response.json().get("deploymentStatus")
            if deployment_status == "UP":
                print(f'✅ Deployment concluded ({deployment_status}) for application "{application_name}" in runtime: "{runtime_id}".')
                print(f"📊 Check the application status on {application_portal_url}/{application_id}/?tabIndex=0")
                break
            else:
                print(f"⚙️ Current deployment status: {deployment_status}. Retrying in 5 seconds...")
        else:
            print("❌ Error getting deployment details")
            print("- Status:", response.status_code)
            print("- Error:", response.reason)
            print("- Response:", response.text)
            exit(1)
        time.sleep(5)

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

# Extract values directly from the top-level structure
application_name = yaml_data.get('applicationName')
application_id = yaml_data.get('applicationId')
runtime_id = yaml_data.get('runtimeId')
image_url = yaml_data.get('imageUrl')
container_port = yaml_data.get('containerPort')
health_check_path = yaml_data.get('healthCheckPath')
env_vars = yaml_data.get('envVars', [])
secret_vars = yaml_data.get('secretVars', [])
mem = yaml_data.get('mem')
cpu = yaml_data.get('cpu')
replica_min = yaml_data.get('replicaNum', {}).get('min')
replica_max = yaml_data.get('replicaNum', {}).get('max')

required_fields = {
    "application_name": application_name,
    "application_id": application_id,
    "runtime_id": runtime_id,
    "image_url": image_url,
    "container_port": container_port,
    "health_check_path": health_check_path,
    "mem": mem,
    "cpu": cpu,
    "replica_min": replica_min,
    "replica_max": replica_max,
}

# Verificar quais campos estão faltando
missing_fields = [field for field, value in required_fields.items() if not value]

if missing_fields:
    print("❌ Missing required fields in the YAML/JSON file:")
    for field in missing_fields:
        print(f"- {field}")
    exit(1)

if not IMAGE_TAG:
    print("❌ Image Tag to deploy not informed.")
    exit(1)

data = {
    "applicationId": application_id,
    "applicationName": application_name,
    "action": "DEPLOY",
    "containerPort": container_port,
    "healthCheckPath": health_check_path,
    "envVars": env_vars,
    "secretVars": secret_vars,
    "imageUrl": image_url,
    "tag": IMAGE_TAG,
    "runtimeId": runtime_id,
    "mem": mem,
    "cpu": cpu,
    "replicaNum": {
        "min": replica_min,
        "max": replica_max,
    }
}

json_data = json.dumps(data, indent=4)
if VERBOSE:
    print("🕵️ DEPLOYMENT REQUEST DATA:", json_data)

access_token = authentication(CLIENT_REALM, CLIENT_ID, CLIENT_KEY)
deploy_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
deployment_id = deployment(application_name, runtime_id, deploy_headers, json_data)
check_deployment_status(application_name, runtime_id, deployment_id, application_id, deploy_headers)