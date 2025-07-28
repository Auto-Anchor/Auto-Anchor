from fastapi import FastAPI, HTTPException, Request
from utils import * # Assuming this and other custom imports are in your project structure
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from run_initial import main as run_initial_main
# from run_initial import RunInitialMain # This import was not used, commented out
from pydantic import BaseModel, Field
# from acube.acube_orchestrator import *
# from acube.validator import *
from githubwebhook import *
# from importlib import import_module # This import was not used, commented out
from dotenv import load_dotenv
from typing import Type
import json
import base64
import os
from constants import *
import logging # Import the logging module
import logging.handlers # For rotating file handler
import time # For timing requests in middleware
import uuid # For unique request IDs in middleware

# --- Logger Configuration ---
LOG_FILE = "app.log"

def setup_logging():
    logger = logging.getLogger("api_logger") # Create a logger instance
    logger.setLevel(logging.DEBUG) # Set the minimum logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(thread)d - %(filename)s:%(lineno)d - %(message)s')

    # Console Handler (for output to stdout)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO) # Log INFO and above to console
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler (for output to a file, with rotation)
    # Rotate log file when it reaches 10MB, keep 5 backup files
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    fh.setLevel(logging.DEBUG) # Log DEBUG and above to file
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

logger = setup_logging()
# --- End Logger Configuration ---


load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") # Use .get for safer access
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable not set.")


app = FastAPI()

# --- Middleware for logging requests and responses ---
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(f"rid={request_id} Request started: {request.method} {request.url.path} Client: {request.client.host}")
    # You could log headers too, but be careful with sensitive data
    # logger.debug(f"rid={request_id} Headers: {dict(request.headers)}")
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception(f"rid={request_id} Unhandled exception during request processing for {request.url.path}")
        # Re-raise the exception to let FastAPI's default error handling take over or your custom exception handlers
        raise
    finally:
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}"
        if 'response' in locals(): # check if response variable was assigned
             logger.info(f"rid={request_id} Request finished: {request.method} {request.url.path} Status: {response.status_code} Took: {formatted_process_time}ms")
        else: # an exception occurred before response was created
            logger.error(f"rid={request_id} Request failed: {request.method} {request.url.path} Took: {formatted_process_time}ms (No response generated due to error)")

    return response
# --- End Middleware ---


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class KeyData(BaseModel):
    public_key: str
    private_key: str

@app.post("/api/save-keys")
def save_keys(data: KeyData):
    logger.info("Received request to /api/save-keys")
    try:
        decoded_private_key = base64.b64decode(data.private_key.encode()).decode()
        decoded_private_key = clean_key(decoded_private_key) # Assuming clean_key is defined in utils
        credentials_store = CredentialsLocalStorage()
        credentials_store.save_encrypted_keys(data.public_key, decoded_private_key)
        logger.info("Keys saved securely to file.")
        

        logger.debug(f"Attempting to read Terraform version path: {TERRAFORM_VERSION_PATH}")
        with open(TERRAFORM_VERSION_PATH, "r") as f:
            read = json.load(f)

        if "public_key" in read:
            read["public_key"] = data.public_key
            logger.debug(f"Updated public key in Terraform config.")
        else:
            logger.warning(f"'public key' not found")


        
        with open(TERRAFORM_VERSION_PATH, "w") as f:
            json.dump(read, f, indent=4)

        return {"message": "Keys saved securely to file."}

    except Exception as e:
        logger.exception("Error in /api/save-keys")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get-keys")
def get_keys():
    logger.info("Received request to /api/get-keys")
    try:
        credentials_store = CredentialsLocalStorage()
        keys = credentials_store.load_decrypted_keys()

        # Re-encode private key to base64 for transport
        keys["private_key"] = base64.b64encode(keys["private_key"].encode()).decode()
        logger.info("Keys retrieved successfully.")
        return keys
    except Exception as e:
        logger.exception("Error in /api/get-keys")
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzerRequest(BaseModel):
    folder_path: str = Field(description="The path to analyze.", default=None)
    environment_path: str = Field(description="Python Env's Path", default=None)

# @app.post("/analyzer")
# async def analyzer(data: AnalyzerRequest):
#     logger.info(f"Received request to /analyzer for folder: {data.folder_path}, env: {data.environment_path}")
#     try:
#         folderPath = data.folder_path
#         environment_path = data.environment_path
#         req = RequirementsGen()
#         py_files = req.get_files_in_dir(folderPath, ".py")
#         logger.debug(f"Found {len(py_files)} Python files in {folderPath}")
        
#         list_of_imports = []
#         for py_file in py_files:
#             list_of_imports.extend(req.find_imports(py_file))
#         list_of_imports = list(set(list_of_imports))
#         logger.debug(f"Found {len(list_of_imports)} unique imports.")

#         matching_libraries = req.find_env_libraries(list_of_imports, environment_path)
#         logger.debug(f"Found {len(matching_libraries)} matching libraries in environment.")
        
#         req.generate_req_file(folderPath, matching_libraries)
#         logger.info(f"Generated requirements file in {folderPath}")

#         context = ContextGenerator()
#         app_type = context.app_type()
#         work_dir, entrypoint = context.working_dir_and_entrypoint(folderPath)
#         logger.info(f"Analysis complete: app_type={app_type}, work_dir={work_dir}, entrypoint={entrypoint}")

#         return {
#             "success": True,
#             "app_type": app_type,
#             "environment_path": environment_path,
#             "work_dir": work_dir,
#             "entrypoint": entrypoint
#         }
#     except Exception as e:
#         logger.exception(f"Error in /analyzer for folder: {data.folder_path}")
#         raise HTTPException(status_code=500, detail=f"Analyzer error: {str(e)}")


@app.post("/analyzer")
async def analyzer(data: AnalyzerRequest):
    logger.info(f"Received request to /analyzer for folder: {data.folder_path}, env: {data.environment_path}")
    try:
        folderPath = data.folder_path
        environment_path = data.environment_path
        
        # --- Requirements generation (no changes needed here) ---
        req = RequirementsGen()
        py_files = req.get_files_in_dir(folderPath, ".py")
        logger.debug(f"Found {len(py_files)} Python files in {folderPath}")
        list_of_imports = []
        for py_file in py_files:
            list_of_imports.extend(req.find_imports(py_file))
        list_of_imports = list(set(list_of_imports))
        logger.debug(f"Found {len(list_of_imports)} unique imports.")
        matching_libraries = req.find_env_libraries(list_of_imports, environment_path)
        logger.debug(f"Found {len(matching_libraries)} matching libraries in environment.")
        req.generate_req_file(folderPath, matching_libraries)
        logger.info(f"Generated requirements file in {folderPath}")

        # --- Use the new, generalized context analysis ---
        context = ContextGenerator()
        analysis_result = context.analyze_project(folderPath)
        
        logger.info(f"Analysis complete: {analysis_result}")

        return {
            "success": True,
            "app_type": analysis_result["app_type"],
            "environment_path": environment_path,
            "work_dir": analysis_result["work_dir"],
            "entrypoint": analysis_result["entrypoint"]
        }
    except Exception as e:
        logger.exception(f"Error in /analyzer for folder: {data.folder_path}")
        raise HTTPException(status_code=500, detail=f"Analyzer error: {str(e)}")
    

@app.get("/creds")
async def get_creds():
    logger.info("Received request to /creds")
    try:
        checker = AWSCLI() # Assuming AWSCLI is defined in utils
        aws_key_pairs = checker.list_keypairs()
        aws_region = checker.check_region()
        aws_vpc = checker.check_vpc()
        aws_subnets = checker.check_subnets()
        aws_sg = checker.check_security_groups()
        logger.info("AWS credentials information retrieved successfully.")
        return {"success": True,
                "aws_key_pairs": aws_key_pairs,
                "aws_region": aws_region,
                "aws_vpc": aws_vpc,
                "aws_subnets": aws_subnets,
                "aws_sg": aws_sg
                }
    except Exception as e:
        logger.exception("Error in /creds")
        raise HTTPException(status_code=500, detail=f"Error getting AWS creds: {str(e)}")

@app.get("/dockerfile-gen")
async def filegen_dockerfile(app_type: str, python_version: str, work_dir: str, entrypoint: str, folder_path: str):
    logger.info(f"Request to /dockerfile-gen: app_type={app_type}, py_version={python_version}, work_dir={work_dir}, entrypoint={entrypoint}, folder={folder_path}")
    try:
        docker = DockerfileGen(
            python_version=python_version,
            end_dir=work_dir,
            app_type=app_type,
            entry_point=entrypoint
        )
        docker.generate(folder_path)
        logger.info(f"Dockerfile generated successfully in {folder_path}")
        return {"success": True}
    except Exception as e:
        logger.exception(f"Error in /dockerfile-gen for folder: {folder_path}")
        raise HTTPException(status_code=500, detail=f"Dockerfile generation error: {str(e)}")


@app.get("/jenkinsfile-gen")
async def filegen_jenkinsfile(folder_path: str, app_name: str, port: str):
    logger.info(f"Request to /jenkinsfile-gen for folder: {folder_path}")
    try:
        git = GithubSCM() # Assuming GithubSCM is defined in utils
        github_url = git.github_repo_url(folder_path)
        logger.debug(f"Determined GitHub URL: {github_url}")
        jenkins = JenkinsfileGen(app_name=app_name, # Consider making app_name dynamic
                                github_url=github_url,
                                port=port, # Consider making port dynamic
                                version="v1")
        jenkins.generate(folder_path)
        logger.info(f"Jenkinsfile generated successfully in {folder_path}")
        return {"success": True}
    except Exception as e:
        logger.exception(f"Error in /jenkinsfile-gen for folder: {folder_path}")
        raise HTTPException(status_code=500, detail=f"Jenkinsfile generation error: {str(e)}")


@app.get("/infra")
async def infra(work_dir:str, instance_size:str):
    logger.info(f"Request to /infra: work_dir={work_dir}, instance_size={instance_size}")
    try:
        logger.debug(f"Attempting to read Terraform version path: {TERRAFORM_VERSION_PATH}")
        with open(TERRAFORM_VERSION_PATH, "r") as f:
            data = json.load(f)
        
        if "instance_type" in data:
            data["instance_type"] = instance_size
            logger.debug(f"Updated instance_type to {instance_size} in Terraform config.")
        else:
            logger.warning(f"'instance_type' not found in {TERRAFORM_VERSION_PATH}, creating it.")
            data["instance_type"] = instance_size


        try:
            credentials_store = CredentialsLocalStorage()
            keys = credentials_store.load_decrypted_keys()
            logger.debug("Decrypted keys loaded for infra setup.")
        except RuntimeError as e:
            logger.error(f"RuntimeError loading decrypted keys: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        ssh_private_key = keys["private_key"] # Be careful not to log this value
        ssh_public_key = keys["public_key"]
        logger.debug("SSH keys retrieved for credentials upload.")


        # if "public_key" in data:
        #     data["public_key"] = ssh_public_key
        #     logger.debug(f"Updated public key in Terraform config.")
        # else:
        #     logger.warning(f"'public key' not found")


        
        with open(TERRAFORM_VERSION_PATH, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Terraform version config updated at {TERRAFORM_VERSION_PATH}")

        terraform = TerraformGen()
        terraform.generate(work_dir)
        logger.info(f"Terraform files generated in {work_dir}")

        job = JenkinsJobXml()
        job.generate_job_xml(work_dir)
        logger.info(f"Jenkins job XML generated in {work_dir}")



        hashing = CredentialsUpload(ssh_private_key, ssh_public_key)
        hashing.save_encrypted_data()
        logger.info("Encrypted credentials data saved.")


        cred = JenkinsCredentialsXml()
        cred.generate_credentials_xml(work_dir)
        logger.info(f"Jenkins credentials XML generated in {work_dir}")
        cred.generate_script_local_shell(work_dir)
        logger.info(f"Local shell script for Jenkins credentials generated in {work_dir}")
        
        logger.info(f"Running initial setup using Terraform for work_dir: {work_dir}...")
        run_initial_main(work_dir) # Assuming this function has its own logging or is safe
        logger.info("Initial Terraform setup completed.")
        return {"success": True}
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e.filename}")
        raise HTTPException(status_code=500, detail=f"Configuration file missing: {e.filename}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {TERRAFORM_VERSION_PATH}: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid configuration file format at {TERRAFORM_VERSION_PATH}")
    except Exception as e:
        logger.exception(f"Error in /infra for work_dir: {work_dir}")
        raise HTTPException(status_code=500, detail=f"Infra setup error: {str(e)}")


@app.get("/get-environments")
async def get_environments(folder_path : str):
    logger.info(f"Request to /get-environments for folder: {folder_path}")
    try:
        context = ContextGenerator()
        python_versions = context.find_python_version(folder_path)
        logger.info(f"Found Python versions: {python_versions} in {folder_path}")
        return {"success": True,
                "python_versions": python_versions}
    except Exception as e:
        logger.exception(f"Error in /get-environments for folder: {folder_path}")
        raise HTTPException(status_code=500, detail=f"Error getting environments: {str(e)}")


@app.get("/github-webhook-setup")
async def github_webhook_setup(folder_path:str):
    logger.info(f"Request to /github-webhook-setup for folder: {folder_path}")
    try:
        webhook_manager = GitHubWebhookManager(folder_path)
        output = webhook_manager.create_webhook()
        logger.info(f"GitHub webhook setup output: {output}")
        return {"success": True, "message": output}
    except Exception as e:
        logger.error(f"Error in /github-webhook-setup for {folder_path}: {e}", exc_info=True) # exc_info=True logs stack trace
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

# "/acube" endpoints have been deprecated since we moved to Google ADK as our orchestration layer

@app.get("/acube/cicdplan")
async def tools_execution_order(user_request: str, service_type: str):
    logger.info(f"Request to /acube/cicdplan: user_request='{user_request[:50]}...', service_type='{service_type}'") # Log truncated request
    try:

        data_to_write = {
            "app_type": "streamlit",
            "python_version": "3.11",
            "work_dir": "/Users/anilrao/Documents/GitHub/Auto-Anchor-Website",
            "entrypoint": "/Users/anilrao/Documents/GitHub/Auto-Anchor-Website/homepage.py"
        }

        with open(ANSWER_VARS_PATH, 'w') as file: # Ensure ANSWER_VARS_PATH is defined in constants.py
            json.dump(data_to_write, file, indent=4)

        logger.debug(f"Cleared {ANSWER_VARS_PATH}")
            
        model = ChatOpenAI(model="gpt-4o-mini", temperature=1.0) # Ensure ChatOpenAI is correctly imported and configured
        tools_instance = Orchestrator(user_request, service_type)
        iam_check = tools_instance.validate_policies(model)
        logger.debug(f"IAM check result: {iam_check}")

        if iam_check.get('has_access') == True: # Use .get for safer dictionary access
            plan = tools_instance.plan()
            reasoning_steps = plan.get('reasoning', [])
            tool_execution_order = plan.get('tools', [])
            logger.info(f"CICD plan generated. Reasoning steps count: {len(reasoning_steps)}, Tools count: {len(tool_execution_order)}")
            return {"Reasoning Steps": reasoning_steps, "Tool Execution Order": tool_execution_order}
        else:
            logger.warning(f"IAM check failed or access denied for user_request='{user_request[:50]}...'")
            return {"Credential Error": True, "IAM_Check_Details": iam_check} # Provide more details if possible
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found for acube/cicdplan: {e.filename}")
        raise HTTPException(status_code=500, detail=f"Configuration file missing: {e.filename}")
    except Exception as e:
        logger.exception(f"Error in /acube/cicdplan for user_request='{user_request[:50]}...'")
        raise HTTPException(status_code=500, detail=f"Error generating CICD plan: {str(e)}")

@app.get("/acube/dynamicquestion")
async def dynamic_question(tool_name: str):
    logger.info(f"Request to /acube/dynamicquestion for tool_name: {tool_name}")
    try:
        with open(TOOL_PATH,"r") as f: # Ensure TOOL_PATH is defined in constants.py
            json_tools=json.load(f)
        logger.debug(f"Loaded tools from {TOOL_PATH}")

        class_name = None
        question = None
        for tool in json_tools.get("tools", []):
            if tool.get("name") == tool_name:
                class_name = tool.get("class")
                question = tool.get("question")
                break
        
        if not class_name:
            logger.warning(f"Tool '{tool_name}' not found in {TOOL_PATH}")
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' configuration not found.")

        ValidatorClass: Type[BaseModel] = globals().get(class_name)
        if not ValidatorClass:
            logger.error(f"Validator class '{class_name}' for tool '{tool_name}' not found in global scope.")
            raise HTTPException(status_code=500, detail=f"Internal server error: Validator class '{class_name}' not found.")

        ValidatorObject = update_answers(ValidatorClass) # Ensure update_answers handles missing ANSWER_VARS_PATH gracefully
        logger.debug(f"ValidatorObject for {tool_name} after update_answers: {ValidatorObject.model_dump_json(indent=2) if ValidatorObject else 'None'}")
        
        all_none = all(value in default_values for value in vars(ValidatorObject).values()) # Ensure default_values is defined
        all_filled = all(value not in default_values for value in vars(ValidatorObject).values())
        logger.debug(f"All fields None for {tool_name}: {all_none}, All fields filled: {all_filled}")

        updated_question = question # Default to original question
        if all_filled:
            updated_question = 'Pass'
            logger.info(f"All fields filled for tool {tool_name}, setting question to 'Pass'.")
        elif not all_none: # Some fields are filled, but not all
            updated_question = llm_updated_question(tool_name, ValidatorObject) # Ensure llm_updated_question is robust
            logger.debug(f"Generated LLM updated question for {tool_name}: '{updated_question}'")
        
        logger.info(f"Dynamic question for tool {tool_name}: '{updated_question}'")
        return {tool_name: updated_question}

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found for acube/dynamicquestion: {e.filename}")
        raise HTTPException(status_code=500, detail=f"Configuration file missing: {e.filename}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {TOOL_PATH}: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid configuration file format at {TOOL_PATH}")
    except Exception as e:
        logger.exception(f"Error in /acube/dynamicquestion for tool_name: {tool_name}")
        raise HTTPException(status_code=500, detail=f"Error generating dynamic question: {str(e)}")


@app.get("/acube/answervalidator")
async def answer_validator(tool_name: str, answer: str):
    logger.info(f"Request to /acube/answervalidator for tool_name: {tool_name}, answer: '{answer[:50]}...'")
    class_name = None
    try:
        with open(TOOL_PATH,"r") as f:
            json_tools=json.load(f)
        logger.debug(f"Loaded tools from {TOOL_PATH} for answer validation.")

        for tool in json_tools.get("tools", []):
            if tool.get("name") == tool_name:
                class_name=tool.get("class")
                break
        
        if not class_name:
            logger.warning(f"Tool '{tool_name}' not found in {TOOL_PATH} for answer validation.")
            return JSONResponse(status_code=404, content={"error": f"Tool '{tool_name}' not found"})


        ValidatorClass: Type[BaseModel] = globals().get(class_name)
        if not ValidatorClass:
            logger.error(f"Validator class '{class_name}' for tool '{tool_name}' not found in global scope (answer validator).")
            return JSONResponse(status_code=500, content={"error": f"Class {class_name} not found"})

        ValidatorObject = update_answers(ValidatorClass)
        logger.debug(f"ValidatorObject for {tool_name} in answer_validator: {ValidatorObject.model_dump_json(indent=2) if ValidatorObject else 'None'}")

        model = ChatOpenAI(model="gpt-4o",temperature=0)
        variables = validator(answer, ValidatorObject, ValidatorClass, model) # Ensure validator is robust
        logger.info(f"Validation result for tool {tool_name}: {variables}")

        # Save validated variables
        current_data = {}
        try:
            if os.path.exists(ANSWER_VARS_PATH): # Check if file exists before reading
                with open(ANSWER_VARS_PATH, 'r') as f:
                    current_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"{ANSWER_VARS_PATH} contained invalid JSON. Initializing with empty data.")
        except FileNotFoundError:
             logger.info(f"{ANSWER_VARS_PATH} not found. Initializing with empty data.")
        
        # Update current_data with new variables, prioritizing new ones if keys conflict (or define your merge strategy)
        if isinstance(variables, dict): # Ensure variables is a dict
            current_data.update(variables)
        else:
            logger.warning(f"Validator for {tool_name} returned non-dict: {variables}. Not updating ANSWER_VARS_PATH with this result.")


        with open(ANSWER_VARS_PATH, 'w') as f:
            json.dump(current_data, f, indent=4)
        logger.debug(f"Updated {ANSWER_VARS_PATH} with validated variables for {tool_name}.")

        return {"variables": variables}

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found for acube/answervalidator: {e.filename}")
        raise HTTPException(status_code=500, detail=f"Configuration file missing: {e.filename}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON (likely from {TOOL_PATH} or {ANSWER_VARS_PATH}): {e}")
        raise HTTPException(status_code=500, detail=f"Invalid configuration file format: {e}")
    except Exception as e:
        logger.exception(f"Error in /acube/answervalidator for tool_name: {tool_name}")
        # The original code had a feedback loop here, decide if you want to keep it or raise HTTP 500
        # For now, let's make it consistent with other error handling
        # feedback = feedback_loop_question_v2(ValidatorObject, str(variables), model)
        # return {"retry_exception": feedback}
        raise HTTPException(status_code=500, detail=f"Error validating answer: {str(e)}")
    
@app.get("/dashboard-file-data")
async def answer_validator():

    with open("configs/answer_vars.json") as f:
        data = json.load(f)
    
    folder_path = data.get('folder_path', "")

    print(folder_path)

    list_of_files=['Dockerfile',
                   'Jenkinsfile',
                   'requirements.txt',
                   'terraform_files/main.tf',
                   'shell_files/streamlit-deploy-job.xml',
                   'shell_files/script-local.sh',
                   ]
    
    new_files = []

    for file in list_of_files:
        file = os.path.join(folder_path, file)
        if os.path.exists(file):
            new_files.append(file)


    file_read = ReadAndUpdateGenerations()
    return file_read.read_files(new_files)


class FileEditRequest(BaseModel):
    filename: str
    original_code: str
    prompt: str

@app.post("/edit-file")
async def edit_file(data: FileEditRequest):
    editor = ReadAndUpdateGenerations()
    
    result = editor.edit_file_with_prompt(
        filename=data.filename,   
        original_code=data.original_code,
        prompt=data.prompt
    )
    print(result)
    update_status="test"

    with open("configs/answer_vars.json") as f:
        data = json.load(f)
    
    folder_path = data.get('folder_path', "")

    update_status = editor.write_updated_code_to_file(
        original_filepath = os.path.join(folder_path,result["filename"]), #WORKDIR+filename
        updated_code = result["updated_code"]
    )

    return update_status

@app.get("/get-instance-ip")
async def get_instance_ip_endpoint(work_dir: str):
    logger.info(f"Received request to get instance IP from: {work_dir}")
    try:
        runner = RunInitialMain(work_dir)
        ip = runner.get_instance_ip()
        return {"success": True, "public_ip": ip}
    except Exception as e:
        logger.exception("Failed to retrieve instance IP")
        raise HTTPException(status_code=500, detail=str(e))


# --- Add a simple startup and shutdown event logging ---
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup complete.")
    logger.info(f"OpenAPI schema available at /docs or /redoc")
    if not OPENAI_API_KEY: # Log again at startup if still not found
        logger.critical("CRITICAL: OPENAI_API_KEY is not configured. LLM features will likely fail.")
    logger.info(f"Logging to console and file: {LOG_FILE}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated.")
    # Perform any cleanup here if necessary
    logging.shutdown() # Flushes and closes all handlers

# To run this (example using uvicorn):
# uvicorn your_file_name:app --reload

