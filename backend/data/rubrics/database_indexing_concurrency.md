# Topic: Database Indexing, B+ Trees & Concurrency Control

## Senior Expectations & Architecture
Database performance relies on proper indexing and transaction isolation. Candidates must go beyond "I added an index" or "I used a transaction."

## Key Concepts Candidates Must Explain
1. **B+ Tree Mechanics & Composite Indexes:** Explain why B+ Trees excel at range queries (`O(log N)` traversal plus sequential leaf pointers) and the **Leftmost Prefix Rule** in composite indexes like `(user_id, created_at)`.
2. **Write Amplification & Selectivity:** Indexes speed up `SELECT` queries but slow down `INSERT/UPDATE/DELETE` operations because every B+ Tree index must be updated and rebalanced. Low-cardinality columns (like boolean flags) make poor standalone indexes.
3. **Race Conditions & Locking:** To prevent race conditions (e.g., double-booking), explain pessimistic locking (`SELECT ... FOR UPDATE`), optimistic concurrency control (version numbers/timestamps), and transaction isolation levels (`READ COMMITTED` vs `REPEATABLE READ` vs `SERIALIZABLE`).