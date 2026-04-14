# Iteration 02 Context

This iteration should improve retrieval quality without destabilizing the baseline pipeline.

Backward compatibility with the Iteration 01 CLI path should be preserved.

Iteration 02 is directly motivated by Iteration 01 manual evaluation findings:

- retrieval is too lexical
- moderate semantic overlap is missed
- lexical trap cases can cause false positives
- richer evidence is needed for downstream scoring and explanation
