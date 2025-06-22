# Graphiti重複Userエンティティ問題の詳細分析

## 概要

ZepとGraphitiの統合において、Neo4jデータベース内に同一ユーザーに対して複数のUserエンティティが作成される現象が発生します。本ドキュメントでは、この現象の詳細なメカニズムと、Graphiti側の動作を中心に解説します。

## 問題の具体例

RAGアプリケーションで1人のユーザーが1回質問しただけで、Neo4jに以下の2つのUserエンティティが作成されました：

```
1. UUID: "8d02d9b38cc24081ad5688e3fdb1bc18" 
   作成時刻: 2025-06-22T08:06:05.965343

2. UUID: "3b2c37383d7a4ebf89924fe5a265543a_8d02d9b38cc24081ad5688e3fdb1bc18"
   作成時刻: 2025-06-22T08:06:08.596017
```

## 詳細な動作フロー

### 1. ユーザー作成時の動作

#### 1.1 Zep側の処理
```python
# アプリケーションコード
user = await zep.user.add(
    user_id=self.user_id,  # 例: "8d02d9b38cc24081ad5688e3fdb1bc18"
    metadata={
        "system": "meiji-rag",
        "created_at": datetime.now().isoformat(),
    }
)
```

#### 1.2 ZepからGraphitiへのAPI呼び出し
```go
// userstore_ce.go:12-20
func (us *userStore) _processCreatedUser(ctx context.Context, user *models.User) error {
    err := graphiti.I().AddNode(ctx, graphiti.AddNodeRequest{
        GroupID: user.UserID,  // "8d02d9b38cc24081ad5688e3fdb1bc18"
        UUID:    user.UserID,  // "8d02d9b38cc24081ad5688e3fdb1bc18"
        Name:    fmt.Sprintf("User %s %s", user.FirstName, user.LastName),
        Summary: fmt.Sprintf("User %s %s", user.FirstName, user.LastName),
    })
    return err
}
```

#### 1.3 Graphiti内部での処理

Graphitiは`POST /entity-node`エンドポイントでリクエストを受信し、以下の処理を実行：

1. **エンティティノードの作成**
   - `group_id`: "8d02d9b38cc24081ad5688e3fdb1bc18"
   - `uuid`: "8d02d9b38cc24081ad5688e3fdb1bc18"
   - `name`: "User  " (名前が空の場合)
   - ラベル: `Entity`

2. **Neo4jへのCypherクエリ実行**
   ```cypher
   CREATE (n:Entity {
       uuid: "8d02d9b38cc24081ad5688e3fdb1bc18",
       group_id: "8d02d9b38cc24081ad5688e3fdb1bc18",
       name: "User  ",
       summary: "User  ",
       created_at: datetime()
   })
   ```

### 2. セッション作成時の動作

#### 2.1 Zep側の処理
```python
# アプリケーションコード
session = await zep.memory.add_session(
    session_id=self.session_id,  # 例: "3b2c37383d7a4ebf89924fe5a265543a"
    user_id=self.user_id,
    metadata={
        "type": "interactive_rag_session",
        "start_time": datetime.now().isoformat(),
    }
)
```

#### 2.2 ZepからGraphitiへのAPI呼び出し（問題の発生箇所）
```go
// sessionstore_ce.go:21-34
func (ss *sessionStore) _processCreatedSession(ctx context.Context, session *models.Session) error {
    if session.UserID == nil {
        return nil
    }
    
    // ここで複合UUIDが生成される！
    err := graphiti.I().AddNode(ctx, graphiti.AddNodeRequest{
        GroupID: session.SessionID,  // "3b2c37383d7a4ebf89924fe5a265543a"
        UUID:    fmt.Sprintf("%s_%s", session.SessionID, *session.UserID),  // 複合UUID
        Name:    fmt.Sprintf("User %s %s", session.User.FirstName, session.User.LastName),
        Summary: fmt.Sprintf("User %s %s", session.User.FirstName, session.User.LastName),
    })
    return err
}
```

#### 2.3 Graphiti内部での処理

1. **2つ目のエンティティノードの作成**
   - `group_id`: "3b2c37383d7a4ebf89924fe5a265543a" (セッションID)
   - `uuid`: "3b2c37383d7a4ebf89924fe5a265543a_8d02d9b38cc24081ad5688e3fdb1bc18" (複合UUID)
   - `name`: "User  "
   - ラベル: `Entity`

2. **Neo4jへのCypherクエリ実行**
   ```cypher
   CREATE (n:Entity {
       uuid: "3b2c37383d7a4ebf89924fe5a265543a_8d02d9b38cc24081ad5688e3fdb1bc18",
       group_id: "3b2c37383d7a4ebf89924fe5a265543a",
       name: "User  ",
       summary: "User  ",
       created_at: datetime()
   })
   ```

### 3. メッセージ追加時の動作

#### 3.1 メモリ初期化処理
```go
// memory_ce.go:59-72
func (dao *memoryDAO) _initializeProcessingMemory(
    ctx context.Context,
    session *models.Session,
    memoryMessages *models.Memory,
) error {
    // セッション用のメッセージ処理
    err := graphiti.I().PutMemory(ctx, session.SessionID, memoryMessages.Messages, true)
    if err != nil {
        return err
    }
    
    // ユーザー用のメッセージ処理（クロスセッション記憶のため）
    if session.UserID != nil {
        err = graphiti.I().PutMemory(ctx, *session.UserID, memoryMessages.Messages, true)
    }
    return err
}
```

#### 3.2 GraphitiのPutMemory処理
```go
// service_ce.go:183-196
func (s *service) PutMemory(ctx context.Context, groupID string, messages []models.Message, addGroupIDPrefix bool) error {
    var graphitiMessages []Message
    for _, m := range messages {
        episodeUUID := m.UUID.String()
        if addGroupIDPrefix {
            // グループIDプレフィックスを追加
            episodeUUID = fmt.Sprintf("%s-%s", groupID, m.UUID)
        }
        graphitiMessages = append(graphitiMessages, Message{
            UUID:      episodeUUID,
            GroupID:   groupID,
            Content:   m.Content,
            Role:      m.Role,
            CreatedAt: m.CreatedAt,
        })
    }
    // GraphitiのPOST /messagesエンドポイントを呼び出し
    return s.postMessages(ctx, graphitiMessages)
}
```

## Graphiti内部のエンティティ管理

### エンティティ解決ロジック

Graphitiは以下のロジックでエンティティを管理します：

1. **エンティティの一意性**: `uuid`フィールドで判定
2. **グループ化**: `group_id`でエンティティをグループ化
3. **重複排除**: 同じ`uuid`のエンティティは作成されない

### 問題の核心

**異なるUUIDが使用されるため、Graphitiは別のエンティティとして認識します：**

- ユーザー作成時: `UUID = user_id`
- セッション作成時: `UUID = session_id + "_" + user_id`

これにより、同じユーザーに対して2つの異なるエンティティノードが作成されます。

## Neo4jでのグラフ構造

### 結果として生成されるグラフ

```
[Entity: User (uuid: 8d02d9...)]
         |
         | (作成されるが関連付けなし)
         |
[Entity: User (uuid: 3b2c3738...8d02d9...)]
         |
         | HAS_EPISODE
         |
[Episodic: Message nodes]
```

### 影響

1. **ストレージの無駄**: 同一ユーザーに対して複数のノードが存在
2. **クエリの複雑化**: ユーザー情報を取得する際に複数のノードを考慮する必要
3. **知識グラフの不整合**: 本来1つであるべきエンティティが分散

## 設計意図の推測

この動作は以下の理由で意図的な可能性があります：

1. **セッションスコープのエンティティ**: セッション固有のユーザー状態を表現
2. **グループ分離**: セッションとユーザーレベルで異なるグループ化
3. **将来の拡張性**: セッション固有の属性を持つユーザーエンティティ

ただし、現在の実装では同じ内容のエンティティが重複しているため、最適化の余地があります。

## 推奨される対応

### オプション1: UUID生成ロジックの統一
```go
// sessionstore_ce.go の修正案
UUID: *session.UserID,  // 複合UUIDではなく、userIDを使用
```

### オプション2: エンティティ参照の実装
既存のUserエンティティを参照する関係性を作成し、新規ノードは作成しない。

### オプション3: Graphiti側での重複排除
Graphitiで同一エンティティの異なる表現を認識し、統合するロジックを実装。

## まとめ

Graphitiにおける重複Userエンティティの作成は、ZepとGraphiti間でのUUID生成ロジックの不一致が原因です。セッション作成時に複合UUID（`session_id + "_" + user_id`）を使用することで、Graphitiは新しいエンティティとして認識し、重複が発生します。この問題は設計レベルでの調整により解決可能です。