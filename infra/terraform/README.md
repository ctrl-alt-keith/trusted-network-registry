# Terraform Storage Infrastructure

This Terraform configuration provisions private Linode Object Storage
infrastructure for the registry publisher.

Terraform owns:

- the bucket
- bucket privacy posture
- optional bucket versioning

Terraform does not own:

- generated registry JSON contents
- uploaded registry objects
- generated `.auto.tfvars.json`
- firewall rules
- consumer mutations

Configure the Linode provider through environment variables or your normal
Terraform credential flow. Object Storage access keys and secrets used by
Terraform can be stored in Terraform state, so keep state private and encrypted
where practical.
