# Zep Client SDK Interfaces

## 概要

Zep Python SDKは、Zepメモリサービスとやり取りするための同期（`Zep`）および非同期（`AsyncZep`）クライアントを提供します。SDKは主に2つの機能領域に整理されています：

1. **ユーザー管理** (`zep.user`)
2. **メモリ管理** (`zep.memory`)

## クライアント初期化

### AsyncZep クライアント（テストで主に使用）

```python
from zep_python.client import AsyncZep

zep = AsyncZep(
    api_key="your_api_key",
    base_url="http://localhost:8000"  # またはZepインスタンスのURL
)
```

### 同期 Zep クライアント

```python
from zep_python.client import Zep

zep = Zep(
    api_key="your_api_key",
    base_url="http://localhost:8000"
)
```

## 1. ユーザー管理インターフェース (`zep.user`)

### 利用可能なメソッド

#### `zep.user.add()`
**目的**: 新しいユーザーを作成
**メソッドシグネチャ**:
```python
async def add(
    *,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> User
```

**使用例**:
```python
user = await zep.user.add(
    user_id="yamada.taro_1234",
    email="yamada.taro@example.com",
    first_name="太郎",
    last_name="山田",
    metadata={
        "gender": "male",
        "age": 30,
        "created_at": datetime.now().isoformat(),
        "app": "zep-chat-test"
    }
)
```

#### `zep.user.get(user_id)`
**目的**: IDでユーザーを取得
**メソッドシグネチャ**:
```python
async def get(user_id: str) -> User
```

**使用例**:
```python
user = await zep.user.get("yamada.taro_1234")
print(f"ユーザー名: {user.first_name} {user.last_name}")
```

#### `zep.user.update(user_id, **kwargs)`
**目的**: ユーザー情報を更新
**メソッドシグネチャ**:
```python
async def update(
    user_id: str,
    *,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> User
```

**使用例**:
```python
updated_user = await zep.user.update(
    "yamada.taro_1234",
    email="new.email@example.com",
    metadata={"age": 31}
)
```

#### `zep.user.delete(user_id)`
**目的**: ユーザーを削除
**メソッドシグネチャ**:
```python
async def delete(user_id: str) -> SuccessResponse
```

#### `zep.user.list_ordered()`
**目的**: ページネーション付きでユーザー一覧を取得
**メソッドシグネチャ**:
```python
async def list_ordered(
    *,
    page_number: Optional[int] = None,
    page_size: Optional[int] = None
) -> UserListResponse
```

**使用例**:
```python
users_response = await zep.user.list_ordered(
    page_number=1,
    page_size=10
)
for user in users_response.users:
    print(f"{user.user_id}: {user.first_name} {user.last_name}")
```

#### `zep.user.get_sessions(user_id)`
**目的**: ユーザーの全セッションを取得
**メソッドシグネチャ**:
```python
async def get_sessions(user_id: str) -> List[List[Session]]
```

## 2. メモリ管理インターフェース (`zep.memory`)

### セッション管理

#### `zep.memory.add_session()`
**目的**: 新しいセッションを作成
**メソッドシグネチャ**:
```python
async def add_session(
    *,
    session_id: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    fact_rating_instruction: Optional[FactRatingInstruction] = None
) -> Session
```

**使用例**:
```python
session = await zep.memory.add_session(
    session_id="session_123",
    user_id="yamada.taro_1234",
    metadata={
        "session_type": "chat_test",
        "start_time": datetime.now().isoformat()
    }
)
```

#### `zep.memory.get_session(session_id)`
**目的**: セッション詳細を取得
**メソッドシグネチャ**:
```python
async def get_session(session_id: str) -> Session
```

#### `zep.memory.update_session(session_id, **kwargs)`
**目的**: セッションメタデータを更新
**メソッドシグネチャ**:
```python
async def update_session(
    session_id: str,
    *,
    metadata: Dict[str, Any],
    fact_rating_instruction: Optional[FactRatingInstruction] = None
) -> Session
```

#### `zep.memory.list_sessions()`
**目的**: ページネーション付きでセッション一覧を取得
**メソッドシグネチャ**:
```python
async def list_sessions(
    *,
    page_number: Optional[int] = None,
    page_size: Optional[int] = None,
    order_by: Optional[str] = None,
    asc: Optional[bool] = None
) -> SessionListResponse
```

### メモリ操作

#### `zep.memory.add()`
**目的**: セッションメモリにメッセージを追加
**メソッドシグネチャ**:
```python
async def add(
    session_id: str,
    *,
    messages: Sequence[Message],
    fact_instruction: Optional[str] = None,
    summary_instruction: Optional[str] = None
) -> SuccessResponse
```

**使用例**:
```python
from zep_python.types import Message

await zep.memory.add(
    session_id="session_123",
    messages=[
        Message(
            role="Taka",
            content="私はラーメンが好きです",
            role_type="user",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "input_length": len("私はラーメンが好きです")
            }
        ),
        Message(
            role="AI Assistant",
            content="ラーメンがお好きなんですね！どんな種類がお好みですか？",
            role_type="assistant",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "response_length": len("ラーメンがお好きなんですね！どんな種類がお好みですか？")
            }
        )
    ]
)
```

#### `zep.memory.get()`
**目的**: セッションメモリを取得（メッセージ、ファクト、要約）
**メソッドシグネチャ**:
```python
async def get(
    session_id: str,
    *,
    lastn: Optional[int] = None,
    min_rating: Optional[float] = None
) -> Memory
```

**使用例**:
```python
memory = await zep.memory.get(
    session_id="session_123",
    lastn=6  # 直近6件のメッセージを取得
)

# メモリコンポーネントにアクセス
messages = memory.messages  # List[Message]
relevant_facts = memory.relevant_facts  # List[Fact]
summary = memory.summary  # Summary オブジェクト

# ファクトの表示
for fact in relevant_facts:
    print(f"ファクト: {fact.fact} (評価: {fact.rating})")
```

#### `zep.memory.delete(session_id)`
**目的**: セッションメモリを削除
**メソッドシグネチャ**:
```python
async def delete(session_id: str) -> SuccessResponse
```

### メモリ検索

#### `zep.memory.search_sessions()`
**目的**: セッション間で関連メモリを検索
**メソッドシグネチャ**:
```python
async def search_sessions(
    *,
    user_id: Optional[str] = None,
    session_ids: Optional[Sequence[str]] = None,
    text: Optional[str] = None,
    search_scope: Optional[SearchScope] = None,
    search_type: Optional[SearchType] = None,
    limit: Optional[int] = None,
    min_fact_rating: Optional[float] = None,
    min_score: Optional[float] = None,
    mmr_lambda: Optional[float] = None,
    record_filter: Optional[Dict[str, Any]] = None
) -> SessionSearchResponse
```

**使用例**:
```python
search_response = await zep.memory.search_sessions(
    user_id="yamada.taro_1234",
    search_scope="facts",
    text="趣味は何？",
    limit=5
)

# 検索結果にアクセス
print("関連するファクト:")
for result in search_response.results:
    if hasattr(result, 'fact'):
        print(f"- {result.fact.fact} (スコア: {result.score})")
```

### メッセージ操作

#### `zep.memory.get_session_messages()`
**目的**: ページネーション付きでセッションからメッセージを取得
**メソッドシグネチャ**:
```python
async def get_session_messages(
    session_id: str,
    *,
    limit: Optional[int] = None,
    cursor: Optional[int] = None
) -> MessageListResponse
```

**使用例**:
```python
messages_response = await zep.memory.get_session_messages(
    session_id="session_123",
    limit=10
)

for message in messages_response.messages:
    print(f"{message.role}: {message.content}")
```

#### `zep.memory.get_session_message()`
**目的**: 特定のメッセージを取得
**メソッドシグネチャ**:
```python
async def get_session_message(
    session_id: str,
    message_uuid: str
) -> Message
```

#### `zep.memory.update_message_metadata()`
**目的**: メッセージメタデータを更新
**メソッドシグネチャ**:
```python
async def update_message_metadata(
    session_id: str,
    message_uuid: str,
    *,
    metadata: Dict[str, Any]
) -> Message
```

### ファクト操作

#### `zep.memory.get_fact(fact_uuid)`
**目的**: 特定のファクトを取得
**メソッドシグネチャ**:
```python
async def get_fact(fact_uuid: str) -> FactResponse
```

#### `zep.memory.delete_fact(fact_uuid)`
**目的**: ファクトを削除
**メソッドシグネチャ**:
```python
async def delete_fact(fact_uuid: str) -> str
```

## 3. 主要データ型

### Message
```python
class Message:
    content: Optional[str]              # メッセージ内容
    role: Optional[str]                 # 役割名（例: "user", "assistant"）
    role_type: Optional[RoleType]       # 役割タイプ: "user", "assistant", "system"
    metadata: Optional[Dict[str, Any]]  # メタデータ
    created_at: Optional[str]           # 作成日時
    updated_at: Optional[str]           # 更新日時
    uuid_: Optional[str]                # UUID
    token_count: Optional[int]          # トークン数
```

### Memory
```python
class Memory:
    messages: Optional[List[Message]]        # メッセージリスト
    relevant_facts: Optional[List[Fact]]     # 関連ファクト
    facts: Optional[List[str]]               # ファクト（非推奨）
    summary: Optional[Summary]               # 要約
    metadata: Optional[Dict[str, Any]]       # メタデータ
```

### Fact
```python
class Fact:
    fact: Optional[str]                 # ファクト内容
    rating: Optional[float]             # 評価スコア
    uuid_: Optional[str]                # UUID
    created_at: Optional[str]           # 作成日時
```

### User
```python
class User:
    user_id: Optional[str]              # ユーザーID
    email: Optional[str]                # メールアドレス
    first_name: Optional[str]           # 名前
    last_name: Optional[str]            # 姓
    metadata: Optional[Dict[str, Any]]  # メタデータ
    created_at: Optional[str]           # 作成日時
    updated_at: Optional[str]           # 更新日時
    uuid_: Optional[str]                # UUID
    session_count: Optional[int]        # セッション数
```

## 4. 機能別インターフェース分類

### ユーザー管理
- `zep.user.add()` - ユーザー作成
- `zep.user.get()` - ユーザー情報取得
- `zep.user.update()` - ユーザー情報更新
- `zep.user.delete()` - ユーザー削除
- `zep.user.list_ordered()` - ページネーション付きユーザー一覧
- `zep.user.get_sessions()` - ユーザーのセッション取得

### セッション管理
- `zep.memory.add_session()` - セッション作成
- `zep.memory.get_session()` - セッション詳細取得
- `zep.memory.update_session()` - セッションメタデータ更新
- `zep.memory.list_sessions()` - ページネーション付きセッション一覧

### 会話メモリ
- `zep.memory.add()` - 会話メッセージ保存
- `zep.memory.get()` - 会話メモリ取得
- `zep.memory.delete()` - セッションメモリ削除

### メッセージ操作
- `zep.memory.get_session_messages()` - ページネーション付きメッセージ取得
- `zep.memory.get_session_message()` - 特定メッセージ取得
- `zep.memory.update_message_metadata()` - メッセージメタデータ更新

### メモリ検索・取得
- `zep.memory.search_sessions()` - セッション間検索
- `zep.memory.get_fact()` - 特定ファクト取得
- `zep.memory.delete_fact()` - ファクト削除

## 5. 一般的な使用パターン

### 基本的なチャットアプリケーションフロー

```python
import asyncio
from datetime import datetime
from zep_python.client import AsyncZep
from zep_python.types import Message

async def chat_application_example():
    # 1. クライアント初期化
    zep = AsyncZep(
        api_key="zep_api_secret",
        base_url="http://localhost:8000"
    )
    
    # 2. ユーザー作成
    user = await zep.user.add(
        user_id="user_123",
        email="user@example.com",
        first_name="太郎",
        last_name="田中"
    )
    
    # 3. セッション作成
    session = await zep.memory.add_session(
        session_id="session_456",
        user_id=user.user_id
    )
    
    # 4. 会話追加
    await zep.memory.add(
        session_id=session.session_id,
        messages=[
            Message(
                role="user",
                content="私はプログラマーです",
                role_type="user"
            ),
            Message(
                role="assistant",
                content="プログラマーでいらっしゃるんですね！",
                role_type="assistant"
            )
        ]
    )
    
    # 5. メモリ取得
    memory = await zep.memory.get(session_id=session.session_id)
    
    # 6. ファクト表示
    for fact in memory.relevant_facts:
        print(f"抽出されたファクト: {fact.fact}")
    
    # 7. 検索実行
    search_results = await zep.memory.search_sessions(
        user_id=user.user_id,
        text="職業",
        search_scope="facts"
    )
    
    for result in search_results.results:
        print(f"検索結果: {result.fact.fact}")

# 実行
asyncio.run(chat_application_example())
```

### エラーハンドリング

SDKは特定の例外を発生させます：
- `BadRequestError` (400)
- `NotFoundError` (404)
- `ConflictError` (409)
- `InternalServerError` (500)
- `ApiError` (一般的なAPIエラー)

```python
from zep_python.exceptions import NotFoundError, BadRequestError

try:
    user = await zep.user.get("non_existent_user")
except NotFoundError:
    print("ユーザーが見つかりません")
except BadRequestError:
    print("不正なリクエストです")
```

### ベストプラクティス

1. **メタデータの活用**: コンテキスト情報をmetadataフィールドに保存
2. **メッセージ構造**: 一貫したroleとrole_type値を使用
3. **メモリ取得**: `lastn`パラメータで直近メッセージ数を制限
4. **検索スコープ**: セマンティック検索には"facts"スコープを使用
5. **非同期パターン**: すべての操作で適切なasync/awaitパターンを使用
6. **リトライ機能**: メモリ保存後は適切な待機時間を設けて取得

### 高度な使用例

```python
async def advanced_memory_management():
    # キャッシュ機能付きメモリ取得
    memory_cache = {}
    
    def get_cached_memory(session_id):
        if session_id in memory_cache:
            return memory_cache[session_id]
        return None
    
    async def get_memory_with_cache(session_id, force_refresh=False):
        if not force_refresh:
            cached = get_cached_memory(session_id)
            if cached:
                return cached
        
        memory = await zep.memory.get(session_id=session_id)
        memory_cache[session_id] = memory
        return memory
    
    # 関連度別ファクト分類
    memory = await get_memory_with_cache("session_123")
    
    high_relevance_facts = [
        f.fact for f in memory.relevant_facts 
        if f.rating and f.rating > 0.8
    ]
    
    medium_relevance_facts = [
        f.fact for f in memory.relevant_facts 
        if f.rating and 0.5 < f.rating <= 0.8
    ]
    
    print("高関連度ファクト:", high_relevance_facts)
    print("中関連度ファクト:", medium_relevance_facts)
```

この包括的なインターフェース分析により、Zepは会話型AIアプリケーションにおける長期記憶管理のための充実したSDKを提供し、堅牢なユーザー管理、セッション処理、セマンティック検索機能を備えていることがわかります。