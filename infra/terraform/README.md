# Terraform Storage Infrastructure

This Terraform configuration provisions private Linode Object Storage
infrastructure for the registry publisher.

Terraform owns:

- the bucket
- bucket privacy posture
- optional bucket versioning
- a one-day expiration rule for noncurrent versions whose keys start with
  `object_key`

Terraform does not own:

- generated registry JSON contents
- uploaded registry objects
- generated `.auto.tfvars.json`
- firewall rules
- consumer mutations

The lifecycle rule uses a prefix filter, so it also applies to any future key
that starts with `object_key`; it cannot select only one exact key. It does not
expire the current version. Akamai enforces a one-day rule at the first bucket-
local midnight after a noncurrent version reaches 24 hours, so the rule does
not cap the number of versions when publishes are frequent. Before applying,
review the actual `object_key`, the complete lifecycle policy, and the plan.
The bucket resource requires Object Storage credentials to manage lifecycle
rules. See [Akamai lifecycle policies](https://techdocs.akamai.com/cloud-computing/docs/lifecycle-policies).

Configure the Linode provider through environment variables or your normal
Terraform credential flow. Object Storage access keys and secrets used by
Terraform can be stored in Terraform state, so keep state private and encrypted
where practical.
