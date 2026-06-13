"""Spatial enrichment domain (WP-G).

Synthesises engine-consumable ``PropertyFact`` rows from a project's resolved
parcel and intersecting planning features, with no drawing upload required.
"""

from draftcheck.domain.spatial.synth_facts import synth_property_facts

__all__ = ["synth_property_facts"]
