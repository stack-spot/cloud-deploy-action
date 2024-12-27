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


def deployment(application_name, runtime_name, deploy_headers, json_data):
    print(f'⚙️ Deploying application "{application_name}" in runtime: "{runtime_name}".')
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


def check_deployment_status(application_name, runtime_name, deployment_id, application_id, deploy_headers):
    status_url = f"https://cloud-cloud-platform-api.prd.stackspot.com/v1/deployments/details/{deployment_id}"
    application_portal_url = "https://cloud.prd.stackspot.com/applications"

    i = 0
    while True:
        print(f'⚙️ Checking application "{application_name}" deployment status in runtime: "{runtime_name}" ({i}).')
        response = requests.get(url=status_url, headers=deploy_headers)

        if response.status_code == 200:
            deployment_status = response.json().get("deploymentStatus")
            if deployment_status == "UP":
                print(f'✅ Deployment concluded ({deployment_status}) for application "{application_name}" in runtime: "{runtime_name}".')
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

application_name = yaml_data['metadata']['name']
application_id = yaml_data['metadata']['id']
runtime_id = yaml_data['spec']['runtime']['id']
runtime_name = yaml_data['spec']['runtime'].get('name', 'Default Runtime')
image_url = yaml_data['spec']['imageUrl']
container_port = yaml_data['spec']['containerPort']
health_check_path = yaml_data['spec']['healthCheckPath']
env_vars = yaml_data.get('spec', {}).get('envVars', [])
secret_vars = yaml_data.get('spec', {}).get('secretVars', [])
mem = yaml_data['spec']['runtime']['memory']
cpu = yaml_data['spec']['runtime']['cpu']
replica_min = yaml_data['spec']['runtime']['replicaNum']['min']
replica_max = yaml_data['spec']['runtime']['replicaNum']['max']

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
deployment_id = deployment(application_name, runtime_name, deploy_headers, json_data)
check_deployment_status(application_name, runtime_name, deployment_id, application_id, deploy_headers)