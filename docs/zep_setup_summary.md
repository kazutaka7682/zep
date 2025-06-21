# Zep Community Edition セットアップサマリー

## プロジェクト概要

### Zepとは
- AIエージェントがユーザーとの対話から継続的に学習するためのメモリ基盤
- テンポラルナレッジグラフを使用して、事実の変化を追跡
- パーソナライズされた体験を提供

### システム構成
Zep Community Editionは以下のサービスで構成されます：

1. **Zep本体** (ポート8000) - メインAPIサーバー
2. **PostgreSQL with pgvector** (ポート5432) - ベクトル検索対応データベース
3. **Graphiti** (ポート8003) - テンポラルナレッジグラフライブラリ
4. **Neo4j** (ポート7474/7687) - グラフデータベース

## 起動手順

### 基本的な起動方法
```bash
# 1. コンテナイメージをダウンロード
./zep pull

# 2. サービスを起動
./zep up
```

### 設定ファイル
- **zep.yaml**: メイン設定ファイル
- **.env**: 環境変数（OpenAI APIキーなど）
- **docker-compose.ce.yaml**: Docker Compose設定

## 遭遇した問題と解決策

### 問題1: OpenAI APIクォータ超過
```
openai.RateLimitError: Error code: 429
'You exceeded your current quota, please check your plan and billing details.'
```

**原因**: GraphitiサービスがOpenAI APIを使用してナレッジグラフを構築する際にクォータを超過

### 解決策: Azure OpenAI + LiteLLMプロキシの導入

#### 1. LiteLLMインストール
```bash
pip install litellm
```

#### 2. LiteLLM設定ファイル作成 (litellm_config.yaml)
```yaml
model_list:
  - model_name: gpt-4o-mini
    litellm_params:
      model: azure/gpt-4o-mini
      api_base: https://meiji-chatbot-rag-openai.openai.azure.com/
      api_version: "2024-12-01-preview"
      api_key: "YOUR_AZURE_API_KEY"

general_settings:
  master_key: "zep-proxy-key"

litellm_settings:
  drop_params: true
  set_verbose: false
```

#### 3. docker-compose.ce.yaml修正
Graphitiサービスの環境変数を以下に変更：
```yaml
environment:
  - OPENAI_API_KEY=zep-proxy-key
  - OPENAI_BASE_URL=http://host.docker.internal:4000
  - MODEL_NAME=gpt-4o-mini
```

#### 4. プロキシ起動とテスト
```bash
# LiteLLMプロキシ起動
litellm --config litellm_config.yaml --port 4000

# Zepサービス再起動
./zep down
./zep up

# プロキシテスト
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer zep-proxy-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
```

## OpenAI APIの使用目的

### 主な用途：知識グラフの自動構築
1. **チャットメッセージからの情報抽出**
   - ユーザーとAIエージェントの会話から事実（facts）を抽出
   - エンティティと関係性を識別

2. **時系列ナレッジグラフの更新**
   - 新しい情報を既存のグラフに統合
   - 古い事実の無効化と新しい事実の追加

3. **コンテキストの理解と要約**
   - 会話の文脈を理解して関連する事実を生成

### アーキテクチャ
```
呼び出し元アプリ → Zep API → Graphiti → LiteLLM Proxy → Azure OpenAI
                     ↓
                  Neo4j（グラフDB）
```

## コミュニティーエディション vs クラウド版

### クラウド版のみの機能
1. **低レイテンシ、スケーラビリティ、高可用性** - 数百万DAUに対応
2. **Dialog Classification** - チャットダイアログの即時分類
3. **Structured Data Extraction** - ビジネスデータの構造化抽出

### 注意点
**Zep Community Editionは非推奨**となっており、新しい開発やサポートは行われていません。

## モデル対応

### サポートモデル
- GPT-4o、o3-mini、gpt-4-turbo等のOpenAI互換モデルに対応
- MODEL_NAME環境変数で指定可能

### パラメータ設定
- Temperature: デフォルト0（一貫性重視）
- Max tokens: デフォルト8192
- 構造化出力対応モデル推奨

## ファイル構成

- `zep` - 起動スクリプト
- `zep.yaml` - メイン設定ファイル
- `docker-compose.ce.yaml` - Docker Compose設定
- `litellm_config.yaml` - LiteLLMプロキシ設定
- `.env` - 環境変数ファイル

## まとめ

Azure OpenAI + LiteLLMプロキシの組み合わせにより、OpenAIのクォータ制限を回避してZep Community Editionを正常に動作させることができました。これにより、AIエージェントが継続的に学習し、パーソナライズされた体験を提供するメモリシステムとして機能します。