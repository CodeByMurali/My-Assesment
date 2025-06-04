import boto3
import json
import time
import os

CODECOMMIT_REPO_NAME = 'AWS-CICD-StepFunction'
CODEBUILD_PROJECT_NAME = 'Numerix-webapp-build-server-test'
CODEDEPLOY_APP_NAME = 'Numerix-web-app-test'
CODEDEPLOY_DEPLOYMENT_GROUP_NAME = 'Numerix-webapp-Staging-Deployment-Group-test'

STEP_FUNCTIONS_ROLE_NAME = 'StepFunctions-Numerix-CICD-Orchestrator-role-vhnkzvull'
CODEPIPELINE_ROLE_NAME = 'AWSCodePipelineServiceRole-us-east-1-Numerix'

LAMBDA_FUNCTION_1_NAME = 'MarkPRReadyForMRLambda'
LAMBDA_FUNCTION_2_NAME = 'NotifyPRIntegrationTestFailure'
LAMBDA_FUNCTION_3_NAME = 'NotifyPRFailure'


def get_aws_account_id_and_region():
    """Fetches AWS account ID and region from boto3 session."""
    sts_client = boto3.client('sts')
    identity = sts_client.get_caller_identity()
    account_id = identity['Account']
    session = boto3.session.Session()
    region = session.region_name
    if not region:
        raise ValueError(
            "AWS region not found. Please configure your AWS CLI or set AWS_REGION environment variable.")
    return account_id, region

# Get the IAM role ARN for Step Functions and CodePipeline


def get_iam_role_arn(role_name, account_id):
    """Fetches the ARN of an IAM role."""
    iam_client = boto3.client('iam')
    try:
        response = iam_client.get_role(RoleName=role_name)
        return response['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        print(f"Error: IAM Role '{role_name}' not found. Please create it.")
        return None
    except Exception as e:
        print(f"Error fetching IAM Role '{role_name}': {e}")
        return None

# Create or update the AWS Step Functions state machine


def create_step_function(account_id, region, sf_role_arn):
    """Creates or updates an AWS Step Functions state machine."""
    client = boto3.client('stepfunctions', region_name=region)
    state_machine_name = 'Numerix-CICD-Orchestrator-Test'

    definition = {
        "Comment": "A simple AWS Step Functions state machine example",
        "StartAt": "Step1",
        "States": {
            "Step1": {
                "Type": "Task",
                "Resource": f"arn:aws:lambda:{region}:{account_id}:function:{LAMBDA_FUNCTION_1_NAME}",
                "Next": "ChoiceState"
            },
            "ChoiceState": {
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.status",
                        "StringEquals": "success",
                        "Next": "Step2"
                    },
                    {
                        "Variable": "$.status",
                        "StringEquals": "failure",
                        "Next": "Step3"
                    }
                ],
                "Default": "Step1"
            },
            "Step2": {
                "Type": "Task",
                "Resource": f"arn:aws:lambda:{region}:{account_id}:function:{LAMBDA_FUNCTION_2_NAME}",
                "End": True
            },
            "Step3": {
                "Type": "Task",
                "Resource": f"arn:aws:lambda:{region}:{account_id}:function:{LAMBDA_FUNCTION_3_NAME}",
                "Next": "Step2"
            }
        }
    }

    try:
        response = client.create_state_machine(
            name=state_machine_name,
            # definition must be JSON string
            definition=json.dumps(definition),
            roleArn=sf_role_arn,
            type='STANDARD'
        )
        print(
            f"Step function '{state_machine_name}' created with ARN: {response['stateMachineArn']}")
        return response['stateMachineArn']
    except client.exceptions.StateMachineAlreadyExists:
        print(
            f"Step function '{state_machine_name}' already exists. Attempting to update...")
        existing_sfn_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:{state_machine_name}"
        try:
            response = client.update_state_machine(
                stateMachineArn=existing_sfn_arn,
                definition=json.dumps(definition),
                roleArn=sf_role_arn
            )
            print(
                f"Step function '{state_machine_name}' updated. ARN: {response['stateMachineArn']}")
            return response['stateMachineArn']
        except Exception as update_e:
            print(
                f"Error updating Step function '{state_machine_name}': {update_e}")
            return None
    except Exception as e:
        print(f"Error creating Step function '{state_machine_name}': {e}")
        return None

# Setup AWS CodePipeline with the specified stages and actions


def setup_codepipeline(account_id, region, cp_role_arn, s3_artifact_bucket_name):
    """Creates or updates an AWS CodePipeline."""
    client = boto3.client('codepipeline', region_name=region)
    pipeline_name = 'Numerix-test'

    pipeline = {
        'name': pipeline_name,
        'roleArn': cp_role_arn,
        'artifactStore': {
            'type': 'S3',
            'location': s3_artifact_bucket_name
        },
        'stages': [
            {
                'name': 'Source',
                'actions': [
                    {
                        'name': 'SourceAction',
                        'actionTypeId': {
                            'category': 'Source',
                            'owner': 'AWS',
                            'provider': 'CodeCommit',
                            'version': '1'
                        },
                        'outputArtifacts': [
                            {
                                'name': 'SourceArtifact'
                            }
                        ],
                        'configuration': {
                            'RepositoryName': CODECOMMIT_REPO_NAME,
                            'BranchName': 'master',
                            'PollForSourceChanges': 'true'  # FIX: Must be string 'true', not boolean True
                        }
                    }
                ]
            },
            {
                'name': 'Build',
                'actions': [
                    {
                        'name': 'BuildAction',
                        'actionTypeId': {
                            'category': 'Build',
                            'owner': 'AWS',
                            'provider': 'CodeBuild',
                            'version': '1'
                        },
                        'inputArtifacts': [
                            {
                                'name': 'SourceArtifact'
                            }
                        ],
                        'outputArtifacts': [
                            {
                                'name': 'BuildArtifact'
                            }
                        ],
                        'configuration': {
                            'ProjectName': CODEBUILD_PROJECT_NAME
                        }
                    }
                ]
            },
            {
                'name': 'Deploy',
                'actions': [
                    {
                        'name': 'DeployAction',
                        'actionTypeId': {
                            'category': 'Deploy',
                            'owner': 'AWS',
                            'provider': 'CodeDeploy',
                            'version': '1'
                        },
                        'inputArtifacts': [
                            {
                                'name': 'BuildArtifact'
                            }
                        ],
                        'configuration': {
                            'ApplicationName': CODEDEPLOY_APP_NAME,
                            'DeploymentGroupName': CODEDEPLOY_DEPLOYMENT_GROUP_NAME
                        }
                    }
                ]
            }
        ]
    }

    try:
        response = client.create_pipeline(pipeline=pipeline)
        print(
            f"CodePipeline '{pipeline_name}' created with name: {response['pipeline']['name']}")
        return response['pipeline']['name']
    except client.exceptions.PipelineNameInUseException:  # FIX: Correct exception name
        print(
            f"Pipeline '{pipeline_name}' already exists. Attempting to update...")
        try:
            current_pipeline = client.get_pipeline(name=pipeline_name)
            pipeline['version'] = current_pipeline['pipeline']['version']
            response = client.update_pipeline(pipeline=pipeline)
            print(
                f"CodePipeline '{pipeline_name}' updated with name: {response['pipeline']['name']}")
            return response['pipeline']['name']
        except Exception as update_e:
            print(f"Error updating CodePipeline '{pipeline_name}': {update_e}")
            return None
    except Exception as e:
        print(f"Error creating CodePipeline '{pipeline_name}': {e}")
        return None


if __name__ == "__main__":
    account_id, region = get_aws_account_id_and_region()
    sf_role_arn = get_iam_role_arn(STEP_FUNCTIONS_ROLE_NAME, account_id)
    cp_role_arn = get_iam_role_arn(CODEPIPELINE_ROLE_NAME, account_id)

    if not sf_role_arn or not cp_role_arn:
        print("Required IAM roles not found or accessible. Please ensure they exist and your AWS credentials have 'iam:GetRole' permission.")
        exit(1)

    s3_artifact_bucket_name = "codepipeline-us-east-1-42ea5acf77cc-45d5-b7b8-0d7ee0fc2620"
    print(
        f"Using pre-existing S3 artifact bucket: '{s3_artifact_bucket_name}'")

    # --- Provision Step Function ---
    print("\n--- Provisioning AWS Step Function ---")
    state_machine_arn = create_step_function(account_id, region, sf_role_arn)
    if state_machine_arn:
        print("Step function provisioning complete.")
    else:
        print("Step function provisioning failed.")

    # --- Provision CodePipeline ---
    print("\n--- Provisioning AWS CodePipeline ---")
    pipeline_name = setup_codepipeline(
        account_id, region, cp_role_arn, s3_artifact_bucket_name)
    if pipeline_name:
        print("CodePipeline provisioning complete.")
    else:
        print("CodePipeline provisioning failed.")
