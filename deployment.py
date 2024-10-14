import os
import requests
import json
from ruamel.yaml import YAML
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


def save_output(name: str, value: str):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output_file:
        print(f'{name}={value}', file=output_file)


def build_pipeline_url() -> str:
    GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL")
    GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
    GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID")
    if None in [GITHUB_SERVER_URL, GITHUB_REPOSITORY, GITHUB_RUN_ID]:
        print("- Some mandatory GitHub Action environment variable is empty.")
        exit(1)
    url = f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"
    return url

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_KEY = os.getenv("CLIENT_KEY")
CLIENT_REALM = os.getenv("CLIENT_REALM")
VERBOSE = os.getenv("VERBOSE")
APPLICATION_FILE = os.getenv("APPLICATION_FILE")

inputs_list = [CLIENT_ID, CLIENT_KEY, CLIENT_REALM]

if None in inputs_list:
    print("- Some mandatory input is empty. Please, check the input list.")
    exit(1)

# Load the YAML content
yaml_data = yaml.safe_load(APPLICATION_FILE)

# Extract and check values from the YAML structure
application_name = yaml_data['metadata']['name']
runtime_name = yaml_data['spec']['runtime']['name']

application_id = yaml_data['metadata']['id']
if application_id is None:
        print("- Application ID not informed or couldn't be extracted.")
        exit(1) 
runtime_id = yaml_data['spec']['runtime']['id']
if runtime_id is None:
        print("- Runtime ID not informed or couldn't be extracted.")
        exit(1) 
image_url = yaml_data['spec']['container']['imageUrl']
if image_url is None:
        print("- Image URL not informed or couldn't be extracted.")
        exit(1) 
tag = yaml_data['spec']['container']['tag']
if tag is None:
        print("- TAG not informed or couldn't be extracted.")
        exit(1) 
container_port = yaml_data['spec']['container']['port']
if container_port is None:
        print("- Container Port not informed or couldn't be extracted.")
        exit(1) 
health_check_path = yaml_data['spec']['container']['healthCheckPath']
if health_check_path is None:
        print("- Health Check Path not informed or couldn't be extracted.")
        exit(1) 
env_vars = yaml_data['spec']['container']['envVars']
mem = yaml_data['spec']['runtime']['memory']
if mem is None:
        print("- Memory not informed or couldn't be extracted.")
        exit(1) 
cpu = yaml_data['spec']['runtime']['cpu']
if cpu is None:
        print("- CPU not informed or couldn't be extracted.")
        exit(1) 
replica_min = yaml_data['spec']['runtime']['replicaNum']['min']
if replica_min is None:
        print("- Replica MIN config not informed or couldn't be extracted.")
        exit(1) 
replica_max = yaml_data['spec']['runtime']['replicaNum']['max']
if replica_min is None:
        print("- Replica MAX config not informed or couldn't be extracted.")
        exit(1) 
replica_cpu = yaml_data['spec']['runtime']['replicaNum']['cpu']
if replica_min is None:
        print("- Replica CPU config not informed or couldn't be extracted.")
        exit(1) 

if VERBOSE is not None:
    print("- APPLICATION FILE:", yaml_data)

# Gather authentication data
iam_url_stg = [ f"https://iam-auth-ssr.stg.stackspot.com/{CLIENT_REALM}/oidc/oauth/token"]
iam_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
iam_data = {"client_id": f"{CLIENT_ID}", "grant_type": "client_credentials", "client_secret": f"{CLIENT_KEY}"}

print("Authenticating...")
r1 = requests.post(
        url=iam_url_stg, 
        headers=iam_headers, 
        data=iam_data
    )

if r1.status_code == 200:
    d1 = r1.json()
    access_token = d1["access_token"]
    print("Successfully authenticated!")

    # Create the DEPLOYMENT JSON structure
    data = {
        "applicationId": application_id,
        "action": "DEPLOY",
        "containerPort": container_port,
        "healthCheckPath": health_check_path,
        "envVars": env_vars,
        "imageUrl": image_url,
        "tag": tag,
        "runtimeId": runtime_id,
        "mem": mem,
        "cpu": cpu,
        "replicaNum": {
            "min": replica_min,
            "max": replica_max,
            "cpu": replica_cpu
        }
    }

    # Convert the dictionary to a JSON string
    json_data = json.dumps(data, indent=4)

    if VERBOSE is not None:
        print("- DEPLOYMENT REQUEST DATA:", json_data)
    
    deploy_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    print(f"Deploying application {application_name} in runtime: {runtime_name}.")
    stackspot_cloud_deployments_url_stg = "https://cloud-cloud-platform-api.stg.stackspot.com/v1/deployments"
    r2 = requests.post(
            url=stackspot_cloud_deployments_url_stg, 
            headers=deploy_headers,
            data=json_data
        )

    if r2.status_code == 201:
        d2 = r2.json()
        deploymentId = d2["deploymentId"]
        save_output('deployment_id', deploymentId)
        print(f"- DEPLOYMENT successfully started with ID: {deploymentId}")
   
    else:
        print("- Error starting cloud deployment")
        print("- Status:", r2.status_code)
        print("- Error:", r2.reason)
        print("- Response:", r2.text)    
        exit(1)

else:
    print("- Error during IAM authentication")
    print("- Status:", r1.status_code)
    print("- Error:", r1.reason)
    print("- Response:", r1.text)
    exit(1)