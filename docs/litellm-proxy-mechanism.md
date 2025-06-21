# LiteLLM Proxy Mechanism

## 概要

LiteLLMプロキシは、OpenAI互換のAPIインターフェースを提供しながら、バックエンドで様々なLLMプロバイダー（Azure OpenAI、AWS Bedrock、Google PaLMなど）を統一的に利用できるプロキシサーバーです。Zepプロジェクトでは、OpenAIのクォータ制限を回避するためにAzure OpenAIを使用する目的で導入されています。

## アーキテクチャ

### 全体構成
```
Graphiti Container (Docker)
↓ OpenAI SDK
http://host.docker.internal:4000 (LiteLLM Proxy)
↓ Azure OpenAI API
https://YOUR_AZURE_ENDPOINT.openai.azure.com/
```

### プロキシの役割
1. **プロトコル変換**: OpenAI API形式 ↔ Azure OpenAI API形式
2. **認証管理**: プロキシ用APIキー ↔ Azure OpenAI APIキー
3. **モデルマッピング**: 仮想モデル名 → 実際のAzureデプロイメント名
4. **エラーハンドリング**: 統一されたエラーレスポンス
5. **負荷分散**: 複数エンドポイント間でのリクエスト分散

## 設定ファイル (litellm_config.yaml)

### モデル定義
```yaml
model_list:
  - model_name: gpt-4o-mini                    # 仮想モデル名
    litellm_params:
      model: azure/gpt-4o                      # 実際のAzureデプロイメント
      api_base: https://YOUR_AZURE_ENDPOINT.openai.azure.com/
      api_version: 2024-12-01-preview
      api_key: YOUR_AZURE_OPENAI_API_KEY

  - model_name: text-embedding-3-small         # 仮想モデル名
    litellm_params:
      model: azure/text-embedding-3-large      # 実際のAzureデプロイメント
      api_base: https://YOUR_AZURE_ENDPOINT.openai.azure.com/
      api_version: 2024-12-01-preview
      api_key: YOUR_AZURE_OPENAI_API_KEY
```

### 認証設定
```yaml
general_settings:
  master_key: zep-proxy-key                    # プロキシ認証用キー
```

### プロキシ設定
```yaml
litellm_settings:
  drop_params: true                            # 不要パラメータの除去
  set_verbose: false                           # ログレベル
  content_policy_fallback: "gpt-4o-mini"      # コンテンツフィルタ時のフォールバック
  retry_policy: 
    - "ContentPolicyViolationError"            # リトライ対象エラー
```

## リクエストフロー詳細

### 1. Graphiti → LiteLLM Proxy

**HTTPリクエスト:**
```http
POST http://host.docker.internal:4000/v1/embeddings
Authorization: Bearer zep-proxy-key
Content-Type: application/json

{
  "model": "text-embedding-3-small",
  "input": ["ユーザーの発言内容"]
}
```

**Graphiti環境変数:**
```yaml
environment:
  - OPENAI_API_KEY=zep-proxy-key                    # プロキシ認証
  - OPENAI_BASE_URL=http://host.docker.internal:4000  # プロキシURL
  - MODEL_NAME=dummy-model                          # 使用モデル
```

### 2. LiteLLM Proxy内部処理

**認証チェック:**
```python
# master_keyとリクエストのAPIキーを照合
if request.headers["Authorization"] != f"Bearer {master_key}":
    return 401_error
```

**モデルマッピング:**
```python
# text-embedding-3-small → azure/text-embedding-3-large
virtual_model = "text-embedding-3-small"
actual_model = model_list[virtual_model]["model"]  # azure/text-embedding-3-large
```

**リクエスト変換:**
```python
# OpenAI形式 → Azure OpenAI形式
azure_request = {
    "input": request.input,
    "model": deployment_name,  # text-embedding-3-large
}
```

### 3. LiteLLM → Azure OpenAI

**変換されたHTTPリクエスト:**
```http
POST https://YOUR_AZURE_ENDPOINT.openai.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2024-12-01-preview
api-key: YOUR_AZURE_OPENAI_API_KEY
Content-Type: application/json

{
  "input": ["ユーザーの発言内容"]
}
```

### 4. レスポンスフロー

**Azure OpenAI → LiteLLM:**
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.123, -0.456, ...]
    }
  ],
  "model": "text-embedding-3-large",
  "usage": {"prompt_tokens": 10, "total_tokens": 10}
}
```

**LiteLLM → Graphiti (OpenAI互換形式):**
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.123, -0.456, ...]
    }
  ],
  "model": "text-embedding-3-small",  # 仮想モデル名で返却
  "usage": {"prompt_tokens": 10, "total_tokens": 10}
}
```

## 起動と運用

### プロキシ起動方法
```bash
# 環境変数を設定してプロキシ起動
export $(grep -v '^#' .env | xargs)
litellm --config litellm_config.yaml --port 4000
```

### 健康チェック
```bash
# プロキシの動作確認
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer zep-proxy-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### ログ例
```
15:47:26 - LiteLLM Proxy:INFO: Received request for model=text-embedding-3-small
15:47:26 - LiteLLM Proxy:INFO: Mapped to azure/text-embedding-3-large
15:47:26 - LiteLLM Proxy:ERROR: Azure authentication failed
```

## エラーパターンと対処法

### 1. 認証エラー (400 Bad Request)
```
litellm.proxy.proxy_server.user_api_key_auth(): Exception occured
```

**原因:**
- `master_key` とクライアントのAPIキーが不一致
- `general_settings.master_key` が設定されていない

**対処:**
```yaml
general_settings:
  master_key: zep-proxy-key  # コメントアウトを解除
```

### 2. Azure認証エラー (401 Unauthorized)
```
AzureException AuthenticationError - Access denied due to invalid subscription key
```

**原因:**
- Azure OpenAI APIキーが無効
- エンドポイントURLが間違っている
- デプロイメント名が存在しない

**対処:**
```yaml
# 正しいAzure設定を確認
api_key: "有効なAzure OpenAI APIキー"
api_base: "https://正しいエンドポイント.openai.azure.com/"
model: "azure/実際に存在するデプロイメント名"
```

### 3. 環境変数展開エラー
```
InvalidURL: /${AZURE_OPENAI_ENDPOINT}/openai/deployments/
```

**原因:**
- 環境変数が正しく読み込まれていない
- `${変数名}` が文字列として残っている

**対処:**
```bash
# 環境変数を明示的に展開
set -a && source .env && set +a
litellm --config litellm_config.yaml --port 4000
```

### 4. モデル不一致エラー
```
No deployments available for selected model
```

**原因:**
- 要求されたモデル名とconfig内のモデル名が不一致
- Azure側にデプロイメントが存在しない

**対処:**
```yaml
# クライアント要求: text-embedding-3-small
# config定義: text-embedding-3-small (一致させる)
- model_name: text-embedding-3-small
  litellm_params:
    model: azure/実際のデプロイメント名
```

## セキュリティ考慮事項

### APIキー管理
- **master_key**: プロキシ認証用（内部通信）
- **Azure API Key**: 実際のAzure OpenAI認証用（外部通信）
- APIキーは環境変数または設定ファイルで管理
- 本番環境では設定ファイルに直接記載しない

### ネットワークセキュリティ
- プロキシは localhost:4000 でのみリッスン
- Docker内部ネットワークからのみアクセス可能
- 外部からの直接アクセスは不可

## パフォーマンス特性

### レイテンシ
- プロキシ処理のオーバーヘッド: ~10-50ms
- 主要な遅延はAzure OpenAI APIの応答時間

### スループット
- 非同期処理によりスループット向上
- 複数エンドポイント設定時の負荷分散

### リソース使用量
- CPU: 軽量（主にI/Oバウンド）
- メモリ: 設定とキャッシュに応じて数十MB
- ネットワーク: クライアント-プロキシ-Azure間の通信

## まとめ

LiteLLMプロキシにより、Zepプロジェクトは以下の利点を得ています：

1. **OpenAIクォータ回避**: Azure OpenAIを透過的に利用
2. **コード変更最小化**: OpenAI SDKをそのまま使用可能
3. **設定の柔軟性**: モデルやエンドポイントの動的切り替え
4. **統一されたエラーハンドリング**: 一貫したAPIレスポンス
5. **運用の簡素化**: 単一プロキシでの一元管理

この仕組みにより、GraphitiはOpenAI APIを使用しているつもりで、実際はAzure OpenAIのリソースを利用してナレッジグラフの構築を行うことができています。