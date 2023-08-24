resource "aws_cloudformation_stack" "pg15_migration_function" {
  name = "guardrails-pg15-migration-function-custom-resource"
  parameters = {
    FunctionArn  = aws_lambda_function.pg15_migrate.arn
    MigrationAction = var.migration_action
    DeploymentFlag = "Blue"
    WorkspaceName = var.workspace_name
  }

  template_body = <<STACK
{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Parameters" : {
    "FunctionArn" : {
      "Type" : "String",
      "Description" : "Lambda Function ARN"
    },
    "MigrationAction" : {
      "Type" : "String",
      "AllowedValues" : ["getVersion", "disableTriggers", "enableTriggers", "updatePgExtensions"],
      "Description" : "Action to pass to the Lambda Function"
    },
    "DeploymentFlag" : {
      "Type" : "String",
      "AllowedValues" : ["Blue", "Green"],
      "Description" : "Flip to rerun the Lambda Function"
    },
    "WorkspaceName" : {
      "Type" : "String",
      "Default" : "Workspace",
      "Description" : "Name of the turbot workspace to manage (all lowercase, no spaces)"
    }
  },
  "Resources" : {
    "GuardrailsPG15MigrationFunction": {
      "Type" : "AWS::CloudFormation::CustomResource",
      "DeletionPolicy" : "Delete",
      "UpdateReplacePolicy" : "Delete",
      "Properties" : {
        "ServiceToken" : { "Ref" : "FunctionArn" },
        "Action" : { "Ref" : "MigrationAction" },
        "DeploymentFlag" : { "Ref" : "DeploymentFlag" },
        "Workspace" : { "Ref" : "WorkspaceName" }
      }
    }
  }
}
STACK
}