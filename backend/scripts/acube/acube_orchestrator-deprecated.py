from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, validator
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from openai import OpenAI
import os
import boto3
import json
from constants import * 

load_dotenv("../")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

model = ChatOpenAI(model="gpt-4o", temperature=0)

# Initialize the IAM client
client = boto3.client('iam')

# To be implemented
class AWSresponse(BaseModel):
    has_access: bool = Field(description="If the request can be resolved with the current policies or not") 

class ToolSelection(BaseModel):
    reasoning: str = Field(description="Your chain of thought for choosing the strategy and order of tool execution. Give it to me in pointwise steps")
    tools: list = Field(description="Ordered list of tools in their execution order based on your strategy. Only the tool names in the list. Carefully look at the description of each tool and how they are dependant on each other.")

def orchestrator(tools_metadata, user_req, model):
    template="""You are the orchestrator of the below tools. A user is trying to solve a devops issue and needs your help to come up with a step by step plan. 
    Think of a strategy to solve his problem by making use of these tools in any order. The result of using all of these should solve the users problem.
    The user request : {user_request}.

    List of available tools : {tools_metadata}.

    Respond with this format :{format_instructions}\n.
    """

    parser = PydanticOutputParser(pydantic_object=ToolSelection)
    
    prompt = PromptTemplate(
                            template=template,
                            input_variables=["user_req", "tools_metadata"],
                            partial_variables={"format_instructions": parser.get_format_instructions()},
                            )
    
    chain = prompt | model | parser

    try:
        response = chain.invoke({"user_request": user_req, "tools_metadata": tools_metadata})
        return response.__dict__
    
    except Exception as e:
        return e
    



class AWSPolicies():
    @staticmethod
    def list_roles_with_managed_policy_names():
        try:
            # List all roles
            roles_response = client.list_roles()
            roles = roles_response['Roles']

            roles_data = {}  # Dictionary to store roles and their managed policies

            for role in roles:
                role_name = role['RoleName']
                roles_data[role_name] = []  # Initialize with an empty list for policies
                
                # List managed policies for the role
                attached_policies_response = client.list_attached_role_policies(RoleName=role_name)
                attached_policies = attached_policies_response['AttachedPolicies']
                
                # Add only policy names to the list
                for policy in attached_policies:
                    roles_data[role_name].append(policy['PolicyName'])

            # Return or print the data in JSON format
            return json.dumps(roles_data, indent=4)

        except Exception as e:
            return json.dumps({"Error": str(e)}, indent=4)

             
    def validate_policies(self, model):
        roles_policies_json = self.list_roles_with_managed_policy_names()
        user_request = self.service_type+self.user_req

        template="""
        You have been given the list of AWS managed policies of a user. List of policies : {roles_policies_json}.

        Your job is to understand the user's request and figure out whether he can perform the action he wants to based on his IAM role list.

        If a user request is not related to an AWS service and is meant for local execution, return it as True

        User request :{user_request}.

        Respond with this format :{format_instructions}\n.
        """

        parser = PydanticOutputParser(pydantic_object=AWSresponse)
        
        prompt = PromptTemplate(
                                template=template,
                                input_variables=["roles_policies_json", "user_request"],
                                partial_variables={"format_instructions": parser.get_format_instructions()},
                                )
        
        chain = prompt | model | parser

        try:
            response = chain.invoke({"roles_policies_json": roles_policies_json, "user_request": user_request})
            return response.__dict__
        
        except Exception as e:
            return e

class Orchestrator(AWSPolicies):

    def __init__(self,user_req,service_type):
        self.user_req=user_req
        self.service_type=service_type

    def plan(self):
        user_request = self.user_req  # + self.service_type
        with open(TOOL_PATH, "r") as f:
            tools_metadata = json.dumps(json.load(f))

        plan = orchestrator(tools_metadata, user_request, model)
        return plan



        


        