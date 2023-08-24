variable "aws_region" {
  type = string
}

variable "aws_profile" {
  type = string
}

variable "db_instance_identifier" {
  type = string
}

variable "workspace_name" {
  type = string
}

variable "security_group_ids" {
  type = list
}

variable "subnet_ids" {
  type = list
}

variable "migration_action" {
  type    = string
  default = "getVersion"

  validation {
    condition     = contains(["getVersion", "disableTriggers", "enableTriggers", "updatePgExtensions"], var.migration_action)
    error_message = "Allowed values: getVersion, disableTriggers, enableTriggers, updatePgExtensions"
  } 
}

resource "aws_lambda_function" "pg15_migrate" {
  function_name                  = "guardrails-pg15-migrate-function"
  s3_bucket                      = aws_s3_bucket.lambda_bucket.id
  s3_key                         = aws_s3_object.pg_migrate_function_source.key
  runtime                        = "python3.9"
  handler                        = "lambda_function.handler"
  source_code_hash               = data.archive_file.pg_migrate_function.output_base64sha256
  role                           = aws_iam_role.lambda_exec.arn
  reserved_concurrent_executions = 1
  timeout                        = 300

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = concat(data.aws_db_instance.guardrails_db.vpc_security_groups,var.security_group_ids)
  }

  environment {
    variables = {
      DB_HOST = var.db_instance_identifier
    }
  }
}

resource "aws_cloudwatch_log_group" "pg15_migrate" {
  name              = "/aws/lambda/${aws_lambda_function.pg15_migrate.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "pg15_migrate" {
  function_name                = aws_lambda_function.pg15_migrate.function_name
  maximum_event_age_in_seconds = 300
  maximum_retry_attempts       = 0
}