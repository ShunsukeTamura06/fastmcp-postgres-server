# FastMCP PostgreSQL Server

FastMCP を使用したPostgreSQLデータベース操作のためのMCPサーバーです。DifyからMCPとして読み込むことで、AIアシスタントがPostgreSQLデータベースを直接操作できるようになります。

## ✨ 主な機能

### 🔧 データベース操作ツール
- **execute_query**: 汎用SQLクエリ実行（SELECT、INSERT、UPDATE、DELETE、DDL等）
- **get_tables**: データベース内のテーブル一覧取得
- **get_table_schema**: 指定テーブルのスキーマ情報取得
- **select_data**: テーブルからデータ選択（WHERE条件、LIMIT指定可能）
- **insert_data**: テーブルへのデータ挿入
- **update_data**: テーブルデータの更新
- **delete_data**: テーブルからデータ削除
- **get_database_info**: データベースの基本情報取得

### 🔒 セキュリティ機能
- **Safe Mode**: 危険なSQL操作（DROP、TRUNCATE等）の検出と防止
- **WHERE句必須**: UPDATE/DELETE操作でのWHERE条件必須化
- **SQL Injection対策**: パラメータ化クエリの使用
- **接続プール管理**: 安全で効率的なデータベース接続

## 🚀 クイックスタート

### 1. リポジトリのクローン
```bash
git clone https://github.com/ShunsukeTamura06/fastmcp-postgres-server.git
cd fastmcp-postgres-server
```

### 2. 環境設定
```bash
# 環境変数ファイルをコピー
cp .env.example .env

# データベース接続情報を編集
vim .env
```

### 3. Docker Composeで起動
```bash
# PostgreSQL + FastMCP サーバーを起動
docker compose up -d

# pgAdminも含めて起動（データベース管理用）
docker compose --profile admin up -d

# 開発モードで起動
docker compose --profile dev up -d
```

### 4. 動作確認
```bash
# サーバーの状態確認
curl http://localhost:8001

# PostgreSQLの動作確認
docker compose exec postgres psql -U postgres -d testdb -c "SELECT version();"
```

## 🔧 設定

### 環境変数 (.env)
```bash
# PostgreSQL Database Configuration
POSTGRES_HOST=localhost          # データベースホスト
POSTGRES_PORT=5432              # データベースポート
POSTGRES_DATABASE=postgres      # データベース名
POSTGRES_USER=postgres          # ユーザー名
POSTGRES_PASSWORD=your_password # パスワード

# Server Configuration
SERVER_HOST=0.0.0.0            # サーバーホスト
SERVER_PORT=8001               # サーバーポート

# Security Settings
SAFE_MODE=true                 # 安全モード（危険なクエリをブロック）
MAX_QUERY_RESULTS=1000         # クエリ結果の最大行数

# Connection Pool Settings
POOL_MIN_SIZE=1                # 接続プールの最小サイズ
POOL_MAX_SIZE=10               # 接続プールの最大サイズ
CONNECTION_TIMEOUT=30          # 接続タイムアウト（秒）
```

## 🔌 DifyとのMCP連携

### 1. Difyでの設定手順

1. **MCPサーバーを起動**
   ```bash
   docker compose up -d
   ```

2. **DifyのMCP設定画面で以下を入力**
   - **サーバーURL**: `http://localhost:8001` または `http://your-server:8001`
   - **サーバータイプ**: `SSE`
   - **認証**: 不要（プライベートネットワーク内での使用を想定）

3. **接続テスト**
   - Difyで接続テストを実行
   - 使用可能なツールが表示されることを確認

### 2. ツールの使用例

#### テーブル一覧の取得
```
get_tables()
```

#### データの検索
```
select_data(
    table_name="users",
    columns="id, name, email",
    where_clause="age > 18",
    limit=50
)
```

#### データの挿入
```
insert_data(
    table_name="users",
    data={
        "name": "田中太郎",
        "email": "taro@example.com",
        "age": 25
    }
)
```

#### 複雑なSQLクエリの実行
```
execute_query(
    query="SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name",
    safe_mode=true
)
```

## 🛡️ セキュリティ

### Safe Mode
デフォルトで有効になっており、以下の危険な操作をブロックします：
- `DROP TABLE`
- `DROP DATABASE`
- `TRUNCATE`
- 条件なしの`DELETE`
- 条件なしの`UPDATE`

### パラメータ化クエリ
SQLインジェクション攻撃を防ぐため、すべてのユーザー入力はパラメータ化されます。

### 接続管理
- 接続プールを使用した効率的なデータベース接続
- 接続タイムアウトの設定
- 自動接続復旧

## 📊 管理

### pgAdmin
データベースの管理にはpgAdminを使用できます：
```bash
# pgAdminを起動
docker compose --profile admin up -d

# ブラウザでアクセス
open http://localhost:8080
```

**デフォルトログイン情報:**
- Email: `admin@example.com`
- Password: `admin`

### ログ
```bash
# サーバーログの確認
docker compose logs fastmcp-postgres-server

# PostgreSQLログの確認
docker compose logs postgres
```

## 🏗️ 開発

### ローカル開発
```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集

# サーバーの起動
python server.py
```

### 開発用Docker環境
```bash
# 開発モードで起動（ファイル変更を自動反映）
docker compose --profile dev up -d
```

## 🎯 使用例

### 顧客データの分析
```python
# 顧客の年齢分布を取得
execute_query("""
SELECT 
    CASE 
        WHEN age < 20 THEN '10代'
        WHEN age < 30 THEN '20代'
        WHEN age < 40 THEN '30代'
        ELSE '40代以上'
    END as age_group,
    COUNT(*) as count
FROM customers 
GROUP BY age_group
ORDER BY age_group
""")
```

### 売上レポートの生成
```python
# 月別売上を取得
select_data(
    table_name="sales_summary",
    columns="month, total_amount, order_count",
    where_clause="year = 2024",
    limit=12
)
```

## 🔧 トラブルシューティング

### 接続エラー
```bash
# PostgreSQLサーバーの状態確認
docker compose exec postgres pg_isready -U postgres

# ネットワーク確認
docker compose exec fastmcp-postgres-server ping postgres
```

### パフォーマンス問題
- 接続プールサイズの調整（`POOL_MAX_SIZE`）
- クエリ結果数の制限（`MAX_QUERY_RESULTS`）
- インデックスの最適化

## 📋 必要な環境

- **Docker**: 20.10以上
- **Docker Compose**: 2.0以上
- **Python**: 3.11以上（ローカル開発時）
- **PostgreSQL**: 15以上（外部データベース使用時）

## 🤝 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 📞 サポート

問題が発生した場合は、[Issues](https://github.com/ShunsukeTamura06/fastmcp-postgres-server/issues) でご報告ください。

## 🔗 関連リンク

- [FastMCP](https://github.com/jlowin/fastmcp) - MCPサーバーフレームワーク
- [Dify](https://dify.ai/) - AIアシスタント構築プラットフォーム
- [PostgreSQL](https://www.postgresql.org/) - データベース
- [asyncpg](https://github.com/MagicStack/asyncpg) - Python PostgreSQL ドライバー
