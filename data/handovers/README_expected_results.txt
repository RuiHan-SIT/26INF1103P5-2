HANDOVER TEST CASES - EXPECTED RESULTS

01 Complete: complete; 2 outstanding, 0 BAU, 1 information entry.
02 Missing owner: incomplete; 1 outstanding with owners=[].
03 Missing deadline: incomplete; 1 outstanding with deadline="".
04 Multiple errors: incomplete; 3 outstanding, missing owners/deadlines/description depending on extraction.
05 BAU only: complete; 0 outstanding, 2 BAU with owners.
06 Information only: incomplete; 0 outstanding, 0 BAU, information entries.
07 Invalid date: incomplete; 1 outstanding, deadline 31/02/2027 should be rejected.
08 Mixed tasks: complete; 2 outstanding, 1 BAU, 1 information entry.

These are intended outputs, not guaranteed LLM behaviour. Review classification and extraction.
Your current Logic Manager treats BAU-only handovers as complete and no-task handovers as incomplete.
