# Real enforcement logic owned by the source repo, referenced by binding locator
# (FR-CONSTRAINT-3). The registry references this file; it does not copy it.
# Conftest-style: a "deny" rule set; non-empty -> fail.
package s3.public

import rego.v1

public_acls := {"public-read", "public-read-write"}

deny contains msg if {
	some name, bucket in input.resources.aws_s3_bucket
	bucket.acl in public_acls
	msg := sprintf("S3 bucket '%s' uses public ACL '%s'", [name, bucket.acl])
}
