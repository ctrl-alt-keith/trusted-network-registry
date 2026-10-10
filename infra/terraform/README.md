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
expire the current version. If a delete marker becomes current, however, every
data version is noncurrent and can expire. Akamai schedules lifecycle processing
at bucket-local midnight after a noncurrent version reaches 24 hours; deletion
may take a later pass. The rule does not cap the number of versions when
publishes are frequent. Before applying, confirm `object_key` equals the
publisher's configured `publish.object_key`, then review the complete lifecycle
policy and plan.
The bucket resource requires Object Storage credentials to manage lifecycle
rules. See [Akamai lifecycle policies](https://techdocs.akamai.com/cloud-computing/docs/lifecycle-policies).

Configure the Linode provider through environment variables or your normal
Terraform credential flow. Object Storage access keys and secrets used by
Terraform can be stored in Terraform state, so keep state private and encrypted
where practical.
