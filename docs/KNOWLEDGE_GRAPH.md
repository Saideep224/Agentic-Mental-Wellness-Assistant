# Knowledge Graph Extraction & Storage

Esona builds a persistent semantic graph of the user's life entities, relationships, and emotional triggers to personalize conversational context over time.

## Graph Schema

The schema represents relationships as directed triples:

```
(Subject Entity) --[Predicate Relation]--> (Object Entity)
```

- **Subject / Object**: People (e.g. `'mother'`, `'boss'`), places (e.g. `'office'`, `'college'`), concepts (e.g. `'exams'`, `'finances'`), or coping mechanisms (e.g. `'running'`).
- **Predicate**: Clear descriptions of the connection (e.g. `'supports'`, `'causes_stress_to'`, `'enjoys'`).
- **Attributes**: Every relationship logs weight (strength), confidence, and an array of emotional tags (e.g. `['anxiety', 'sadness']`).

---

## Extraction Flow

Extraction runs in the background or during graph execution using structured LLM prompting:
1. **User Message Analysis**: The orchestrator sends the user message to the LLM with a schema template asking it to output new relationships.
2. **Entity Recognition**: The LLM extracts distinct nouns as subject/object and links them with a logical predicate.
3. **Database Storage**: Relationship records are written to `knowledge_graph` and `user_entities` tables on Supabase.
4. **Graph De-duplication**: If a relation between a subject and object already exists, the backend updates its weight and appends any new emotional attributes.

---

## Prompt Injection

When generating a response, relevant subgraphs are fetched and injected directly into the LLM system prompt:
- **Retrieval**: Queries the graph for entities mentioned in the current user message (e.g. if user mentions `'boss'`, it retrieves all triples where `'boss'` is a subject or object).
- **Format**: Formats relationships as structured list text:
  ```
  - (Boss, causes_stress_to, User) | Weight: 0.85 | Emotions: ['anxiety', 'anger']
  - (Boss, works_at, Corporate Office) | Weight: 0.90
  ```
- **Context Injection**: Placed in the chatbot system prompt under `=== USER KNOWLEDGE GRAPH ===` so the model remembers personal contexts.
