resource "random_pet" "lambda_bucket_name" {
  prefix = "guardrails-pg15-migrate-function"
}

resource "aws_s3_bucket" "lambda_bucket" {
  bucket = random_pet.lambda_bucket_name.id  
  force_destroy = true
}

data "archive_file" "pg_migrate_function" {
  type        = "zip"
  source_dir  = "${path.module}/pg-migrate-function"
  output_path = "${path.module}/pg-migrate-function.zip"
}

resource "aws_s3_object" "pg_migrate_function_source" {
  bucket = aws_s3_bucket.lambda_bucket.id
  key    = "pg-migrate-function.zip"
  source = data.archive_file.pg_migrate_function.output_path
  etag = filemd5(data.archive_file.pg_migrate_function.output_path)
}

