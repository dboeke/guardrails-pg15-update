data "aws_db_instance" "guardrails_db" {
  db_instance_identifier = var.db_instance_identifier
}

output "guardrails_db_security_groups" {
  value = data.aws_db_instance.guardrails_db.vpc_security_groups
}