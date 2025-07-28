# Auto Anchor - The New Era of Agentic DevOps 

> 📢 **Note**: This project is part of an upcoming demo paper currently in preparation.  
> A formal citation will be provided upon submission or preprint release.  
> In the meantime, feel free to explore, use, and provide feedback.

© 2025 Mitul Garg and Ajay Anil Kumar  
Licensed under the [MIT License](./LICENSE).


Struggling with limited online DevOps documentation? Too many manual setup configuration issues? Hours of Research and not knowing the right way to setup your CI/CD pipeline?

What typically takes hours (or even days) for a DevOps engineer, Auto Anchor does in just 5 minutes. End to End.

No prior DevOps knowledge required. No cloud infra expertise needed. Just code, talk to aCube (Auto Anchor Agent), and you’re live! Pushing your code to production has never been this seamless!

Youtube End-end demo -  
[Watch the End-to-End Demo on YouTube](https://www.youtube.com/watch?v=szbxx4Ujl_w)

Key Features:

🔁 Automatic CI/CD Pipeline Setup
Sets up and configures your entire pipeline from scratch - fast and reliably.
Generates 'smart context' and other artefacts based on your application and through aCube that help generate all required DevOps scripts.

🧠 Conversational Interface with aCube
Talk to aCube in plain English to get your code deployed. No YAMLs, no docs, no hassle.

🛡️ Local-First & Secure
Keeps your code on your machine. Picks up your repository and automatically configures your GitHub webhooks with the infrastructure that Auto Anchor spins up for you while managing end-to-end encryption of your credentials.

☁️ Cloud-Ready
Seamlessly sets up AWS infrastructure components along with critical setups within the infrastructure.  

Start building. Stop configuring.
Let Auto Anchor handle the DevOps so you can focus on code.

Current version supports deploying python applications on AWS.


## Pre-Requisites

```bash
pip install -r requirements.txt
```

You need to have a Mac system to be able to run this application.

Steps:

1. Create a .ssh file in your root (~/) folder and update your public and private ed25519 keys if you haven't already.
2. Install AWS CLI. 
3. Create an AWS account. If you have one already then copy your AWS access keys and paste them into the CLI prompts while configuring AWS CLI.
4. Install GitHub CLI and sign in into your account. Select SSH while logging in.
5. Install Terraform.
6. Gemini and OpenAI API Keys

## High level understanding of the Application

![](https://github.com/Auto-Anchor/Auto-Anchor/blob/main/images/Auto-Anchor-HLD.png)

### Frontend React Application 

The frontend application is in the folder `frontend`. 


**Initial Setup**

1) Click on the settings icon on the top right corner of the home page.
2) You will see that you need to update your SSH credentials here.
3) Copy and paste both your ssh public and private key here. This gets stored locally and is only used while setting up the CI/CD pipeline within the cloud infrastructure using our secure 'Mustard Encryption Algorithm'. More about that below.
4) Return to the Home Page. Your keys are now saved for future use.

### aCube 

aCube - short for "Auto Anchor Agent" - is our middle layer LLM orchestrator powered by Google Agent Development Kit (ADK). It has access to various Tools that help in the deployment of your application. 

Create a `.env` file inside `aCube/src`:
```env
GOOGLE_GENAI_USE_VERTEXAI="FALSE"
GOOGLE_API_KEY="<YOUR KEY>"
```

Once you run the above commands - aCube is exposed on `localhost:9999`.

aCube is designed to be user friendly and very interactive. If you are unsure about something related to your deployment - aCube is here to help you! It assumes you have no/very-less prior experience.

Your job is to help aCube understand a few things about your application through a short QnA process during which multiple tools are called to generate artefacts/scripts specific to your application.

It is currently powered by `gemini 2.5 flash`.

![](https://github.com/Auto-Anchor/Auto-Anchor/blob/main/images/aCube-Tools.png)

aCube currently has access to 6 tools which are exposed as FastAPI endpoints in our backend. It can call any set of tools sequentially/in-parallel based on the user's requirement. More about the tools in the next section. We plan to expand the capabilities of aCube with more tools in the Future, especially with MCP, we encourage contributions to Auto Anchor for the community!

### FastAPI Backend - Tools and Logic

Each of our tools are exposed as FastAPI endpoints. To get it started:

Create a `.env` file inside `backend`:
```env
OPENAI_API_KEY=""
```

#### Analyzer

The main function of this tool is analyze your code repo locally and return:
- The **type of python** application: Streamlit/Flask/Django etc.
- The main **working directory/folder** in your repo.
- The **entrypoint** file to run your application.

Analyzer creates the `requirements.txt` file for your repo based on the python environment that you provide!

All of this is done without the help of LLM's and all of your code stays secure and on the local machine.

#### Dockerfile and Jenkinsfile Generator

An LLM with a one shot example is used to generate a simple Dockerfile and a Jenkinsfile. These tools take in context from the output of the `Analyzer` tool.

#### Infra Setup

This is an insanely powerful tool with a lot going on under the hood... 

1. `Terraform` files are generated to spin up a new EC2 instance.
2. `Shell scripts` are used to install required dependencies.
3. `XML Files` are generated for Jenkins which help add the credentials and create a new job.

As step 3 involves creation of XML files including your public and private SSH keys - it is something that requires good security. Fear not, as we have a strong encryption algorithm - **Mustard Encryption!**

How Mustard Encryption Works:
Mustard Encryption is a custom two-layer end-to-end encryption system that ensures your credentials stay safe and private:

🔑 Random key generation + salt for every encryption session

🔒 Double-encryption: one key encrypts your data, while a second encrypted key protects the first

💾 Hashed local storage: even locally stored credentials are hashed before saving to your machine

Your credentials are dynamically populated within Jenkins and Git inside the EC2 instance 

We take privacy seriously — no data is ever transmitted unless explicitly required, and your credentials never leave your local environment unprotected.

Note: Mustard Encryption is designed with strong privacy principles, it is not yet independently audited. Use with caution for production-grade secrets.


#### GitHub WebHook Setup

Once the instance is up and running and all the shell scripts have run - A GitHub webhook is setup with the public IP of the newly launched instance.

Once this is complete - the user can make a code push to the remote repo on GitHub to start the CI/CD process.

#### Get Instance IP

This is a utility function that helps the user get the exact IP - where he can see his newly deployed application.

You are now ready to meet aCube! Start interacting with our chatbot and see what it can do!

![](https://github.com/Auto-Anchor/Auto-Anchor/blob/main/images/aCube-Chat.png)

## Starting the application

To start the application execute the `execute.sh` shell script:

```bash
chmod +x execute.sh
./execute.sh
```

## Future Work

Auto Anchor is still in its early stages, and we've completely open-sourced it to grow with the community's help. We're excited to invite developers, DevOps engineers, and curious tinkerers to join us in shaping the future of agentic DevOps.

We welcome:

🐛 Bug Reports — Help us identify and squash issues.

💬 Feedback — Share your experience and suggestions for improvements.

🤝 Contributions — Help us make Auto Anchor more robust, scalable, and packed with even more DevOps features.

Let’s work together to take Auto Anchor to the next level - with broader customizability, improved cloud support, and an even smoother developer experience.
