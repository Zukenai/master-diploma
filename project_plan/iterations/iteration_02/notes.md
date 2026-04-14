# Iteration 02 Notes

Priority should stay on architecture quality and retrieval extensibility, not on adding unrelated product surface.

The main risk is building too much evaluation or thesis-polish logic too early. This iteration should stay focused on retrieval quality and evidence richness.

Post-implementation note:

- sparse, dense, and hybrid retrieval paths now exist
- hybrid retrieval improves recall for overlap-heavy cases on the toy corpus
- lexical trap and far-case behavior are still imperfect, which confirms that Iteration 03 still needs stronger evidence logic and evaluation
