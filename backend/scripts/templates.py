
script_content = """#!/bin/bash
# Update the package list and upgrade installed packages
sudo yum update -y

# Upgrade packages
sudo yum upgrade -y

# Install Java (Amazon Corretto)
sudo dnf install java-17-amazon-corretto -y


# Add the Jenkins repository and GPG key
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key


# Install Jenkins
sudo yum install jenkins -y

# Enable and start Jenkins service
sudo systemctl enable jenkins
sudo systemctl start jenkins



# Install Docker
sudo yum install docker -y

# Wait for Jenkins to initialize (optional: adjust the sleep time if necessary)
echo systemctl enable docker
sudo systemctl start docker

# Add the Jenkins user to the Docker group for Docker CLI access
sudo usermod -aG docker jenkins

# Install git as well
sudo yum install git -y

# Wait for Jenkins to initialize
echo "Waiting for Jenkins to start..."
sleep 5

# Install Docker CLI
DOCKER_CLI_VERSION="20.10.25"
sudo wget https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_CLI_VERSION.tgz
sudo tar xzvf docker-$DOCKER_CLI_VERSION.tgz --strip 1 -C /usr/local/bin docker/docker
sudo rm docker-$DOCKER_CLI_VERSION.tgz

# Download Jenkins CLI jar
JENKINS_URL="http://localhost:8080"
JENKINS_CLI_JAR="/usr/local/bin/jenkins-cli.jar"
sudo wget -O $JENKINS_CLI_JAR $JENKINS_URL/jnlpJars/jenkins-cli.jar


# Verify installations
echo "Java version:"
java -version
echo "Jenkins status:"
sudo systemctl status jenkins
echo "Docker version:"
docker --version
echo "Jenkins CLI installed at $JENKINS_CLI_JAR"

# Reminder to open port 8080 in the EC2 Security Group
echo "Ensure port 8080 is open in your EC2 Security Group for Jenkins access."

# Reminder to retrieve the Jenkins admin password
echo "To retrieve the Jenkins admin password, use:"
echo "sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
"Waiting for Jenkins to start..."
"""

dockerfile_example = """
        FROM python:3.12.7-slim

        # Set the working directory in the container
        WORKDIR /src

        # Copy the /example directory contents into the container at /src
        COPY /example /src

        # Install any needed packages specified in requirements.txt
        RUN pip install --no-cache-dir -r requirements.txt

        # Make port 8501 available to the world outside this container
        EXPOSE 8501

        # Define entrypoint for the container
        CMD ["streamlit", "run", "homepage.py", "--server.port=8501", "--server.address=0.0.0.0"]
        """

terraform_example = """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = "us-east-1"
}

resource "aws_key_pair" "yc-autoanchordemo1" {
  key_name   = "yc-autoanchordemo1"
  public_key = "ssh-ed25519 AAAAS4NzvC0lZDI1NTE7ABCVIKfOsAbG7S3+yJLOIioq1Z03A+B+k9j90q9k5uRyrklp xyz@gmail.com"
}

resource "aws_instance" "jenkins" {
  ami                         = "ami-05e411cf591b5c9f6"
  instance_type               = "t2.micro"
  key_name                    = aws_key_pair.yc-autoanchordemo1.key_name
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.jenkins-sg-yc-autoanchordemo1.id]
  user_data                   = file("jenkins-install.sh")


  tags = {
    Name = "Jenkins-yc-autoanchordemo1"
  }
}


#Jenkins Security Group Resource
resource "aws_security_group" "jenkins-sg-yc-autoanchordemo1" {
  name        = "jenkins-sg-yc-autoanchordemo1"
  description = "Allow Port 22, 8080 and 8501"
  vpc_id = "vpc-08d33290f169c4dc3"

  ingress {
    description = "Allow SSH Traffic"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS Traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow 8080 Traffic"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow 8501 Traffic"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
""" 

jenkinsfile_example = """pipeline {
    agent any

    environment {
        IMAGE_NAME = "<<app name>>"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                git credentialsId: 'new', branch: 'main', url: <<github url>>
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    dockerImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
                }
            }
        }

        stage('Run Docker Container') {
            steps {
                script {
                    sh '''
                    docker run -d -p <<port to expose>> ${IMAGE_NAME}:${IMAGE_TAG}
                    '''
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline completed"
        }
    }
}
"""

xml_creds = """<?xml version='1.0' encoding='UTF-8'?>
<com.cloudbees.plugins.credentials.SystemCredentialsProvider plugin="credentials@1405.vb_cda_74a_f8974">
  <domainCredentialsMap class="hudson.util.CopyOnWriteMap$Hash">
    <entry>
      <com.cloudbees.plugins.credentials.domains.Domain>
        <specifications />
      </com.cloudbees.plugins.credentials.domains.Domain>
      <java.util.concurrent.CopyOnWriteArrayList>
        <com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey plugin="ssh-credentials@349.vb_8b_6b_9709f5b_">
          <scope>GLOBAL</scope>
          <id>new</id>
          <description />
          <username>git</username>
          <usernameSecret>false</usernameSecret>
          <privateKeySource class="com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey$DirectEntryPrivateKeySource">
<privateKey>-----BEGIN OPENSSH PRIVATE KEY-----

Will Be Updated Dynamically in EC2 using Mustard Encryption

-----END OPENSSH PRIVATE KEY-----</privateKey>
          </privateKeySource>
        </com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey>
      </java.util.concurrent.CopyOnWriteArrayList>
    </entry>
  </domainCredentialsMap>
</com.cloudbees.plugins.credentials.SystemCredentialsProvider>
"""

xml_job = """<?xml version='1.0' encoding='UTF-8'?>
<flow-definition plugin="workflow-job@1498.v33a_0c6f3a_4b_4">
  <actions />
  <description />
  <keepDependencies>false</keepDependencies>
  <properties>
    <com.dabsquared.gitlabjenkins.connection.GitLabConnectionProperty plugin="gitlab-plugin@1.9.7">
      <gitLabConnection />
      <jobCredentialId />
      <useAlternativeCredential>false</useAlternativeCredential>
    </com.dabsquared.gitlabjenkins.connection.GitLabConnectionProperty>
    <com.sonyericsson.rebuild.RebuildSettings plugin="rebuild@332.va_1ee476d8f6d">
      <autoRebuild>false</autoRebuild>
      <rebuildDisabled>false</rebuildDisabled>
    </com.sonyericsson.rebuild.RebuildSettings>
    <hudson.plugins.throttleconcurrents.ThrottleJobProperty plugin="throttle-concurrents@2.16">
      <maxConcurrentPerNode>0</maxConcurrentPerNode>
      <maxConcurrentTotal>0</maxConcurrentTotal>
      <categories class="java.util.concurrent.CopyOnWriteArrayList" />
      <throttleEnabled>false</throttleEnabled>
      <throttleOption>project</throttleOption>
      <limitOneJobWithMatchingParams>false</limitOneJobWithMatchingParams>
      <paramsToUseForLimit />
    </hudson.plugins.throttleconcurrents.ThrottleJobProperty>
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers>
        <com.cloudbees.jenkins.GitHubPushTrigger plugin="github@1.41.0">
          <spec />
        </com.cloudbees.jenkins.GitHubPushTrigger>
      </triggers>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps@4014.vcd7dc51d8b_30">
    <scm class="hudson.plugins.git.GitSCM" plugin="git@5.7.0">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>git@github.com:ajayanilkumar/Auto-Anchor-Website.git</url>
          <credentialsId>new</credentialsId>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>main</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list" />
      <extensions />
    </scm>
    <scriptPath>Jenkinsfile</scriptPath>
    <lightweight>true</lightweight>
  </definition>
  <triggers />
  <disabled>false</disabled>
</flow-definition>
"""

script_local=r"""#!/bin/bash

IP="18.234.201.41"
ssh-keyscan -H $IP >> ~/.ssh/known_hosts

scp -i ~/.ssh/id_ed25519 "{work_dir}/shell_files/credentials.xml" ec2-user@$IP:/tmp
scp -i ~/.ssh/id_ed25519 "{work_dir}/shell_files/streamlit-deploy-job.xml" ec2-user@$IP:/tmp
scp -i ~/.ssh/id_ed25519 "{work_dir_parallel}/{ENCRYPTED_KEYS_PATH}" ec2-user@$IP:~/.ssh/
scp -i ~/.ssh/id_ed25519 "{work_dir_parallel}/e2e/decrypt_in_ec2.py" ec2-user@$IP:/tmp
scp -i ~/.ssh/id_ed25519 "{work_dir_parallel}/e2e/update_credentials_job.py" ec2-user@$IP:/tmp/


# SSH into the EC2 instance
ssh -o StrictHostKeyChecking=no ec2-user@$IP << 'EOF'


  # Start decryption script setup
  # Update system packages
  sudo yum update -y

  # Install Python 3 and pip
  sudo yum install -y python3 python3-pip

  # Create a virtual environment
  python3 -m venv decrypt_env
  source decrypt_env/bin/activate

  # Install required dependencies
  pip install cryptography

  # Create a specific directory for decryption
  sudo mkdir -p /opt/decrypt
  sudo cp ~/.ssh/encrypted_keys.json /opt/decrypt/
  sudo cp /tmp/decrypt_in_ec2.py /opt/decrypt/

  # Run the decryption script
  cd /opt/decrypt
  python3 decrypt_in_ec2.py /opt/decrypt/encrypted_keys.json

  # Continue with original script

  sudo mv /tmp/credentials.xml /var/lib/jenkins/
  echo "credentials.xml file created successfully."

  sudo mv /tmp/streamlit-deploy-job.xml /var/lib/jenkins/ 
  
  cd /tmp

  # # Run the Python script to update credentials.xml with the SSH key
  # sudo python3 /tmp/update_credentials_job.py "/var/lib/jenkins/credentials.xml"

  sudo python3 update_credentials_job.py /var/lib/jenkins/credentials.xml --ssh_key_path ~/.ssh/

  # Optional: Deactivate virtual environment
  deactivate


  # Change shell for jenkins user
  sudo usermod -s /bin/bash jenkins

  # Switch to jenkins user
  sudo su - jenkins

  # Create and setup SSH keys
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  cd ~/.ssh

  # Create SSH key file (make sure to replace 'id_ed25519' with the actual key content)

  sudo chmod 600 ~/.ssh/id_ed25519

  # Add GitHub to known hosts
  ssh-keyscan github.com >> ~/.ssh/known_hosts

  # Test SSH connection to GitHub
  ssh -T git@github.com


  # Exit back to the original user
  exit
EOF

ssh -o StrictHostKeyChecking=no ec2-user@$IP << 'EOF'

  cd /var/lib/jenkins


  java -jar /usr/local/bin/jenkins-cli.jar -s http://localhost:8080/ -auth admin:$(sudo cat /var/lib/jenkins/secrets/initialAdminPassword) install-plugin \
  dashboard-view \
  cloudbees-folder \
  configuration-as-code \
  antisamy-markup-formatter \
  build-name-setter \
  build-timeout \
  config-file-provider \
  credentials-binding \
  embeddable-build-status \
  rebuild \
  ssh-agent \
  throttle-concurrents \
  timestamper \
  ws-cleanup \
  ant \
  gradle \
  msbuild \
  nodejs \
  cobertura \
  htmlpublisher \
  junit \
  warnings-ng \
  xunit \
  workflow-aggregator \
  github-branch-source \
  pipeline-github-lib \
  pipeline-stage-view \
  conditional-buildstep \
  parameterized-trigger \
  copyartifact \
  bitbucket \
  clearcase \
  cvs \
  git \
  git-parameter \
  github \
  github-branch-source \
  gitlab-plugin \
  p4 \
  repo \
  subversion \
  matrix-project \
  ssh-slaves \
  matrix-auth \
  pam-auth \
  ldap \
  role-strategy \
  active-directory \
  email-ext \
  emailext-template \
  mailer \
  locale \
  localization-zh-cn \
  dashboard-view \
  cloudbees-folder \
  docker-commons \
  docker-workflow \
  docker-plugin \
  pipeline-utility-steps

EOF

ssh -o StrictHostKeyChecking=no ec2-user@$IP << 'EOF'

  echo "Running Jenkins Job Setup Setup commands"

  sudo systemctl restart jenkins

  cd /var/lib/jenkins

  java -jar /usr/local/bin/jenkins-cli.jar -s http://localhost:8080/ -auth admin:$(sudo cat /var/lib/jenkins/secrets/initialAdminPassword) create-job streamlit-deploy-job < streamlit-deploy-job.xml
  echo "Pipeline Job created successfully."

  # Ensure the file has the correct permissions
  sudo chmod 600 credentials.xml
  sudo chown jenkins:jenkins /var/lib/jenkins/credentials.xml
  sudo usermod -s /bin/false jenkins

  # Notify the user that the script has completed
  echo "Deployment script has completed successfully."

EOF

echo "Finished Setting up instance+jenkins+credentials+pipeline"

echo "Now you push changes to your GitHub!"

"""