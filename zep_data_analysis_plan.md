# Zep Community Edition データ分析調査計画

## 概要

本文書は、Zep Community Editionのデータ管理特性とスケーリング能力を調査するための包括的な分析計画です。以下の3つの主要な調査項目について、詳細な調査方法、実行計画、予想される結果をまとめています。

### 調査項目
1. **データ量とスケーリング特性の調査**
2. **データ削除による整合性への影響調査**
3. **データ分類と保存戦略の分析**

---

## 1. データ量とスケーリング特性の調査

### 1.1 調査目的

- チャットボットシステムにおける1ユーザーあたりのデータ増加量を定量化
- スケール時のデータ増加パターンとリソース消費を分析
- 無限にデータが増加し続ける問題の有無と対策を検証

### 1.2 調査の背景

Zepは以下の2つのデータストアを使用しているため、それぞれでのデータ増加パターンが異なる可能性があります：
- **PostgreSQL**: 構造化されたチャット履歴（線形増加）
- **Neo4j**: ナレッジグラフ（ネットワーク効果による非線形増加の可能性）

### 1.3 詳細調査計画

#### ステップ1: ベースライン測定環境の構築

**目的**: 測定用の専用環境を構築し、正確なデータサイズ変化を追跡

**実装方法**:
```python
# baseline_measurement.py
import asyncio
import psutil
import docker
import psycopg2
from zep_python.client import AsyncZep
import pandas as pd
from datetime import datetime

class ZepDataAnalyzer:
    def __init__(self):
        self.zep_client = AsyncZep(
            api_key="zep_api_secret",
            base_url="http://localhost:8000"
        )
        self.postgres_conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="postgres",
            user="postgres",
            password="postgres"
        )
        self.results = []
    
    async def measure_baseline(self):
        """初期状態のデータサイズを測定"""
        pg_sizes = self._get_postgres_sizes()
        neo4j_stats = self._get_neo4j_stats()
        memory_usage = self._get_memory_usage()
        
        baseline = {
            'timestamp': datetime.now(),
            'postgres_sizes': pg_sizes,
            'neo4j_stats': neo4j_stats,
            'memory_usage': memory_usage,
            'user_count': 0,
            'session_count': 0,
            'message_count': 0
        }
        
        self.results.append(baseline)
        return baseline
    
    def _get_postgres_sizes(self):
        """PostgreSQLテーブルサイズを取得"""
        with self.postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size_pretty,
                    pg_total_relation_size('public.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'sessions', 'messages');
            """)
            return dict(cur.fetchall())
    
    def _get_neo4j_stats(self):
        """Neo4jのノード・関係数を取得"""
        # Neo4j REST APIまたはcypher-shellを使用
        # docker exec経由でクエリを実行
        pass
    
    def _get_memory_usage(self):
        """システムメモリ使用量を取得"""
        docker_client = docker.from_env()
        containers = ['zep-ce-zep-1', 'zep-ce-postgres', 'zep-ce-neo4j-1', 'zep-ce-graphiti-1']
        
        usage = {}
        for container_name in containers:
            container = docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            usage[container_name] = {
                'memory_usage': stats['memory_stats']['usage'],
                'memory_limit': stats['memory_stats']['limit'],
                'cpu_usage': stats['cpu_stats']['cpu_usage']['total_usage']
            }
        
        return usage
```

#### ステップ2: 段階的データ投入テスト

**目的**: 様々な使用パターンでのデータ増加量を測定

**テストシナリオ**:

| シナリオ | ユーザー数 | セッション/ユーザー | メッセージ/セッション | 想定ケース |
|----------|------------|---------------------|----------------------|------------|
| 軽量使用 | 10 | 1 | 10 | 初期ユーザー、短い質問 |
| 標準使用 | 100 | 5 | 50 | 一般的な使用パターン |
| 重量使用 | 1000 | 10 | 100 | ヘビーユーザー |
| 長期使用 | 100 | 50 | 500 | 長期間の継続使用 |
| 深い会話 | 10 | 1 | 1000 | 非常に長いセッション |

**実装**:
```python
async def run_data_volume_test():
    """段階的データ投入テスト"""
    scenarios = [
        {'name': '軽量使用', 'users': 10, 'sessions_per_user': 1, 'messages_per_session': 10},
        {'name': '標準使用', 'users': 100, 'sessions_per_user': 5, 'messages_per_session': 50},
        {'name': '重量使用', 'users': 1000, 'sessions_per_user': 10, 'messages_per_session': 100},
        {'name': '長期使用', 'users': 100, 'sessions_per_user': 50, 'messages_per_session': 500},
        {'name': '深い会話', 'users': 10, 'sessions_per_user': 1, 'messages_per_session': 1000},
    ]
    
    analyzer = ZepDataAnalyzer()
    await analyzer.measure_baseline()
    
    for scenario in scenarios:
        print(f"実行中: {scenario['name']}")
        
        # データ投入前測定
        before = await analyzer.measure_current_state()
        
        # データ投入
        await analyzer.inject_test_data(
            users=scenario['users'],
            sessions_per_user=scenario['sessions_per_user'],
            messages_per_session=scenario['messages_per_session']
        )
        
        # データ投入後測定
        after = await analyzer.measure_current_state()
        
        # 結果分析
        growth = analyzer.calculate_growth(before, after)
        print(f"データ増加量: {growth}")
        
        # 待機時間（ナレッジグラフ構築完了を待つ）
        await asyncio.sleep(30)
```

#### ステップ3: データ増加パターンの分析

**分析項目**:
1. **線形増加要素**:
   - メッセージ数とPostgreSQLサイズの関係
   - ユーザー数とベースデータサイズの関係

2. **非線形増加要素**:
   - エンティティ数とNeo4jノード数の関係
   - 関係性の複雑化によるエッジ増加
   - エンベディングベクトルのメモリ使用量

3. **リソース消費パターン**:
   - CPU使用量（Graphiti処理）
   - メモリ使用量（LLM推論、エンベディング）
   - ディスクI/O（データベース書き込み）

**実装**:
```python
def analyze_growth_patterns(results):
    """データ増加パターンを分析"""
    df = pd.DataFrame(results)
    
    # 線形関係の分析
    message_count = df['message_count']
    postgres_size = df['postgres_sizes'].apply(lambda x: x.get('messages', 0))
    
    # 相関分析
    correlation = message_count.corr(postgres_size)
    print(f"メッセージ数とPostgreSQLサイズの相関: {correlation}")
    
    # 成長率分析
    growth_rates = []
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        
        message_growth = (curr['message_count'] - prev['message_count']) / prev['message_count']
        size_growth = (curr['total_size'] - prev['total_size']) / prev['total_size']
        
        growth_rates.append({
            'message_growth': message_growth,
            'size_growth': size_growth,
            'efficiency': message_growth / size_growth if size_growth > 0 else 0
        })
    
    return growth_rates
```

#### ステップ4: スケーリング限界の調査

**目的**: システムの実用的な限界を特定

**調査ポイント**:
1. **パフォーマンス劣化ポイント**
   - レスポンス時間の増加
   - メモリ不足の発生
   - CPU使用率の上昇

2. **データベース制約**
   - PostgreSQLのテーブルサイズ制限
   - Neo4jのノード・エッジ数制限
   - インデックス効率の低下

**実装**:
```python
async def test_scaling_limits():
    """スケーリング限界テスト"""
    limits_test = [
        {'users': 1000, 'sessions': 10000, 'messages': 100000},
        {'users': 5000, 'sessions': 50000, 'messages': 500000},
        {'users': 10000, 'sessions': 100000, 'messages': 1000000},
    ]
    
    for test in limits_test:
        try:
            start_time = time.time()
            
            # データ投入
            await inject_large_dataset(test)
            
            # パフォーマンステスト
            response_times = await measure_api_performance()
            
            # リソース使用量測定
            resource_usage = measure_resource_usage()
            
            end_time = time.time()
            
            results = {
                'test_config': test,
                'processing_time': end_time - start_time,
                'response_times': response_times,
                'resource_usage': resource_usage,
                'success': True
            }
            
        except Exception as e:
            results = {
                'test_config': test,
                'error': str(e),
                'success': False
            }
        
        print(f"スケーリングテスト結果: {results}")
```

### 1.4 予想される結果と分析

#### データ増加の予想パターン

1. **PostgreSQL（線形増加）**:
   - メッセージあたり約500-1000バイト
   - 1000メッセージ/日のユーザーで約1MB/日
   - 年間約365MB/ユーザー

2. **Neo4j（対数的増加）**:
   - 初期は急速に増加（新しいエンティティが多い）
   - 時間経過とともに増加率は低下（既存エンティティの再利用）
   - ユーザーあたり100-1000ノード、200-5000エッジ

3. **メモリ使用量**:
   - エンベディングベクトル: 1536次元 × 4バイト = 6KB/エンティティ
   - LLM推論時の一時メモリ: 2-4GB

#### スケーリング課題の予想

1. **無限増加の問題**:
   - チャット履歴は無制限に増加
   - ナレッジグラフは収束する可能性
   - 定期的なデータアーカイブが必要

2. **パフォーマンス劣化**:
   - 100万メッセージ超でクエリ速度低下
   - メモリ不足によるスワップ発生
   - インデックス再構築の必要性

---

## 2. データ削除による整合性への影響調査

### 2.1 調査目的

- PostgreSQLとNeo4jのデータ削除が記憶機能に与える影響を検証
- 安全に削除可能なデータの種類と量を特定
- データ削除戦略の最適化指針を策定

### 2.2 調査の背景

Zepのハイブリッドアーキテクチャでは、以下の依存関係が存在します：
- **PostgreSQL**: 構造化データ（ユーザー、セッション、メッセージ）
- **Neo4j**: 派生データ（エンティティ、事実、関係）
- **Graphiti**: PostgreSQLからNeo4jへの非同期データ変換

データ削除時の整合性維持が重要な課題となります。

### 2.3 詳細調査計画

#### ステップ1: データ依存関係のマッピング

**目的**: システム内のデータ依存関係を完全に把握

**調査対象**:
1. **データベース間の依存関係**
2. **テーブル間の外部キー制約**
3. **Graphitiサービスでの参照関係**
4. **APIレベルでの整合性チェック**

**実装**:
```python
class DataDependencyMapper:
    def __init__(self):
        self.postgres_conn = psycopg2.connect(...)
        self.neo4j_driver = neo4j.GraphDatabase.driver(...)
    
    def map_postgres_dependencies(self):
        """PostgreSQLの外部キー関係を調査"""
        with self.postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT
                    tc.table_name, 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public';
            """)
            return cur.fetchall()
    
    def map_neo4j_structure(self):
        """Neo4jのノード・関係構造を調査"""
        with self.neo4j_driver.session() as session:
            # ノードラベルの調査
            labels = session.run("CALL db.labels()").data()
            
            # 関係タイプの調査
            relationships = session.run("CALL db.relationshipTypes()").data()
            
            # ノード間の参照関係を調査
            references = session.run("""
                MATCH (a)-[r]->(b)
                RETURN DISTINCT labels(a) as source_labels, 
                       type(r) as relationship_type,
                       labels(b) as target_labels,
                       count(*) as count
                ORDER BY count DESC
                LIMIT 50
            """).data()
            
            return {
                'labels': labels,
                'relationships': relationships,
                'references': references
            }
    
    def analyze_cross_database_references(self):
        """データベース間の参照関係を分析"""
        # PostgreSQLのユーザーIDとNeo4jのエンティティIDの対応
        # セッションIDとファクトの関係
        # メッセージとナレッジグラフの対応
        pass
```

#### ステップ2: 削除シナリオの設計

**削除シナリオ一覧**:

| シナリオ | 対象データ | 削除方法 | 影響範囲 | 期待される結果 |
|----------|------------|----------|----------|----------------|
| S1 | 古いメッセージ（PostgreSQL） | 時系列削除（90日以前） | チャット履歴 | 履歴短縮、事実は保持 |
| S2 | 古い事実（Neo4j） | valid_at基準削除 | ナレッジグラフ | 古い知識の削除 |
| S3 | 非アクティブユーザー | 完全削除 | 全データ | 完全な記憶消去 |
| S4 | 特定セッション | カスケード削除 | 関連メッセージと事実 | 部分的記憶削除 |
| S5 | エンベディングデータ | ベクトル削除 | 検索性能 | 検索精度低下 |
| S6 | メタデータのみ | JSONB削除 | 詳細情報 | 基本機能は維持 |

**実装**:
```python
class DeletionScenarioTester:
    def __init__(self):
        self.zep_client = AsyncZep(...)
        self.postgres_conn = psycopg2.connect(...)
        self.neo4j_driver = neo4j.GraphDatabase.driver(...)
    
    async def test_scenario_s1_old_messages(self, cutoff_days=90):
        """シナリオS1: 古いメッセージの削除"""
        # 削除前の状態を記録
        before_state = await self.capture_system_state()
        
        # 90日以前のメッセージを特定
        old_messages = self.find_old_messages(cutoff_days)
        
        # メッセージ削除
        deleted_count = self.delete_old_messages(old_messages)
        
        # 削除後の状態を記録
        after_state = await self.capture_system_state()
        
        # 整合性チェック
        integrity_check = await self.check_data_integrity()
        
        # 機能テスト
        function_test = await self.test_memory_functionality()
        
        return {
            'scenario': 'S1_old_messages',
            'deleted_count': deleted_count,
            'before_state': before_state,
            'after_state': after_state,
            'integrity_check': integrity_check,
            'function_test': function_test
        }
    
    async def capture_system_state(self):
        """システム状態をキャプチャ"""
        postgres_counts = self.get_postgres_row_counts()
        neo4j_counts = self.get_neo4j_node_counts()
        sample_data = await self.get_sample_memory_responses()
        
        return {
            'postgres_counts': postgres_counts,
            'neo4j_counts': neo4j_counts,
            'sample_data': sample_data,
            'timestamp': datetime.now()
        }
    
    async def check_data_integrity(self):
        """データ整合性チェック"""
        checks = []
        
        # 孤立したレコードの確認
        orphaned_sessions = self.find_orphaned_sessions()
        orphaned_messages = self.find_orphaned_messages()
        
        # 外部キー制約違反の確認
        fk_violations = self.check_foreign_key_violations()
        
        # Neo4jの参照整合性確認
        neo4j_orphans = self.find_neo4j_orphans()
        
        return {
            'orphaned_sessions': orphaned_sessions,
            'orphaned_messages': orphaned_messages,
            'fk_violations': fk_violations,
            'neo4j_orphans': neo4j_orphans,
            'is_consistent': len(orphaned_sessions) == 0 and len(fk_violations) == 0
        }
    
    async def test_memory_functionality(self):
        """メモリ機能のテスト"""
        test_cases = [
            {'user_id': 'test_user_1', 'query': '私の趣味は何ですか？'},
            {'user_id': 'test_user_2', 'query': '前回話した内容を教えて'},
            {'user_id': 'test_user_3', 'query': '最近の出来事は？'}
        ]
        
        results = []
        for test_case in test_cases:
            try:
                memory = await self.zep_client.memory.get(test_case['user_id'])
                search_results = await self.zep_client.memory.search_sessions(
                    user_id=test_case['user_id'],
                    search_scope="facts",
                    text=test_case['query']
                )
                
                results.append({
                    'test_case': test_case,
                    'memory_available': memory is not None,
                    'search_results_count': len(search_results.results),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'test_case': test_case,
                    'error': str(e),
                    'success': False
                })
        
        return results
```

#### ステップ3: 段階的削除テストの実行

**実行順序**:
1. **準備**: テストデータの投入
2. **ベースライン**: 削除前の機能確認
3. **削除実行**: 各シナリオの段階的実行
4. **影響評価**: 機能への影響度測定
5. **復旧テスト**: 可能な範囲での復旧

**実装**:
```python
async def run_deletion_test_suite():
    """削除テストスイートの実行"""
    tester = DeletionScenarioTester()
    
    # テストデータの準備
    await tester.prepare_test_data()
    
    # ベースライン測定
    baseline = await tester.capture_system_state()
    
    scenarios = [
        ('S1', tester.test_scenario_s1_old_messages),
        ('S2', tester.test_scenario_s2_old_facts),
        ('S3', tester.test_scenario_s3_inactive_users),
        ('S4', tester.test_scenario_s4_specific_sessions),
        ('S5', tester.test_scenario_s5_embedding_data),
        ('S6', tester.test_scenario_s6_metadata_only),
    ]
    
    results = {'baseline': baseline, 'scenarios': {}}
    
    for scenario_name, scenario_func in scenarios:
        print(f"実行中: シナリオ {scenario_name}")
        
        try:
            scenario_result = await scenario_func()
            results['scenarios'][scenario_name] = scenario_result
            
            # 各シナリオ後に一定時間待機
            await asyncio.sleep(60)
            
        except Exception as e:
            results['scenarios'][scenario_name] = {
                'error': str(e),
                'success': False
            }
    
    return results
```

#### ステップ4: 復旧可能性の調査

**目的**: 削除されたデータの復旧可能性と影響を評価

**調査内容**:
1. **ソフトデリート vs ハードデリート**
2. **バックアップからの部分復旧**
3. **ナレッジグラフの再構築可能性**
4. **データ削除の可逆性**

**実装**:
```python
class RecoveryTester:
    async def test_soft_delete_recovery(self):
        """ソフトデリートからの復旧テスト"""
        # deleted_atフラグを使った論理削除
        # フラグクリアによる復旧
        # 整合性の回復度合いを測定
        pass
    
    async def test_backup_recovery(self):
        """バックアップからの復旧テスト"""
        # PostgreSQLダンプからの復旧
        # Neo4jエクスポートからの復旧
        # 時系列整合性の確認
        pass
    
    async def test_knowledge_graph_rebuild(self):
        """ナレッジグラフ再構築テスト"""
        # PostgreSQLメッセージからのナレッジグラフ再構築
        # 再構築時間の測定
        # 元のグラフとの比較
        pass
```

### 2.4 予想される結果と分析

#### 削除安全性の予想結果

1. **低リスク削除**:
   - 古いメッセージ（PostgreSQL）: チャット履歴は短縮されるが、重要な事実はNeo4jに保持
   - メタデータ: 機能には影響せず

2. **中リスク削除**:
   - 古い事実（Neo4j）: 過去の知識は失われるが、新しい情報は維持
   - 特定セッション: 部分的な記憶欠損

3. **高リスク削除**:
   - ユーザー完全削除: 全記憶の消失
   - エンベディング削除: 検索機能の大幅低下

#### 整合性への影響

1. **許容可能な削除**:
   - 90日以前のメッセージ: 5-10%の記憶精度低下
   - 非アクティブユーザー: 他ユーザーへの影響なし

2. **注意が必要な削除**:
   - 重要エンティティに関連する事実: 大幅な知識欠損
   - 頻繁に参照される情報: ユーザー体験の悪化

---

## 3. データ分類と保存戦略の分析

### 3.1 調査結果（コードベース分析）

#### データアーキテクチャの全体像

Zepは**ハイブリッドデータアーキテクチャ**を採用しており、以下の特徴があります：

**参照箇所**: 
- `/src/store/postgres/`: PostgreSQL関連
- `/src/lib/graphiti/`: Neo4j関連
- `/src/store/memory_dao.go`: データフロー制御

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Zep Client    │    │   Zep Server    │    │   Graphiti      │
│                 │───▶│                 │───▶│   Service       │
│ (Python/JS SDK) │    │   (Go)          │    │   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │     Neo4j       │
                       │                 │    │                 │
                       │ ・Users         │    │ ・Entities      │
                       │ ・Sessions      │    │ ・Facts         │
                       │ ・Messages      │    │ ・Relationships │
                       └─────────────────┘    └─────────────────┘
```

### 3.2 PostgreSQLデータ構造（構造化データ）

**参照箇所**: `/src/store/postgres/migrations/`

#### 3.2.1 主要テーブル構造

```sql
-- Users テーブル（ユーザーマスタ）
CREATE TABLE "users" (
    "uuid" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "id" BIGSERIAL,
    "user_id" VARCHAR NOT NULL UNIQUE,        -- 外部システムからのユーザーID
    "email" VARCHAR,
    "first_name" VARCHAR,
    "last_name" VARCHAR,
    "project_uuid" uuid NOT NULL,             -- マルチテナント対応
    "metadata" jsonb,                         -- 柔軟なメタデータ
    "created_at" timestamptz NOT NULL DEFAULT current_timestamp,
    "updated_at" timestamptz DEFAULT current_timestamp,
    "deleted_at" timestamptz                  -- ソフトデリート対応
);

-- Sessions テーブル（会話セッション）
CREATE TABLE "sessions" (
    "uuid" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "id" BIGSERIAL,
    "session_id" VARCHAR NOT NULL UNIQUE,     -- 外部システムからのセッションID
    "user_id" VARCHAR REFERENCES users(user_id), -- ユーザーとの関連
    "project_uuid" uuid NOT NULL,
    "metadata" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT current_timestamp,
    "updated_at" timestamptz NOT NULL DEFAULT current_timestamp,
    "deleted_at" timestamptz,
    "ended_at" timestamptz                    -- セッション終了時刻
);

-- Messages テーブル（チャットメッセージ）
CREATE TABLE "messages" (
    "uuid" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "id" BIGSERIAL,
    "session_id" VARCHAR NOT NULL REFERENCES sessions(session_id),
    "project_uuid" uuid NOT NULL,
    "role" VARCHAR NOT NULL,                  -- ユーザー名やAI名
    "role_type" role_type_enum DEFAULT 'norole', -- user, assistant, system等
    "content" VARCHAR NOT NULL,               -- メッセージ本文
    "token_count" BIGINT NOT NULL,           -- トークン数（課金計算用）
    "metadata" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT current_timestamp,
    "updated_at" timestamptz DEFAULT current_timestamp,
    "deleted_at" timestamptz
);
```

#### 3.2.2 インデックス戦略

**参照箇所**: `/src/store/postgres/migrations/000000000001_database_setup.up.sql`

```sql
-- パフォーマンス最適化のためのインデックス
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_project_uuid ON users(project_uuid);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_project_uuid ON sessions(project_uuid);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- ソフトデリート対応
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_sessions_deleted_at ON sessions(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_deleted_at ON messages(deleted_at) WHERE deleted_at IS NULL;

-- pgvector拡張（エンベディング用）
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 3.2.3 データ特性

| テーブル | データ特性 | 増加パターン | 保持期間 |
|----------|------------|--------------|----------|
| users | 低頻度更新 | ユーザー登録に比例 | 永続的 |
| sessions | 中頻度作成 | ユーザー活動に比例 | 長期保持 |
| messages | 高頻度作成 | 会話量に比例 | アーカイブ対象 |

### 3.3 Neo4jデータ構造（ナレッジグラフ）

**参照箇所**: Graphitiサービス経由（`/src/lib/graphiti/service.go`）

#### 3.3.1 ノード構造

```cypher
-- Entity ノード（エンティティ）
CREATE (e:Entity {
    uuid: 'entity-uuid',
    name: 'エンティティ名',
    summary: 'エンティティの要約',
    created_at: datetime(),
    valid_at: datetime(),
    invalid_at: datetime()
})

-- Fact ノード（事実）
CREATE (f:Fact {
    uuid: 'fact-uuid',
    fact: '具体的な事実の内容',
    created_at: datetime(),
    valid_at: datetime(),    -- 事実が有効になった時刻
    invalid_at: datetime(),  -- 事実が無効になった時刻（時系列推論用）
    expired_at: datetime()   -- 事実の有効期限
})

-- Episode ノード（エピソード）
CREATE (ep:Episode {
    uuid: 'episode-uuid',
    name: 'エピソード名',
    summary: 'エピソードの要約',
    created_at: datetime(),
    valid_at: datetime(),
    invalid_at: datetime()
})
```

#### 3.3.2 関係性構造

```cypher
-- エンティティ間の関係
CREATE (e1:Entity)-[r:RELATES_TO {
    relation_type: '関係の種類',
    strength: 0.8,           -- 関係の強度
    created_at: datetime(),
    valid_at: datetime(),
    invalid_at: datetime()
}]->(e2:Entity)

-- 事実とエンティティの関係
CREATE (f:Fact)-[r:MENTIONS {
    role: 'subject' | 'object' | 'predicate',
    created_at: datetime()
}]->(e:Entity)

-- エピソードと事実の関係
CREATE (ep:Episode)-[r:CONTAINS {
    sequence: 1,             -- エピソード内での順序
    created_at: datetime()
}]->(f:Fact)
```

#### 3.3.3 時系列データの管理

**時系列ナレッジグラフの特徴**:

1. **Bi-temporal データモデル**:
   - `valid_at`: 事実が現実世界で有効になった時刻
   - `invalid_at`: 事実が現実世界で無効になった時刻
   - `created_at`: システムに記録された時刻

2. **事実の更新メカニズム**:
   ```cypher
   -- 古い事実を無効化
   MATCH (f:Fact {uuid: 'old-fact-uuid'})
   SET f.invalid_at = datetime()
   
   -- 新しい事実を作成
   CREATE (new_f:Fact {
       uuid: 'new-fact-uuid',
       fact: '更新された事実',
       valid_at: datetime(),
       created_at: datetime()
   })
   ```

### 3.4 データフロー分析

**参照箇所**: `/src/store/memory_dao.go`

#### 3.4.1 書き込みフロー

```go
// メッセージ追加時のデータフロー
func (dao *memoryDAO) Add(ctx context.Context, sessionID string, messages []models.Message) error {
    // 1. PostgreSQLにメッセージを即座に保存
    err := dao.messageStore.Create(ctx, messages)
    if err != nil {
        return err
    }
    
    // 2. Graphitiサービスに非同期でメッセージを送信
    go func() {
        graphiti.I().PutMemory(ctx, graphiti.PutMemoryRequest{
            GroupID:  groupID,
            Messages: convertMessages(messages),
        })
    }()
    
    return nil
}
```

**フロー説明**:
1. **即座にPostgreSQLに保存**: チャット履歴の確実な保存
2. **非同期でGraphitiに送信**: ナレッジグラフの構築（時間がかかるため）
3. **Graphiti内部処理**:
   - LLM（GPT-4o-mini）で事実抽出
   - エンベディング（text-embedding-3-large）でベクトル化
   - Neo4jにグラフ構造で保存

#### 3.4.2 読み込みフロー

```go
// メモリ取得時のデータフロー
func (dao *memoryDAO) Get(ctx context.Context, sessionID string, lastN int) (*models.Memory, error) {
    // 1. PostgreSQLからメッセージ履歴を取得
    messages, err := dao.messageStore.GetBySessionID(ctx, sessionID, lastN)
    if err != nil {
        return nil, err
    }
    
    // 2. Graphitiから関連する事実を取得
    graphitiMemory, err := graphiti.I().GetMemory(ctx, graphiti.GetMemoryRequest{
        GroupID:  groupID,
        MaxFacts: 5,
        Messages: convertMessages(messages),
    })
    if err != nil {
        return nil, err
    }
    
    // 3. 結果を統合して返却
    result := &models.Memory{
        Messages:      messages,
        RelevantFacts: convertFacts(graphitiMemory.Facts),
    }
    
    return result, nil
}
```

**統合戦略**:
- **PostgreSQL**: 完全なチャット履歴
- **Neo4j**: 文脈に関連する重要な事実
- **統合結果**: リッチなメモリ応答

### 3.5 データ保持戦略

#### 3.5.1 PostgreSQLデータ保持

**参照箇所**: `/src/store/db_utils_ce.go`

```go
// コミュニティエディション特有のデータパージ処理
func purgeDeletedResources(ctx context.Context, db pg.Connection) error {
    logger.Debug("purging memory store")
    
    // ソフトデリートされたリソースをハードデリート
    for _, schema := range messageTableList {
        _, err := db.NewDelete().
            Model(schema).
            WhereDeleted().        // deleted_at IS NOT NULL
            ForceDelete().         // 物理削除
            Exec(ctx)
        if err != nil {
            return fmt.Errorf("error purging rows from %T: %w", schema, err)
        }
    }
    
    // VACUUMによる領域回収
    _, err := db.ExecContext(ctx, "VACUUM ANALYZE")
    return err
}
```

**保持戦略**:
1. **ソフトデリート**: `deleted_at`フラグによる論理削除
2. **定期パージ**: 物理削除による領域回収
3. **VACUUM処理**: pgvectorインデックスの最適化

#### 3.5.2 Neo4jデータ保持

**時系列データの自動管理**:
```cypher
-- 期限切れ事実の特定
MATCH (f:Fact)
WHERE f.expired_at < datetime()
SET f.invalid_at = datetime()

-- 古い無効事実の削除
MATCH (f:Fact)
WHERE f.invalid_at < datetime() - duration('P90D')  -- 90日前
DELETE f
```

### 3.6 スケーラビリティ考慮事項

#### 3.6.1 PostgreSQLスケーラビリティ

1. **パーティショニング戦略**:
   ```sql
   -- 時系列パーティショニング（将来的な拡張）
   CREATE TABLE messages_y2024m01 PARTITION OF messages
   FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
   ```

2. **インデックス最適化**:
   - B-treeインデックス: 等価検索、範囲検索
   - GINインデックス: JSONB検索
   - 部分インデックス: ソフトデリート対応

#### 3.6.2 Neo4jスケーラビリティ

1. **インデックス戦略**:
   ```cypher
   CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name);
   CREATE INDEX fact_valid_at_index FOR (f:Fact) ON (f.valid_at);
   ```

2. **クエリ最適化**:
   - ラベルベースの効率的なトラバーサル
   - インデックスヒントの活用
   - 結果セットの制限

### 3.7 データ分類まとめ

| データ種別 | 保存場所 | 特性 | 用途 | 保持期間 |
|------------|----------|------|------|----------|
| **ユーザープロファイル** | PostgreSQL | 静的、構造化 | 認証、個人設定 | 永続 |
| **セッション情報** | PostgreSQL | 準静的、構造化 | 会話管理 | 長期 |
| **チャットメッセージ** | PostgreSQL | 動的、半構造化 | 履歴表示、監査 | アーカイブ |
| **抽出された事実** | Neo4j | 動的、グラフ構造 | 知識検索、推論 | 時系列管理 |
| **エンティティ** | Neo4j | 準静的、グラフ構造 | 関係性管理 | 長期 |
| **関係性** | Neo4j | 動的、グラフ構造 | 文脈理解 | 時系列管理 |
| **エンベディング** | 両方 | 静的、ベクトル | 意味検索 | キャッシュ |
| **メタデータ** | PostgreSQL | 動的、JSONB | 拡張情報 | 親データに依存 |

---

## 実行計画とスケジュール

### フェーズ1: 環境構築と基礎測定（1-2日）
1. 測定用スクリプトの作成
2. ベースライン測定の実行
3. 測定インフラの検証

### フェーズ2: データ量調査（3-5日）
1. 段階的データ投入テストの実行
2. スケーリングテストの実行
3. 結果分析とレポート作成

### フェーズ3: 削除影響調査（3-5日）
1. 削除シナリオテストの実行
2. 整合性検証の実行
3. 安全な削除ガイドラインの策定

### フェーズ4: 総合分析（1-2日）
1. 全結果の統合分析
2. 運用推奨事項の策定
3. 最終レポートの作成

### 期待される成果物

1. **データ量分析レポート**:
   - ユーザーあたりのデータ増加量定量化
   - スケーリング限界の特定
   - リソース使用量予測モデル

2. **データ削除ガイドライン**:
   - 安全な削除手順書
   - リスクレベル別の削除方針
   - 復旧手順書

3. **運用推奨事項**:
   - データ保持ポリシー
   - パフォーマンス監視指標
   - スケーリング戦略

この調査計画により、Zep Community Editionの実用的な運用指針を策定できると期待されます。