# Iteration 04 Notes

This iteration should not drift into product work or final thesis polish.

The main risk is mixing:

- core experimental work
- final packaging and chapter formatting

Only the first belongs here.

Post-implementation note:

- the curated corpus is now acquired from public metadata offline and frozen locally
- sparse, dense, and hybrid comparisons run on the curated setup
- retrieval and verdict observations are now separated in experiment outputs
- the current setup is thesis-grade in structure, but still small and not yet the final polished thesis package

Final constrained pass note:

- this pass strengthens curated controls and calibrates verdict behavior without changing the architecture
- the intent is to remove the last obvious collapse behavior on the curated setup
- after this pass, the project should move to thesis-oriented packaging rather than more core logic work
- dense and hybrid no longer collapse the shared legacy curated cases into uniformly high-risk verdicts
- one lexical-stress control still remains slightly elevated for dense and hybrid, and this should be treated as a documented limitation rather than a reason for more architecture work
