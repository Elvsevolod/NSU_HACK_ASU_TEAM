# Legacy order oracle v3 delta

Historical legacy-v2 bytes stay unchanged. OwnerResource.findAll (Petclinic source lines 76–78) delegates to inherited OwnerRepository.findAll without ORDER BY or Sort. After creating Eva there are two rows. Step 5, “Read first owner”, therefore cannot establish ownerId=1 from SQL storage order.

Current bounded NL behavior keeps ownerId, URL scalar and response unresolved and explicitly diagnoses the missing input. It does not enumerate browser row permutations. The v3 checker requires this honest unresolved result; known 1, an arbitrary generated ID, or a concrete response fails. All existing identity, generated value, mutation, state, wire, HTTP status, binding rejection and E/C/R/D checks on the other six steps are retained. PiggyMetrics expectations are unchanged. The small legacy graph remains exact against v2, but this is not a claim of complete branch-sensitive ground truth for unknown repository arguments.

The historical v2 state checker fails on this deliberately corrected ordinal; v3 is a source-based oracle change, not evidence that v2 passed. No input, source, scenario or historical oracle was edited.
