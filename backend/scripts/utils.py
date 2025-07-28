import os,re,subprocess
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from openai import OpenAI
from dotenv import load_dotenv
from templates import *
import xml.etree.ElementTree as ET
import json
import subprocess
from pathlib import Path
load_dotenv()
from e2e.encrypt_local import *
from cryptography.fernet import Fernet
import json
from constants import * 


OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

default_values = ["",0,0.0,False,[],{}]


class DirectoryHandler:

    def __init__(self):
        pass

    def get_files_in_dir(self, dir:str, file_type:Optional[str]=None):
        paths = []
        for root, dirs, files in os.walk(dir):
            for file in files:
                if file_type:       
                    if file.endswith(file_type):
                        file_path = os.path.join(root, file)
                        paths.append(file_path)
                else:
                    file_path = os.path.join(root, file)
                    paths.append(file_path)
        return paths
    
    def find_folder(self, folder_name):
        """Find the absolute path of a folder in the user's home directory."""

        base_directory = Path.home()  
    
        for root, dirs, _ in os.walk(base_directory):
            if folder_name in dirs:
                absolute_path = os.path.join(root, folder_name)
                return absolute_path
        
        return None

    

class RequirementsGen(DirectoryHandler):

    def __init__(self):
        pass

    def find_imports(self, file_path:str):                                 
        with open(file_path, 'r') as file:
            first_lines = []
            for line in file:
                line = line.strip()  # Remove leading/trailing spaces
                # Skip empty lines or comments
                if not line or line.startswith("#"):
                    continue

                if line.startswith("import "):
                    # Extract module names after "import"
                    modules = line[7:].split(',')
                    for module in modules:
                        # Split by ' as ' to remove alias, if present
                        module_name = module.split(' as ')[0].split('.')[0].strip()  # Get base module name
                        first_lines.append(module_name)

                elif line.startswith("from "):
                    # Match pattern: "from <module> import <something> [as <alias>]"
                    match = re.match(r"from\s+([a-zA-Z0-9_\.]+)\s+import", line)
                    if match:
                        # Extract the module name and remove aliases, if any
                        module_name = match.group(1).split('.')[0]  # Get base module name
                        first_lines.append(module_name)

            # Remove duplicates
            first_lines = list(set(first_lines))
            return first_lines

    def find_env_libraries(self, list_of_imports: list, environment_path: str):

        command = [environment_path, '-m', 'pip', 'freeze']
        
        result = subprocess.run(command, capture_output=True, text=True)

        # Print the result for debugging
        print("Pip Freeze Command Output:")
        print(result.stdout)  # Output of the `pip freeze` command

        # Capture the output from the subprocess
        installed_packages = result.stdout.splitlines()
        matching_libraries = []

        # Match libraries in the list with installed packages from `pip freeze`
        for lib in list_of_imports:
            for package in installed_packages:
                if lib.lower() == package.split('==')[0].lower():  # Match only package names
                    matching_libraries.append(package)

        return matching_libraries
    
    
    def generate_req_file(self, req_file_path:str, matching_libraries:str):
        with open(req_file_path+"/requirements.txt", 'w') as file:
            for lib in matching_libraries:  # Write each library to requirements.txt line by line
                file.write(lib + '\n')

            print("requirements.txt has been generated")
        return 
    

class AWSCLI:
    def __init__(self, region_name="us-east-1"):
        """
        Initialize the AWSChecker class with a specific region.
        """
        self.region_name = region_name
        try:
            self.ec2_client = boto3.client("ec2", region_name=self.region_name)
        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"Error with AWS credentials: {e}")
            raise
    
    def list_keypairs(self):
        """
        List all key pairs in the region.
        """
        try:
            response = self.ec2_client.describe_key_pairs()
            key_pairs = response.get("KeyPairs", [])
            return [{"KeyName": kp["KeyName"], "KeyFingerprint": kp["KeyFingerprint"]} for kp in key_pairs]
        except self.ec2_client.exceptions.ClientError as e:
            print(f"Error fetching key pairs: {e}")
            return []

    
    def check_region(self):
        """
        Verify the current region and list available regions.
        """
        ec2 = boto3.client("ec2")
        response = ec2.describe_regions()
        available_regions = [region["RegionName"] for region in response["Regions"]]
        is_region_valid = self.region_name in available_regions
        return {
            "current_region": self.region_name,
            "is_valid": is_region_valid,
            "available_regions": available_regions
        }
    
    def check_vpc(self):
        """
        List all VPCs in the region.
        """
        response = self.ec2_client.describe_vpcs()
        vpcs = response.get("Vpcs", [])
        return [{"VpcId": vpc["VpcId"], "CidrBlock": vpc["CidrBlock"]} for vpc in vpcs]
    
    def check_subnets(self):
        """
        List all subnets in the region.
        """
        response = self.ec2_client.describe_subnets()
        subnets = response.get("Subnets", [])
        return [{"SubnetId": subnet["SubnetId"], "VpcId": subnet["VpcId"], "CidrBlock": subnet["CidrBlock"]} for subnet in subnets]
    
    def check_security_groups(self):
        """
        List all security groups in the region.
        """
        response = self.ec2_client.describe_security_groups()
        security_groups = response.get("SecurityGroups", [])
        return [{"GroupId": sg["GroupId"], "GroupName": sg["GroupName"], "Description": sg["Description"]} for sg in security_groups]

    def list_running_instances(self):
        """
        List all running EC2 instances with their instance ID, state, and IP addresses.
        """
        try:
            response = self.ec2_client.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            instances_info = []
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_info = {
                        "InstanceId": instance.get("InstanceId"),
                        "InstanceType": instance.get("InstanceType"),
                        "PrivateIpAddress": instance.get("PrivateIpAddress"),
                        "PublicIpAddress": instance.get("PublicIpAddress"),
                        "State": instance.get("State", {}).get("Name"),
                        "Tags": instance.get("Tags", [])
                    }
                    instances_info.append(instance_info)
            return instances_info
        except self.ec2_client.exceptions.ClientError as e:
            print(f"Error fetching instances: {e}")
            return []


class PythonEnvironments():

    def get_python_version(self, python_path):
        """Get the Python version of a given executable."""
        try:
            output = subprocess.check_output([python_path, "--version"], stderr=subprocess.STDOUT, text=True)
            return output.strip()  # Returns output like 'Python 3.x.x'
        except Exception as e:
            return f"Error: {e}"

    def find_global_pythons(self):
        """Find Python interpreters in global paths, excluding config files."""
        paths = ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin"]
        interpreters = []
        for path in paths:
            for python in Path(path).glob("python*"):
                if python.is_file() and not any(
                    suffix in python.name for suffix in ["-config", "check-easy-install-script"]
                ):
                    interpreters.append(str(python))
        return interpreters

    def find_conda_envs(self):
        """Find Conda environments using `conda env list`."""
        try:
            output = subprocess.check_output(["conda", "env", "list"], text=True)
            envs = []
            for line in output.splitlines():
                if line.strip() and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) > 1:
                        env_path = Path(parts[-1]) / "bin/python"
                        if env_path.is_file():
                            envs.append(str(env_path))
            return envs
        except FileNotFoundError:
            return []

    def find_virtualenvs_in_current_directory(self, current_dir):
        """Find Python virtual environments in the current directory."""
        venvs = []
        typical_env_names = ["venv", ".venv"]  # Common virtual environment folder names
        current_dir = Path(current_dir)
        for name in typical_env_names:
            venv_path = current_dir / name / "bin/python"  # Adjust for Windows if needed
            if venv_path.is_file():
                venvs.append(str(venv_path))

        return venvs if venvs else []


class ContextGenerator(DirectoryHandler):

    def __init__(self):
        super().__init__()

    def analyze_project(self, directory: str) -> dict:
        """
        Analyzes a directory to determine the Python application type,
        working directory, and entrypoint.
        """
        python_files = self.get_files_in_dir(directory, ".py")
        
        # --- 1. Check for Django (file-based detection) ---
        all_project_files = self.get_files_in_dir(directory)
        for file_path in all_project_files:
            if os.path.basename(file_path) == "manage.py":
                return {
                    "app_type": "Django",
                    "work_dir": os.path.dirname(file_path),
                    "entrypoint": os.path.basename(file_path),
                }

        # --- 2. Check for other web frameworks (content-based detection) ---
        framework_signatures = {
            "Streamlit": ["import streamlit"],
            "FastAPI": ["import fastapi", "FastAPI("],
            "Flask": ["import flask", "Flask(__name__)"],
            "Dash": ["import dash"],
        }
        
        candidate_entrypoints = {}
        for file_path in python_files:
            # Streamlit rule: entrypoint cannot be in a 'pages' subfolder
            if "streamlit" in file_path.lower() and "/pages/" in file_path.replace("\\", "/"):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for framework, signatures in framework_signatures.items():
                        if any(sig in content for sig in signatures):
                            candidate_entrypoints[file_path] = framework
                            break # Found a framework, move to next file
            except Exception:
                # Silently ignore files that can't be read
                continue
        
        # Prioritize common entrypoint names like 'app.py' or 'main.py'
        if candidate_entrypoints:
            preferred_names = ['app.py', 'main.py', 'application.py']
            for name in preferred_names:
                for path, framework in candidate_entrypoints.items():
                    if os.path.basename(path) == name:
                        return {
                            "app_type": framework,
                            "work_dir": os.path.dirname(path),
                            "entrypoint": os.path.basename(path),
                        }
            # If no preferred name is found, return the first candidate
            first_path, first_framework = list(candidate_entrypoints.items())[0]
            return {
                "app_type": first_framework,
                "work_dir": os.path.dirname(first_path),
                "entrypoint": os.path.basename(first_path),
            }

        # --- 3. Fallback: Check for a generic script with a main block ---
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if 'if __name__ == "__main__":' in f.read():
                        return {
                            "app_type": "Script",
                            "work_dir": os.path.dirname(file_path),
                            "entrypoint": os.path.basename(file_path),
                        }
            except Exception:
                continue

        # --- 4. Final Fallback ---
        return {
            "app_type": "Unknown",
            "work_dir": directory,
            "entrypoint": None
        }
    

    def find_python_version(self, directory):

        py = PythonEnvironments()
        dropdown = dict()

        for python in py.find_global_pythons():
            version = py.get_python_version(python)
            dropdown[python] = version
            print(f"{python}: {version}")

        for conda_env in py.find_conda_envs():
            version = py.get_python_version(conda_env)
            dropdown[conda_env] = version
            print(f"{conda_env}: {version}")

        venvs = py.find_virtualenvs_in_current_directory(directory)
        if venvs:
            for venv in venvs:
                version = py.get_python_version(venv)
                dropdown[venv] = version
                print(f"{venv}: {version}")

        return dropdown

    
    def app_type(self):
        """For future when we go beyond python"""
        return "Streamlit"
    
    def working_dir_and_entrypoint(self, directory):
        
        work_dir, entrypoint = None, None
        folders = []
        for root, dirs, files in os.walk(directory):
            for d in dirs:
                folder_path = os.path.join(root, d)
                folders.append(folder_path)

        pythonfiles = self.get_files_in_dir(directory, ".py")

        flag = 0
        for file in pythonfiles:
            if "/pages" not in file:
                with open(file, 'r') as f:
                    contents = f.read()
                    if 'import streamlit' in contents or 'from streamlit' in contents:
                        entrypoint = file
                        work_dir = os.path.dirname(entrypoint)
                        flag = 1
   
        if not flag:
            print("No Streamlit entrypoint found")


        return work_dir, entrypoint


class DockerfileGen:

    def __init__(self, python_version, end_dir, entry_point, app_type):
        self.python_version = python_version
        self.end_dir = end_dir
        self.entry_point = entry_point
        self.app_type = app_type

    def generate(self,work_dir):

        messages = [
          {"role": "system", "content": "You are an assistant who writes Dockerfiles"},
          {
              "role": "user",
              "content": dockerfile_example + f"""Generate a dockerfile for 'python_version': {self.python_version}, 'type_of_application': {self.app_type}, 'work_directory_in_local': {self.end_dir}, 'entrypoint_filename': {self.entry_point}. Only give me the dockerfile in markdown and no other explanations. Make sure you copy from '.' while copying the folder to src."""
          }
        ]

        api_key = OPENAI_API_KEY
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        unclean_dockerfile = completion.choices[0].message.content
        print(completion.choices[0].message.content)
        dockerfile_pattern = re.compile(r"(FROM[\s\S]+?CMD\s+\[.*?\])", re.MULTILINE)
        match = dockerfile_pattern.search(unclean_dockerfile)

        if match:
            dockerfile_content = match.group(1)
            print("\nSUCCESSFULLY GENERATED DOCKERFILE !!")
        else:
            print("COULD NOT GENERATE DOCKERFILE !!")

        work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed

        # Generate the Jenkinsfile path using os.path.join()
        dockerfile_path = os.path.join(work_dir, "Dockerfile")

        with open(dockerfile_path, "w") as file:         
            file.write(dockerfile_content)

    def docker_version(self):
        with open(DOCKER_VERSION_PATH) as file:
            data = json.load(file)
        version = data['version']
        return version

    def docker_appname(self):
        with open(DOCKER_VERSION_PATH) as file:
            data = json.load(file)
        name = data['name']
        return name


class TerraformGen:
    def __init__(self, keypairname=None, region=None, s3_bucket_name=None, instance_type=None, vpc_id=None, public_subnets=None, usergroup=None, security_group=None):
        
        # if keypairname is None:
        #     raise ValueError("keypairname is a mandatory field and cannot be None.")

        self.region = region if region else "us-east-1"
        self.s3_bucket_name = s3_bucket_name if s3_bucket_name else None
        self.keypairname = keypairname if keypairname else None
        self.instance_type = instance_type if instance_type else "t2.micro"
        self.vpc_id = vpc_id if vpc_id else "vpc-08d33290f169c4dc3"
        self.public_subnets = public_subnets if public_subnets else '["0.0.0.0/0"]'
        self.usergroup = usergroup if usergroup else None
        self.security_group = security_group

    def increment_version(self, value):
        match = re.search(r'v(\d+)$', value)
        if match:
            current_version = int(match.group(1))
            new_version = f"v{current_version + 1}"
            return value[:match.start()] + new_version
        return value

    def generate(self,work_dir):

        data_dictionary={"region":self.region,
                         "s3bucketname":self.s3_bucket_name,
                         "keypair_name":self.keypairname,
                         "user_data":"jenkins-install.sh",
                         "instance_type":self.instance_type,
                         "vpc_id":self.vpc_id,
                         "public_subnet":self.public_subnets,
                         "usergroup":self.usergroup,
                         "security_group":self.security_group}
        
        data_dictionary = {key: value for key, value in data_dictionary.items() if value is not None}

        file_path = TERRAFORM_VERSION_PATH

        with open(file_path, 'r') as file:
            data = json.load(file)

        task = f"""
            Similarly, generate terraform files while replacing with these values for
            """+str(data_dictionary)+ str(data) + """. Only give me the terraform file in markdown and no other explanations."""
        
        prompt = terraform_example + task

        api_key = OPENAI_API_KEY
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a terrafrom file generator."},
            {
                "role": "user",
                "content": prompt
            }
            ]
        )

        terrform_response = completion.choices[0].message.content

        for key, value in data.items():
            if isinstance(value, str): 
                data[key] = self.increment_version(value)

        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

        # Ensure work_dir is correctly set
        work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed

        folder_name = os.path.join(work_dir, "terraform_files")
        
        os.makedirs(folder_name, exist_ok=True)
        script_path = os.path.join(folder_name, "jenkins-install.sh")
        
        with open(script_path, "w") as script_file:
            script_file.write(script_content)
            
        pattern = r"hcl([\s\S]*?)```"
        terraform_pattern = re.compile(pattern, re.MULTILINE)
        match = terraform_pattern.search(terrform_response)

        if match:
            terrraform_content = match.group(1)
            print("\nSUCCESSFULLY GENERATED TERRAFORM !!")
        else:
            print("COULD NOT GENERATE TERRAFORM !!")

        with open(folder_name+"/main.tf", "w") as file:
            file.write(terrraform_content)
        


        print(f"Terraform files have been created in the '{folder_name}' directory.")


class JenkinsfileGen:

    def __init__(self, app_name, github_url, port, version):
        self.app_name = app_name
        self.github_url = github_url
        self.port = port
        self.version=version

    def generate(self,work_dir):

        task = f"""
            Similarly, generate a Jenkinsfile replacing the placehaolders <<>>. Replace it with these values:

            app name : {self.app_name}
            version : {self.version}
            github repo url : {self.github_url}
            port number : {self.port}
            
            Only give me the Jenkinfile in markdown and no other explanations.
        """

        api_key = OPENAI_API_KEY
        client = OpenAI(api_key=api_key)
        prompt = jenkinsfile_example + task

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Jenkinsfile generator."},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        unclean_jenkinsfile = completion.choices[0].message.content

        pattern = r"groovy([\s\S]*?)```"
        jenkinsfile_pattern = re.compile(pattern, re.MULTILINE)
        match = jenkinsfile_pattern.search(unclean_jenkinsfile)

        if match:
            jenkinsfile_content = match.group(1)
            print("\nSUCCESSFULLY GENERATED JENKINSFILE !!")
        else:
            print("COULD NOT GENERATE JENKINSFILE !!")

        work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed

        # Generate the Jenkinsfile path using os.path.join()
        jenkinsfile_path = os.path.join(work_dir, "Jenkinsfile")

        with open(jenkinsfile_path, "w") as file:         
            file.write(jenkinsfile_content)


class GithubSCM:

    def __init__(self, ssh_key=None):
        if ssh_key is None:
            self.ssh_key = ["~/.ssh/id_rsa", "~/.ssh/id_ed25519"]
        else:
            self.ssh_key = ssh_key

    def get_private_key_path(self):
        
        for key in self.ssh_key:
            expanded_key = os.path.expanduser(key)  # Expand ~ to full path
            if os.path.exists(expanded_key):
                return expanded_key

    def _github_ssh_key(self):

        private_key_path = self.get_private_key_path()
          
        if private_key_path:
        # Use the private key with SSH for GitHub
            ssh_command = f"ssh -T -i {private_key_path} git@github.com"
            try:
                # Run the SSH command to verify the connection
                result = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)


            except subprocess.CalledProcessError as e:

                if "Hi" in e.stderr:                                                    #It always shows error in subprocess after authentication success - since git cant run on shell
                    print("Succesfully Authenticated - SSH Key connects to Github")

                else:
                    print("ERROR - SSH Not valid with Github")

            else:
                if "Hi" in result.stdout:
                    print(f"Successfully connected using {private_key_path}")
                else:
                    print(f"Connection failed with {private_key_path}")
                    print("Output:", result.stdout)

        else:
            print("No valid SSH private key found in PATH.")
            return
        
        if os.path.exists(private_key_path):
            with open(private_key_path, "r") as file:
                key_string = file.read().strip() 

        else:
            print(f"File not found: {private_key_path}")
            return
        
        return key_string

        
    def github_repo_url(self, repo_path, prefer_ssh=True):

        if not os.path.isdir(repo_path):
            print(f"ERROR: The provided path '{repo_path}' is not a valid directory.")
            return None

        try:
            original_url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                stderr=subprocess.STDOUT,
                text=True,
                cwd=repo_path
            ).strip()

            final_url = original_url

            if prefer_ssh and original_url.startswith("https://"):
                https_pattern = r"^https://([^/]+)/(.+)$"
                ssh_replacement = r"git@\1:\2"
                converted_url = re.sub(https_pattern, ssh_replacement, original_url)

                if converted_url != original_url:
                    print(f"INFO: Converted HTTPS URL '{original_url}' to SSH format.")
                    final_url = converted_url
                else:
                    print(f"WARNING: URL started with https:// but regex conversion failed: {original_url}")

            elif original_url.startswith("git@"):
                 print(f"INFO: Retrieved URL is already in SSH format: {original_url}")
            else:
                 print(f"INFO: Retrieved URL is not HTTPS or SSH: {original_url}")

            print(f"Found Git repo URL '{final_url}' in {repo_path}")
            return final_url

        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to get 'origin' remote URL from '{repo_path}'.")
            print(f"       Command output:\n{e.output.strip()}")
            return None
        except FileNotFoundError:
            print(f"ERROR: 'git' command not found. Is Git installed and in PATH?")
            return None
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            return None
    

class CredentialsUpload(Encryption):
    """ Encryption Class comes from e2e.encrypt_local.py """

    def __init__(self,ssh_private_key,ssh_public_key):
        self.ssh_private_key = ssh_private_key
        self.ssh_public_key = ssh_public_key
        
        
    def save_encrypted_data(self):
        """ssh key and private key is entered, hashed ssh key hashed private key and rsa key are outputted
        these outputted values need to be uploaded to ec2
        in ec2 need to access these hashed data and decrypt the data
        need to use the data to dynamically update credentials in shellfile a well as credentials.xml"""

        password = "AUTOANCHORHASH"  #User can use their own extra password if they want

        # Generate RSA Key Pair
        rsa_private_key, rsa_public_key = self.generate_rsa_keys(password)

        # Generate AES Key
        aes_key = os.urandom(32)  # AES-256 Key

        # Assuming encrypt_aes function exists (AES encryption)
        encrypted_private = self.encrypt_aes(self.ssh_private_key, aes_key)
        encrypted_public = self.encrypt_aes(self.ssh_public_key, aes_key)

        # Encrypt AES Key with RSA Public Key
        encrypted_aes_key = self.encrypt_aes_key_using_rsa(aes_key, rsa_public_key)

        # Save Everything to File
        self.save_to_file(ENCRYPTED_KEYS_PATH, encrypted_aes_key, encrypted_private, encrypted_public, rsa_private_key)  #you can store rsa_private_key seperately as per your implementation for higher level security

        print("Encrypted data saved to file successfully!")


class JenkinsCredentialsXml(GithubSCM):

    def generate_credentials_xml(self,work_dir):
        
        ssh_data = self._github_ssh_key()
        
        if not ssh_data:
            print("Failed to retrieve SCM data.")
            return  

        try:
            # Parse the existing credentials.xml file
            work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed
            
            folder_name = os.path.join(work_dir, "shell_files")
        
            os.makedirs(folder_name, exist_ok=True)

            file_path = os.path.join(work_dir, 'shell_files/credentials.xml')

            with open(file_path, "w") as f:
                f.write(xml_creds)

        except Exception as e:
            print(f"An error occurred while updating credentials.xml: {e}")



    def generate_script_local_shell(self,work_dir):

        work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed
        
            # Get the parallel work directory
        work_dir_parallel = os.path.dirname(work_dir)  # Moves one level up

        folder_name = os.path.join(work_dir, "shell_files")

        os.makedirs(folder_name, exist_ok=True)

        cwd = os.getcwd()

        # Replace {work_dir} in script_local with actual path
        script_content = script_local.format(work_dir=work_dir,work_dir_parallel=cwd,ENCRYPTED_KEYS_PATH=ENCRYPTED_KEYS_PATH)

        sh_file_path = os.path.join(work_dir, 'shell_files/script-local.sh')

        with open(sh_file_path,'w') as file:
            file.write(script_content)
    

class JenkinsJobXml(GithubSCM):
    
    def generate_job_xml(self, work_dir):  

        repository_url = self.github_repo_url(work_dir)
        
        if not repository_url:
            print("Failed to retrieve github repo URL")
            return
        
        try:
            # Parse the existing credentials.xml file
            work_dir = os.path.abspath(work_dir)  # Converts to absolute path if needed
            
            folder_name = os.path.join(work_dir, "shell_files")
        
            os.makedirs(folder_name, exist_ok=True)


            file_path = os.path.join(work_dir, 'shell_files/streamlit-deploy-job.xml')


            with open(file_path, "w") as f:
                f.write(xml_job)

            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find the privateKey element
            repo_element = root.find(
                ".//hudson.plugins.git.UserRemoteConfig/url"
            )

            if repo_element is None:
                print("GitHub Repo URL element not found in the XML.")
                return

            # Insert the private key
            repo_element.text = repository_url.strip()

            # Write changes back to the file
            tree.write(file_path, encoding="UTF-8", xml_declaration=True)
            print(f"GitHub Repo URL successfully added to {file_path}.")

        except Exception as e:
            print(f"An error occurred while updating streamlit-deploy-job.xml: {e}")


    # def process_local_jenkins_jobs(self, work_dir): 
    #     output = []

    #     for root, _, files in os.walk(work_dir):
    #         for file in files:
    #             file_path = os.path.join(root, file)
    #             rel_path = os.path.relpath(file_path, work_dir)
    #             try:
    #                 with open(file_path, 'r', encoding='utf-8') as f:
    #                     content = f.read()
    #                 output.append({
    #                     "name": rel_path,
    #                     "code": content
    #                 })
    #             except Exception as e:
    #                 output.append({
    #                     "name": rel_path,
    #                     "code": f"Error reading file: {e}"
    #                 })

    #     print(json.dumps(output, indent=2))
    #     return output

class ReadAndUpdateGenerations:

    def read_files(self, filepaths):
        result = []
        for filepath in filepaths:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                result.append({
                    "name": filename,
                    "code": content
                })
            except Exception as e:
                result.append({
                    "filepath":filepath,
                    "name": filename,
                    "code": f"Error reading file: {e}"
                })
        return result

    def edit_file_with_prompt(self, filename: str, original_code: str, prompt: str):
        """Edits code using OpenAI API based on a natural language prompt."""
        task = f"""
        Edit the following file named `{filename}`.

        Original code:
        {original_code}

        Edit instruction:
        {prompt}

        Return only the updated code with no extra commentary.
        """

        try:
            api_key = OPENAI_API_KEY
            client = OpenAI(api_key=api_key)


            completion = client.chat.completions.create(
                model="gpt-4o-mini",  # You can use "gpt-4o-mini" or another available model
                messages=[
                    {"role": "system", "content": "You are a code editor AI."},
                    {"role": "user", "content": task}
                ],
                temperature=0.3
            )

            updated_code = completion.choices[0].message.content.strip()

            return {
                "filename": filename,
                "updated_code": updated_code
            }

        except Exception as e:
            return {
                "filename": filename,
                "updated_code": f"Error editing code: {e}"
            }
    
    def write_updated_code_to_file(self, original_filepath: str, updated_code: str):
        """
        Writes the updated code back to the original file path.
        
        Args:
            original_filepath (str): The full path to the file to be overwritten.
            updated_code (str): The new code content to write.
        
        Returns:
            dict: A result indicating success or failure.
        """
        try:
            with open(original_filepath, 'w', encoding='utf-8') as f:
                f.write(updated_code)
            return {
                "filepath": original_filepath,
                "status": "success",
                "message": "File updated successfully."
            }
        except Exception as e:
            return {
                "filepath": original_filepath,
                "status": "error",
                "message": f"Failed to write file: {e}"
            }


class CredentialsLocalStorage:
    """Handles ingestion of API key to backend from frontend and saving into file"""
    
    def __init__(self, fernet_key_path=FERNET_KEY_PATH, keys_file_path=KEYS_PATH):
        self.fernet_key_path = fernet_key_path
        self.keys_file_path = keys_file_path
        self.fernet = self._load_or_generate_key()

    def _load_or_generate_key(self):
        if os.path.exists(self.fernet_key_path):
            with open(self.fernet_key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.fernet_key_path, "wb") as f:
                f.write(key)
        return Fernet(key)

    def save_encrypted_keys(self, public_key: str, private_key: str):
        try:
            encrypted_data = {
                "public_key": self.fernet.encrypt(public_key.encode()).decode(),
                "private_key": self.fernet.encrypt(private_key.encode()).decode()
            }
            with open(self.keys_file_path, "w") as f:
                json.dump(encrypted_data, f)
        except Exception as e:
            raise RuntimeError(f"Error saving keys: {e}")
        
    def load_decrypted_keys(self):
        try:
            with open(self.keys_file_path, "r") as f:
                encrypted_data = json.load(f)

            return {
                "public_key": self.fernet.decrypt(encrypted_data["public_key"].encode()).decode(),
                "private_key": self.fernet.decrypt(encrypted_data["private_key"].encode()).decode()
            }
        except Exception as e:
            raise RuntimeError(f"Error loading keys: {e}")


def clean_key(decoded_private_key):
    start = "-----BEGIN OPENSSH PRIVATE KEY-----"
    end = "-----END OPENSSH PRIVATE KEY-----"
    start_index = decoded_private_key.find("-----BEGIN OPENSSH PRIVATE KEY-----")

    key_start = start_index + len(start)
    key_end = decoded_private_key.find(end, key_start)
    key = decoded_private_key[key_start:key_end]
    key = key.lstrip()
    key = key.rstrip()
    key_removed_spaces = key.replace(" ", "\n")
    fixed_key = start + "\n" + key_removed_spaces + "\n" + end
    
    return fixed_key


