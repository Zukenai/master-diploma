# Iteration 03 Notes

Avoid replacing transparency with opaque learned heuristics unless evaluation clearly justifies the tradeoff.

This iteration should improve decision quality, not just retrieval diversity. The main risk is overfitting to the toy corpus while pretending to have a general scholarly evaluator.

Post-implementation note:

- claim-aware and facet-aware scoring signals are now present
- manual cases can now be compared repeatably across sparse, dense, and hybrid modes
- the toy corpus still makes several cases look too risky, which is a real limitation and should be treated as motivation for a stronger scholarly setup rather than hidden
