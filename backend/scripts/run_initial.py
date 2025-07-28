import os
import subprocess
import json
import time
import sys


class RunInitialMain:

    def __init__(self,work_dir):
        self.work_dir=work_dir
        self.terraform_dir = "terraform_files"
        self.shell_file_path = "shell_files/script-local.sh"

        self.terraform_complete_path=os.path.join(self.work_dir,self.terraform_dir)
        self.shell_complete_path = os.path.join(self.work_dir,self.shell_file_path)

    # Run a command and capture output
    def run_command(self,command, cwd=None):
        result = subprocess.run(command, cwd=cwd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Error running command: {command}\n{result.stderr}")
            exit(result.returncode)
        return result.stdout

    # Run Terraform commands
    def terraform_init(self):
        print("\033[1mInitializing Terraform...")
        self.run_command("terraform init", cwd=self.terraform_complete_path)

    def terraform_plan(self):
        print("\033[1mRunning Terraform plan...")
        self.run_command("terraform plan", cwd=self.terraform_complete_path)

    def terraform_apply(self):
        print("\033[1mApplying Terraform configuration...")
        self.run_command("terraform apply -auto-approve", cwd=self.terraform_complete_path)

    # Extract the public IP from terraform.tfstate
    def get_instance_ip(self):

        terraform_dir=self.terraform_complete_path

        tfstate_path = os.path.join(terraform_dir, "terraform.tfstate")
        if not os.path.exists(tfstate_path):
            print("terraform.tfstate file not found.")
            exit(1)

        with open(tfstate_path, "r") as tfstate_file:
            tfstate = json.load(tfstate_file)

        try:
            resources = tfstate["resources"]
            for resource in resources:
                if resource["type"] == "aws_instance":
                    for instance in resource.get("instances", []):
                        attributes = instance.get("attributes", {})
                        if "public_ip" in attributes:
                            return attributes["public_ip"]
        except KeyError as e:
            print(f"Error extracting IP: {e}")
            exit(1)

        print("Public IP not found in terraform.tfstate.")
        exit(1)

    # Update the IP in the shell script
    def update_ip_in_script(self,ip):

        shell_file_path=self.shell_complete_path

        if not os.path.exists(shell_file_path):
            print(f"Shell file {shell_file_path} not found.")
            exit(1)

        updated_lines = []
        with open(shell_file_path, "r") as file:
            for line in file.readlines():
                if line.startswith("IP="):
                    updated_lines.append(f'IP="{ip}"\n')
                else:
                    updated_lines.append(line)

        with open(shell_file_path, 'w') as file:
            file.writelines(updated_lines)


        print(f"\033[1mUpdated IP in {shell_file_path} to {ip}")


    # Function to execute the shell script
    def execute_shell_script(self):
        shell_file_path=self.shell_complete_path
        print("\033[1mSetting up Instance Prerequisites before setting up Jenkins Credentials, Jobs...")
        print()
        print()
        anchor_animation=['\r\033[1m\033[34mA          ]  ','\r\033[1m\033[34mau         ]- ',
                        '\r\033[1m\033[34mAuT        ]-)','\r\033[1m\033[34mauT0       ]  ',
                        '\r\033[1m\033[34mauTOa      ]-)  ','\r\033[1m\033[34mauToan     ]  ',
                        '\r\033[1m\033[34mAutOanc    ]-  ','\r\033[1m\033[34maut0anch   ]-)  ',
                        '\r\033[1m\033[34mautoancho  ]-  ','\r\033[1m\033[34mAut0anchor ]  ']
        for i in range(70): #from 70
            for iter in anchor_animation:
                sys.stdout.write(iter)
                time.sleep(0.2)
        print('\033[1m\033[34m______________WELCOME_______________')


        print("\r\033[0mExecuting shell script now...")
        print (shell_file_path)
        # Quote the path to handle spaces in directories
        result = subprocess.run(f"sh '{shell_file_path}'", shell=True)

        # Check the result of the shell execution
        if result.returncode == 0:
            print("Shell script executed successfully.")
        else:
            print(f"Shell script execution failed with exit code {result.returncode}.")


# Main script flow
def main(work_dir):

    run= RunInitialMain(work_dir)

    run.terraform_init()
    run.terraform_plan()
    run.terraform_apply()
    instance_ip = run.get_instance_ip()
    print(f"Extracted instance IP: {instance_ip}")
    run.update_ip_in_script(instance_ip)
    print("Script execution completed successfully.")
    run.execute_shell_script()

if __name__ == "__main__":
    main()
