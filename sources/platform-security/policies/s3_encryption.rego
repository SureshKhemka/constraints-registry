package s3.encryption

import rego.v1

deny contains msg if {
	some name, bucket in input.resources.aws_s3_bucket
	not bucket.sse
	msg := sprintf("S3 bucket '%s' has no server-side encryption", [name])
}
