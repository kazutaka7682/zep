# Graphiti User Deduplication Fix - Technical Specification

## Problem Statement

Zep creates duplicate User nodes in Neo4j via Graphiti:
1. One node when creating a user (UUID = user_id)
2. Another node when creating a session (UUID = session_id + "_" + user_id)

## Proposed Fix

### Option 1: Minimal Change - Consistent UUID (Recommended)

**File to modify**: `src/store/sessionstore_ce.go`

```go
func (dao *sessionDAO) _postCreateSession(ctx context.Context, sessionID, userID string) error {
    user, err := dao.rs.Users.Get(ctx, userID)
    if err != nil {
        return fmt.Errorf("failed to get user: %w", err)
    }
    if user == nil {
        return errors.New("user not found")
    }
    name := fmt.Sprintf("User %s %s", user.FirstName, user.LastName)
    
    // CHANGE: Use userID as UUID instead of sessionID_userID
    return graphiti.I().AddNode(ctx, graphiti.AddNodeRequest{
        GroupID: sessionID,
        UUID:    userID,  // Changed from: fmt.Sprintf("%s_%s", sessionID, userID)
        Name:    name,
        Summary: name,
    })
}
```

**Pros**:
- Minimal code change
- Reuses existing User node
- Maintains backward compatibility for new data

**Cons**:
- Existing duplicate nodes remain in database
- May need migration script for existing data

### Option 2: Skip User Node Creation for Sessions

**File to modify**: `src/store/sessionstore_ce.go`

```go
func (dao *sessionDAO) _postCreateSession(ctx context.Context, sessionID, userID string) error {
    // Remove the AddNode call entirely
    // Sessions don't need separate User nodes
    return nil
}
```

**Pros**:
- Eliminates duplicates completely
- Simplifies data model

**Cons**:
- May break assumptions about session-user relationships
- Requires testing impact on memory retrieval

### Option 3: Create Session Nodes Instead

**File to modify**: `src/store/sessionstore_ce.go`

```go
func (dao *sessionDAO) _postCreateSession(ctx context.Context, sessionID, userID string) error {
    // Create a Session node instead of User node
    return graphiti.I().AddNode(ctx, graphiti.AddNodeRequest{
        GroupID: sessionID,
        UUID:    sessionID,
        Name:    fmt.Sprintf("Session for %s", userID),
        Summary: fmt.Sprintf("Chat session %s for user %s", sessionID, userID),
        // Add node type metadata if Graphiti supports it
    })
}
```

**Pros**:
- Clear separation of entities
- Better represents actual data model

**Cons**:
- Requires Graphiti to support different node types
- May require changes to memory retrieval logic

## Implementation Plan

### Phase 1: Fix New Data (Week 1)
1. Implement Option 1 (consistent UUID)
2. Test with new users/sessions
3. Verify memory retrieval works correctly

### Phase 2: Data Migration (Week 2)
1. Create migration script to merge duplicate nodes
2. Update references to old session-user nodes
3. Clean up orphaned nodes

### Phase 3: Validation (Week 3)
1. Query Neo4j to confirm no new duplicates
2. Performance testing
3. Update documentation

## Migration Script Concept

```cypher
// Find duplicate User nodes
MATCH (u1:User), (u2:User)
WHERE u1.name = u2.name 
  AND u1.uuid <> u2.uuid
  AND u2.uuid CONTAINS '_'
RETURN u1, u2

// Merge relationships from duplicate to original
MATCH (u1:User {uuid: $original_uuid})
MATCH (u2:User {uuid: $duplicate_uuid})
MATCH (u2)-[r]->(n)
MERGE (u1)-[r2:SAME_TYPE]->(n)
SET r2 = properties(r)
DELETE r

// Delete duplicate nodes
MATCH (u:User)
WHERE u.uuid CONTAINS '_'
DELETE u
```

## Testing Strategy

### Unit Tests
```go
func TestSessionCreation_DoesNotCreateDuplicateUser(t *testing.T) {
    // 1. Create user
    // 2. Create session
    // 3. Query Graphiti for nodes with user's name
    // 4. Assert only one node exists
}
```

### Integration Tests
1. Create user and multiple sessions
2. Add messages to different sessions
3. Retrieve memory and verify facts are properly aggregated
4. Search across sessions and verify results

### Performance Tests
- Measure query performance before/after deduplication
- Test with large number of sessions per user

## Rollback Plan

If issues occur:
1. Revert code changes
2. Keep duplicate nodes (they don't break functionality)
3. Plan more comprehensive fix for next release

## Success Metrics

1. No new duplicate User nodes created
2. Memory retrieval performance unchanged or improved
3. All existing features continue working
4. Neo4j storage usage reduced by ~30-50%

## Timeline

- Day 1-2: Implement code fix
- Day 3-4: Testing
- Day 5: Deploy to staging
- Week 2: Migration script development
- Week 3: Production deployment

## Risk Assessment

- **Low Risk**: Option 1 (consistent UUID)
- **Medium Risk**: Option 2 (skip node creation)
- **High Risk**: Option 3 (different node types)

Recommendation: Start with Option 1 as the safest approach.