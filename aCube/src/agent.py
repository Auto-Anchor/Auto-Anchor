# auto_anchor/agent.py

from google.adk.agents import Agent
from google.genai import types
from dotenv import load_dotenv
BASE_URL='http://127.0.0.1:8084'
load_dotenv()

import requests
import json
from typing import Dict, Any, Optional

# Define the custom exception class if it's not already defined elsewhere
class APIClientError(Exception):
    """Custom exception for API client errors."""
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

def handle_api_response(response: requests.Response) -> Dict[str, Any]:
    """
    Handles the response from the API, expecting a 'status':'success'/'error' convention.

    If 'status' is 'error', expects 'error_message' for details.
    If 'status' is 'success', returns the full JSON data.
    Raises APIClientError for HTTP errors or if the JSON response indicates an application-level error.
    """
    try:
        # First, check for HTTP-level errors (4xx or 5xx).
        # This will raise requests.exceptions.HTTPError if the status code is an error.
        response.raise_for_status()

        # If no HTTP error, then we expect a JSON response for 2xx status codes.
        try:
            data = response.json()
        except json.JSONDecodeError as json_err:
            # HTTP status was 2xx, but response body is not valid JSON.
            raise APIClientError(
                f"Failed to decode JSON response from successful HTTP call: {response.text}",
                status_code=response.status_code
            ) from json_err

        # We have valid JSON and a 2xx HTTP status.
        # Now, check the application-level 'status' field.
        if isinstance(data, dict):
            api_status = data.get("status")

            if api_status == "error":
                error_message = data.get("error_message", "Unknown API error: 'status' is 'error' but 'error_message' is missing.")
                raise APIClientError(error_message, status_code=response.status_code, response_data=data)
            elif api_status == "success":
                # Valid success response as per the new format.
                # The calling function will be responsible for extracting specific fields
                # (e.g., the content of a "report" key, as in your example).
                return data
            elif api_status is None:
                # 'status' field is missing. This could be an API endpoint that doesn't (yet)
                # use the new status convention or implies success on 2xx.
                # We'll check for an explicit "error_message" just in case.
                # Also, we can check for the old {"success": False} pattern for backward compatibility if needed.
                if "error_message" in data:
                    # If "error_message" is present even without status="error", treat it as an error.
                    raise APIClientError(data["error_message"], status_code=response.status_code, response_data=data)
                
                # Optional: Check for old {"success": False} pattern if you need to support mixed APIs
                # if data.get("success") is False:
                #     old_error_message = data.get("error", data.get("message", "Unknown API error with success=False"))
                #     raise APIClientError(old_error_message, status_code=response.status_code, response_data=data)

                # If no explicit error indicators ('status':'error', 'error_message', or old 'success':False),
                # and HTTP status was 2xx, assume it's a valid successful response.
                return data
            else:
                # 'status' field is present but has an unexpected value (e.g., "pending", "in_progress").
                raise APIClientError(
                    f"API response has an unexpected 'status' field value: '{api_status}'",
                    status_code=response.status_code,
                    response_data=data
                )
        else:
            # Response JSON is not a dictionary (e.g., a list or a string directly).
            # With a 2xx status, this is considered successful data.
            return data

    except requests.exceptions.HTTPError as http_err:
        # This block handles 4xx or 5xx HTTP errors.
        # Try to parse JSON from the error response body for a more specific message.
        try:
            err_data = response.json()
            if isinstance(err_data, dict):
                # Prefer the new "error_message" if the API provides it for HTTP errors
                message = err_data.get("error_message")
                if message is None:
                    # Fallback to FastAPI's "detail" or other common fields
                    message = err_data.get("detail")
                    # Handle FastAPI's validation error format if 'detail' is a list of errors
                    if isinstance(message, list) and len(message) > 0 and \
                       isinstance(message[0], dict) and 'loc' in message[0] and 'msg' in message[0]:
                        # Format FastAPI validation errors into a readable string
                        message = "; ".join([f"{err.get('loc', ['unknown_field'])[-1]}: {err.get('msg', '')}" for err in message])
                
                if message is None: # If still no specific message from known fields
                    message = str(err_data) # Use the string representation of the error data dict
                
            else: # Error response JSON was not a dict (e.g. a list or string)
                message = str(err_data) # Use its string representation
        except json.JSONDecodeError:
            # Error response body was not JSON. Use the raw response text.
            message = f"HTTP error: {response.text}" if response.text else str(http_err)
        
        raise APIClientError(message, status_code=response.status_code, response_data=getattr(http_err, 'response', {})) from http_err

    except requests.exceptions.RequestException as req_err:
        # Handles network errors, DNS failures, timeouts, etc.
        raise APIClientError(f"Request exception: {req_err}") from req_err
    
# --- Client Functions ---

def save_keys(public_key: str, private_key: str) -> Dict[str, Any]:
    """
    Saves public and private keys to the server. The private key must be base64 encoded.

    Args:
        public_key (str): The public SSH key.
        private_key (str): The base64 encoded private SSH key.

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "Keys saved securely to file."}`
              Example error: `{"success": False, "error": "Error details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/api/save-keys"
    payload = {"public_key": public_key, "private_key": private_key}
    response = requests.post(endpoint, json=payload)
    return handle_api_response(response)

def get_keys() -> Dict[str, Any]:
    """
    Retrieves the saved public and private keys from the server.
    The returned private key will be base64 encoded.

    Returns:
        dict: API response.
              Example success: `{"success": True, "keys": {"public_key": "...", "private_key": "base64encodedkey"}}`
              Example error: `{"success": False, "error": "Error details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/api/get-keys"
    response = requests.get(endpoint)
    return handle_api_response(response)

def analyzer(folder_path: str, environment_path: str) -> Dict[str, Any]:
    """
    Analyzes Python files in a specified directory to identify dependencies,
    generate a requirements file, and extract contextual information like
    app type, working directory, and entry point.

    Args:
        folder_path [str]: The path to the folder to analyze.
                                     Server-side logic might require this.
        environment_path [str]: Path to the Python environment
                                          to help resolve dependencies.

    Returns:
        dict: API response.
              Example success: `{"success": True, "app_type": "streamlit", "environment_path": "/path/env", "work_dir": "/app", "entrypoint": "run.py"}`
              Example error: `{"success": False, "error": "Analyzer error: folder_path is required."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/analyzer"
    payload = {}
    if folder_path is not None:
        payload["folder_path"] = folder_path
    if environment_path is not None:
        payload["environment_path"] = environment_path

    response = requests.post(endpoint, json=payload)
    return handle_api_response(response)

def get_creds() -> Dict[str, Any]:
    """
    Fetches AWS credentials and configurations like key pairs, regions, VPCs,
    subnets, and security groups that are configured for the server environment.

    Returns:
        dict: API response.
              Example success: `{"success": True, "aws_key_pairs": [...], "aws_region": "us-west-2", ...}`
              Example error: `{"success": False, "error": "Error getting AWS creds: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/creds"
    response = requests.get(endpoint)
    return handle_api_response(response)

def dockerfile_gen(app_type: str, python_version: str, work_dir: str, entrypoint: str, folder_path: str) -> Dict[str, Any]:
    """
    Generates a Dockerfile based on the specified application context data.

    Args:
        app_type (str): Type of the application (e.g., 'streamlit', 'fastapi'). Required.
        python_version (str): Python version to use (e.g., '3.9'). Required.
        work_dir (str): The working directory path inside the Docker container (e.g., '/app'). Required.
        entrypoint (str): Entrypoint script for the application (e.g., 'app.py'). Required.
        folder_path (str): The server-side folder path where the Dockerfile will be generated. Required.
       

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "Dockerfile generated in /path/to/folder"}`
              Example error: `{"success": False, "error": "Dockerfile generation error: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/dockerfile-gen"
    params = {
        "app_type": app_type,
        "python_version": python_version,
        "work_dir": work_dir,
        "entrypoint": entrypoint,
        "folder_path": folder_path
    }
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def jenkinsfile_gen(folder_path: str, app_name: str, port: str) -> Dict[str, Any]:
    """
    Generates a Jenkinsfile in the specified server-side folder path.
    Optionally, app_name, port, and version can be provided if the server supports them as query parameters.

    Args:
        folder_path (str): The server-side folder path where the Jenkinsfile will be generated. Required.
        app_name (str): Name of the application (e.g., "streamlitApp").
        port (str): Port the application runs on (e.g., '8501').

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "Jenkinsfile generated in /path/to/folder"}`
              Example error: `{"success": False, "error": "Jenkinsfile generation error: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/jenkinsfile-gen"
    params: Dict[str, Any] = {"folder_path": folder_path}
    if app_name: params["app_name"] = app_name
    if port: params["port"] = port

    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def infra(work_dir: str, instance_size: str) -> Dict[str, Any]:
    """
    Generates Terraform infrastructure configurations and can trigger an initial setup
    for the user's requested infrastructure based on the specified working directory and instance size.

    Args:
        work_dir (str): The server-side working directory path for Terraform operations. Required.
        instance_size (str): The EC2 instance size (e.g., 't2.micro', 't3.medium'). Required.

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "Infrastructure setup process initiated successfully."}`
              Example error: `{"success": False, "error": "Infra setup error: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/infra"
    params = {"work_dir": work_dir, "instance_size": instance_size}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def get_environments(folder_path: str) -> Dict[str, Any]:
    """
    Retrieves available Python versions found in a specified server-side directory.
    This can include system Python, conda environments, or brew environments scanned by the server.

    Args:
        folder_path (str): The server-side folder path to scan for Python environments. Required.

    Returns:
        dict: API response.
              Example success: `{"success": True, "python_versions": ["3.8", "3.9.7"]}`
              Example error: `{"success": False, "error": "Error getting environments: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/get-environments"
    params = {"folder_path": folder_path}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def github_webhook_setup(folder_path: str) -> Dict[str, Any]:
    """
    Sets up a GitHub webhook for a repository associated with the specified server-side folder path.
    This typically requires prior configuration of GitHub credentials on the server.

    Args:
        folder_path (str): The server-side path to the folder (Git repository)
                           for which the GitHub webhook needs to be set up. Required.

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "Webhook setup process completed.", "details": "Webhook created with ID 12345"}`
              Example error: `{"success": False, "error": "GitHub webhook setup error: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/github-webhook-setup"
    params = {"folder_path": folder_path}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

# --- Acube Endpoints ---
def acube_cicd_plan(user_request: str, service_type: str) -> Dict[str, Any]:
    """
    Generates a CI/CD plan using the Acube orchestrator based on a user request and service type.
    May involve IAM checks and LLM interactions on the server side.

    Args:
        user_request (str): The user's natural language request or objective for the CI/CD pipeline.
        service_type (str): The type of service or application (e.g., "streamlit", "aws-lambda").

    Returns:
        dict: API response.
              Example success: `{"success": True, "Reasoning_Steps": [...], "Tool_Execution_Order": [...]}`
              Example IAM fail: `{"success": False, "error_type": "Credential Error", "IAM_Check_Details": {...}}`
              Example general error: `{"success": False, "error": "Error generating CICD plan: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/acube/cicdplan"
    params = {"user_request": user_request, "service_type": service_type}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def acube_dynamic_question(tool_name: str) -> Dict[str, Any]:
    """
    Retrieves a dynamic question for a specific tool within the Acube interactive flow.
    The question generated depends on the tool's state and previously provided answers.

    Args:
        tool_name (str): The name of the tool for which to get the dynamic question (e.g., "analyzer", "dockerfile-gen").

    Returns:
        dict: API response.
              Example success: `{"success": True, "analyzer": "Which folder path do you want to analyze?"}` or `{"success": True, "dockerfile-gen": "Pass"}` (if no question needed)
              Example error: `{"success": False, "error": "Tool 'X' configuration not found."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/acube/dynamicquestion"
    params = {"tool_name": tool_name}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def acube_answer_validator(tool_name: str, answer: str) -> Dict[str, Any]:
    """
    Validates a user's answer provided for a specific tool's dynamic question in the Acube flow.
    The server uses an LLM to parse and validate the answer against the tool's requirements.

    Args:
        tool_name (str): The name of the tool for which the answer is being validated.
        answer (str): The user's natural language answer to the tool's question.

    Returns:
        dict: API response.
              Example success: `{"success": True, "variables": {"folder_path": "/tmp", "app_type": "streamlit"}}`
              Example error: `{"success": False, "error": "Validation error: Could not extract X from your answer."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/acube/answervalidator"
    params = {"tool_name": tool_name, "answer": answer}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

# --- Other Endpoints ---
def dashboard_file_data() -> Dict[str, Any]:
    """
    Retrieves the content of pre-defined generated files (like Dockerfile, Jenkinsfile, etc.)
    from a server-configured location, intended for display on a dashboard.

    Returns:
        dict: API response.
              Example success: `{"success": True, "files_data": [{"filename": "Dockerfile", "content": "..."}, ...]}`
              Example empty: `{"success": True, "message": "No relevant files found to display.", "files_data": []}`
              Example error: `{"success": False, "error": "'folder_path' not specified in server config."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/dashboard-file-data"
    response = requests.get(endpoint)
    return handle_api_response(response)

def edit_file(filename: str, original_code: str, prompt: str) -> Dict[str, Any]:
    """
    Requests the server to edit a specified file's content based on a natural language prompt,
    likely using an LLM. The server then attempts to write the updated code back to the file.

    Args:
        filename (str): The name of the file (relative to a server-defined base path) to be edited.
        original_code (str): The current/original content of the file.
        prompt (str): The natural language prompt describing the desired changes.

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "File 'X' updated successfully.", "status_detail": "Write successful"}`
              Example error: `{"success": False, "error": "Failed to get updated code from LLM."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/edit-file"
    payload = {"filename": filename, "original_code": original_code, "prompt": prompt}
    response = requests.post(endpoint, json=payload)
    return handle_api_response(response)

def get_instance_ip(work_dir: str) -> Dict[str, Any]:
    """
    Retrieves the public IP address of an EC2 instance, typically one that was
    provisioned or managed via operations related to the given server-side working directory.

    Args:
        work_dir (str): The server-side working directory associated with the instance
                        (e.g., where Terraform state might be located). Required.

    Returns:
        dict: API response.
              Example success: `{"success": True, "public_ip": "12.34.56.78"}`
              Example error: `{"success": False, "error": "Failed to retrieve instance IP. It might not be available yet."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/get-instance-ip"
    params = {"work_dir": work_dir}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)


if __name__ == '__main__':
    print("Demonstrating API client functions. Ensure the FastAPI server is running at", BASE_URL)

    # Example of how to use a function and handle potential errors
    try:
        print("\n--- Example: get_creds (if configured on server) ---")
        # help(get_creds) # To see the docstring
        # creds_info = get_creds()
        # print("Get Creds Response:", json.dumps(creds_info, indent=2))

        print("\n--- Example: analyzer (provide valid paths if testing) ---")
        # help(analyzer)
        # analysis = analyzer(folder_path="/path/to/your/local_project_for_server_to_access", 
        #                          environment_path="/path/to/python_env_on_server")
        # print("Analyzer Response:", json.dumps(analysis, indent=2))
        
        print("\n--- An example of calling an endpoint that might 'fail' logically ---")
        print("--- For instance, analyzer without a required folder_path (if server enforces it) ---")
        # try:
        #     # Assuming the server returns {"success": False, "error": "Analyzer error: folder_path is required."}
        #     # for this call, which our handle_api_response should catch.
        #     result = analyzer(environment_path="/some/env") # Missing folder_path
        #     print("Unexpected success:", result)
        # except APIClientError as e:
        #     print(f"Caught expected APIClientError for missing folder_path: {e}")
        #     if e.response_data:
        #         print("Error Response Data:", json.dumps(e.response_data, indent=2))

        print(f"\n--- Help for {analyzer.__name__} ---")
        help(analyzer)


    except APIClientError as e:
        print(f"\nAPI Client Error during example execution: {e}")
        if e.response_data:
            print("Error Response Data:", json.dumps(e.response_data, indent=2))
        if e.status_code:
            print("Status Code:", e.status_code)
    except Exception as e: # Catch any other unexpected errors during the example run
        print(f"\nAn unexpected error occurred during example execution: {type(e).__name__} - {e}")

def github_webhook_setup(folder_path: str) -> Dict[str, Any]:
    """
    Sets up a GitHub webhook for a repository associated with the specified server-side folder path.
    This requires infra setup to be completed.

    Args:
        folder_path (str): The server-side path to the folder (Git repository)
                           for which the GitHub webhook needs to be set up. Required.

    Returns:
        dict: API response.
              Example success: `{"success": True, "message": "Webhook setup process completed.", "details": "Webhook created with ID 12345"}`
              Example error: `{"success": False, "error": "GitHub webhook setup error: details"}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/github-webhook-setup"
    params = {"folder_path": folder_path}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

def get_instance_ip(work_dir: str) -> Dict[str, Any]:
    """
    Retrieves the public IP address of an EC2 instance, typically one that was
    provisioned or managed via operations related to the given server-side working directory.
    You should add the specified port in the conversation history to returned IP and show it to the user.
    The IP address is expected to be available after the infrastructure setup is complete and the user pushes code into the repository.

    Args:
        work_dir (str): The server-side working directory associated with the instance
                        (e.g., where Terraform state might be located). Required.

    Returns:
        dict: API response.
              Example success: `{"success": True, "public_ip": "12.34.56.78"}`
              Example error: `{"success": False, "error": "Failed to retrieve instance IP. It might not be available yet."}`

    Raises:
        APIClientError: If the API call fails or returns an error.
    """
    endpoint = f"{BASE_URL}/get-instance-ip"
    params = {"work_dir": work_dir}
    response = requests.get(endpoint, params=params)
    return handle_api_response(response)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="auto_anchor_agent",
    instruction = """
You are a friendly and expert DevOps assistant. Your purpose is to help users who have little to no DevOps knowledge deploy their applications. You will achieve this by guiding them through a simple, conversational, step-by-step process.

Your entire interaction model is built on the following core principles:

1.  **Be a Guide, Not an Orchestrator:** You operate a suite of tools behind the scenes, but you MUST NEVER mention the tools or the act of "calling a tool." The user should feel like they are talking to a single, intelligent assistant.
    * **Bad:** "I will now use the Code_Analyzer tool on your folder."
    * **Good:** "Okay, I've taken a look at your project code. It seems to be a Python Flask application."

2.  **One Question at a Time:** To avoid overwhelming the user, ask only ONE question at a time. Wait for their answer before moving to the next logical step.

3.  **Natural, Jargon-Free Language:** Your language must be simple, encouraging, and completely free of technical DevOps jargon. Explain what you need in plain terms.
    * **Bad:** "What arguments are required for the container entrypoint?"
    * **Good:** "When your application starts, what command should be run?"
    * **Bad:** "Please provide the `folder_path` parameter."
    * **Good:** "Can you please tell me the full path to your project's folder on your computer?"

4.  **Remember Everything (Stateful Conversation):** You have a perfect memory of the current conversation. If the user has already provided a piece of information (like a project folder path, an application name, or a port number), you MUST remember it and reuse it for subsequent background tasks.
    * **STRICT RULE:** Do not ask for the same information more than once. If a later step needs the project path, use the one you already have.

**Your Workflow:**
1.  Start by asking the user for their high-level goal (e.g., "I want to get my web app online").
2.  Based on their goal, determine the very first, most logical question to ask (this is almost always the location of their code).
3.  When you receive an answer, internally map it to the input of the appropriate tool. Only run the tool once you receive all required parameters for that particular tool.  And only then call the tool with the provided input.
4.  After the background tool runs, process its output and formulate the next logical, user-friendly question.
5.  Continue this question-answer-process cycle until the user's goal is complete. By calling all the necessary tools in the background, you will eventually reach a point where you can provide a final result or confirmation.
6.  Conclude with a success message and any relevant information, like a public URL.
""",

# You can now use the prompt_template variable in your Python code.
# print(prompt_template),
    tools=[
    analyzer,
    dockerfile_gen,
    jenkinsfile_gen,
    infra,
    github_webhook_setup,
    get_instance_ip,
    ],
    generate_content_config=types.GenerateContentConfig(temperature=0.1),

)

