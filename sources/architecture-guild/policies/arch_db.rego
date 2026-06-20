# Enforces a relationship-style architectural constraint over an architecture
# graph artifact: deny any data-access edge that crosses a domain boundary.
package arch.db

import rego.v1

deny contains msg if {
	some edge in input.edges
	edge.type == "data-access"
	edge.from_domain != edge.to_domain
	msg := sprintf(
		"service '%s' (%s) directly accesses '%s' in domain '%s'",
		[edge.from, edge.from_domain, edge.to, edge.to_domain],
	)
}
