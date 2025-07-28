from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field, field_validator  # Pydantic v2
from typing import Any, get_args, get_origin, Union
import json
from langchain_openai import ChatOpenAI
from typing import Optional, List
from dotenv import load_dotenv
import os
from constants import * 
load_dotenv()
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


model = ChatOpenAI(model="gpt-4o",temperature=0)



def get_dummy_value(field_type: Any) -> Any:
    """Generate a dummy value based on the field type."""
    origin = get_origin(field_type)  # Handle typing constructs like Optional
    args = get_args(field_type)

    if origin is Union and type(None) in args:  # Handle Optional fields
        field_type = args[0]  # Get the main type

    # Handle basic types
    if field_type is str:
        return ""
    elif field_type is int:
        return 0
    elif field_type is float:
        return 0.0
    elif field_type is bool:
        return False
    elif field_type is list:
        return []
    elif field_type is dict:
        return {}
    elif issubclass(field_type, BaseModel):
        # For nested Pydantic models, create an instance with dummy values
        return field_type(**{f: get_dummy_value(t) for f, t in field_type.__annotations__.items()})
    else:
        return None  # Fallback for unknown types
    

class AnalyzerValidator(BaseModel):
    folder_path: Optional[str] = Field(description="The path to analyze.", default=None)
    environment_path: Optional[str] = Field(description="Environment context.", default=None)

    # @field_validator("folder_path")
    # @classmethod

    # def validate_folder_path(cls, value):
    #     if value and value.startswith("/"):
    #         if not os.path.exists(value):
    #             raise ValueError("Folder path does not exist.")
    #     else:
    #         raise ValueError("Folder path must start with a '/'.")
    #     return value


class GetCredsValidator(BaseModel):
    # No specific inputs required for this endpoint currently
    pass


class DockerFileGenValidator(BaseModel):
    app_type: str = Field(description="Type of the application (e.g., 'streamlit').")
    python_version: str = Field(description="Python version to use (e.g., '3.8').")
    work_dir: str = Field(description="The working directory path.")
    entrypoint: str = Field(description="Entrypoint for the application.")
    folder_path: str = Field(description="The folder path where files will be generated.")

    
    # @field_validator("work_dir", "folder_path", mode="before")
    # @classmethod
    # def validate_paths(cls, value):
    #     if not value.startswith("/"):
    #         raise ValueError("Paths must start with a '/'.")
    #     if not os.path.exists(value):
    #         raise ValueError(f"Path does not exist: {value}")
    #     return value
    
class JenkinsFileGenValidator(BaseModel):
    folder_path: str = Field(description="The folder path where files will be generated.")
    
    # @field_validator("folder_path", mode="before")
    # @classmethod
    # def validate_paths(cls, value):
    #     if not value.startswith("/"):
    #         raise ValueError("Paths must start with a '/'.")
    #     if not os.path.exists(value):
    #         raise ValueError(f"Path does not exist: {value}")
    #     return value


class InfraValidator(BaseModel):
    work_dir: str = Field(description="The working directory path.")
    instance_size: str = Field(description="The EC2 instance size as required by the User.")

    # @field_validator("work_dir")
    # @classmethod
    # def validate_work_dir(cls, value):
    #     if not value.startswith("/"):
    #         raise ValueError("Working directory path must start with a '/'.")
    #     if not os.path.exists(value):
    #         raise ValueError("Working directory does not exist.")
    #     return value


class GetEnvironmentsValidator(BaseModel):
    folder_path: str = Field(description="The folder path to analyze.")

    # @field_validator("folder_path")
    # @classmethod
    # def validate_folder_path(cls, value):
    #     if not value.startswith("/"):
    #         raise ValueError("Folder path must start with a '/'.")
    #     if not os.path.exists(value):
    #         raise ValueError("Folder path does not exist.")
    #     return value

class GitHubWebhookSetupValidator(BaseModel):
    folder_path: str = Field(description="The folder path to analyze.")



def validator(query, pydantic_object, pydantic_class, model):

    template = """
    Your job is to match the user response with the given fields. Understand the response carefully, If you don't find anything related to the fields then leave the field empty.
    You have also been provided with an older pydantic object, if that object has any fields that can be used then club it with the user's answer and then return the new object.
    User response : {query}.

    Older Pydantic Object : {pydantic_object}
    
    Respond with this format :{format_instructions}\n.
    """
    parser = PydanticOutputParser(pydantic_object=pydantic_class)
    
    prompt = PromptTemplate(
                            template=template,
                            input_variables=["query", "pydantic_object"],
                            partial_variables={"format_instructions": parser.get_format_instructions()},
                            )
    
    chain = prompt | model | parser

    try:
        response = chain.invoke({"query": query, "pydantic_object": pydantic_object})
        return response.__dict__
    
    except Exception as e:
        return e
    

def feedback_loop_question(error, model):
    template = """
    Your job is to look at the pydantic parsing error given below and as the user to enter the fields correctly. 
    Understand the error carefully, and then mention to the user what went wrong and what he has to do to correct it and tell them to correct it in the way that the error says it.
    Error : {error}.
    Only list the solutions along with the errors as points. The solutions should be concise telling the user what to correct. Dont Give examples, just tell him what to correct based on his input.
    """
    prompt = PromptTemplate(
                            template=template,
                            input_variables=["error"]
                            )
    
    chain = prompt | model | StrOutputParser()

    try:
        response = chain.invoke({"error": error})
        return response
    
    except Exception as e:
        return e
    
def feedback_loop_question_v2(pydantic_object, error, model):
    template = """
    Your job is to look at the pydantic parsing error given below along with the older pydantic object.
    The user was trying to fill a value into this older object and ran into the following error.
    Error : {error}.
    
    Pydantic Object : {pydantic_object}.

    Tell the user why there was an error when he was tring to fill in the variable into the older pydantic object in one line and tell him to provide the input for that variable again.
    """
    prompt = PromptTemplate(
                            template=template,
                            input_variables=["error", "pydantic_object"]
                            )
    
    chain = prompt | model | StrOutputParser()

    try:
        response = chain.invoke({"error": error, "pydantic_object": pydantic_object})
        print(response)
        return response
    
    except Exception as e:
        return e
    
def update_answers(ValidatorClass):

    with open(ANSWER_VARS_PATH, "r") as f:
        answers = json.load(f)
    

    # Prepare all fields with dummy values or actual answers
    all_fields = {
        field: answers.get(field, get_dummy_value(ValidatorClass.__annotations__[field]))
        for field in ValidatorClass.__annotations__
    }

    # Return an instance of the ValidatorClass
    try:
        return ValidatorClass(**all_fields)
    except:
        return ValidatorClass

def llm_updated_question(tool_name, ValidatorClass):
    
    with open(TOOL_PATH,"r") as f:
        json_tools=json.load(f)

    for tool in json_tools["tools"]:
        if tool["name"] == tool_name:
            # class_name=tool["class"]
            question=tool["question"]
            break
    
    template="""Your job is to ask the user to fill in the variables of a pydantic class. 
    You have been given the initial question for that class, but you have to reframe the question if the user has already entered some of the variables.
    **Important**
    - You have to omit the variables that have already been entered in your question. 
    - If none one the variables have been entered then return the question as it is by asking the user to enter all the variables with 'none'. 
    - If all the variables are entered then return 'Pass'
    
    Question : {question}

    Pydantic Class : {class}
    
    Only returned the reframed question in 1 line mentioning the variables to be filled and nothing else.
    """

    prompt = PromptTemplate(
                            template=template,
                            input_variables=["question", "class"]
                            )
    
    chain = prompt | model | StrOutputParser()

    try:
        response = chain.invoke({"question": question, "class": ValidatorClass})
        return response
    
    except Exception as e:
        return e
