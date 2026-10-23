# Topic: React & Redux Toolkit State Optimization

## Senior Expectations & Architecture
When managing global state in Redux Toolkit (RTK), using `useSelector` naively can cause severe re-render bottlenecks. `useSelector` runs after every dispatched action and forces a component re-render if the returned reference changes (`===` strict reference equality).

## Key Concepts Candidates Must Explain
1. **Reference Equality Trap:** Returning a new array or object literal inside `useSelector` (such as `.filter()` or `.map()`) creates a new memory reference every time, triggering unnecessary re-renders.
2. **Memoized Selectors (`createSelector` / Reselect):** Candidates should explain using `createSelector` to memoize derived data so recalculation only happens when input state slices actually change.
3. **State Normalization (`createEntityAdapter`):** Storing posts as `{ ids: [], entities: { id: post } }` allows individual `PostItem` components to select by ID (`state.posts.entities[postId]`), ensuring an edit to Post A never re-renders Post B.