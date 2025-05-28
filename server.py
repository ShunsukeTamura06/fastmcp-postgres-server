from fastmcp import FastMCP
from typing import Optional, List, Dict, Any, Union
import asyncpg
import asyncio
import nest_asyncio
import os
import json
import re
from datetime import datetime, date

# FastMCPサーバーを作成
mcp = FastMCP("PostgreSQL MCP Server")

# nest_asyncioを適用してネストしたイベントループを許可
nest_asyncio.apply()

# データベース接続プール
connection_pool = None

# 危険なSQL操作のパターン
DANGEROUS_PATTERNS = [
    r'\bdrop\s+table\b',
    r'\bdrop\s+database\b',
    r'\btruncate\b',
    r'\bdelete\s+from\s+\w+\s*;?\s*$',  # DELETE文で条件がないもの
    r'\bupdate\s+\w+\s+set\s+.*\s*;?\s*$',  # UPDATE文で条件がないもの
]

async def get_connection_pool():
    """データベース接続プールを取得または作成"""
    global connection_pool
    if connection_pool is None:
        try:
            # 環境変数からデータベース設定を取得
            host = os.getenv('POSTGRES_HOST', 'localhost')
            port = int(os.getenv('POSTGRES_PORT', 5432))
            database = os.getenv('POSTGRES_DATABASE', 'postgres')
            user = os.getenv('POSTGRES_USER', 'postgres')
            password = os.getenv('POSTGRES_PASSWORD', '')
            
            connection_pool = await asyncpg.create_pool(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                min_size=1,
                max_size=10,
                command_timeout=30
            )
        except Exception as e:
            raise Exception(f"Failed to create database connection pool: {str(e)}")
    
    return connection_pool

def is_dangerous_query(query: str) -> bool:
    """危険なSQL操作かどうかチェック"""
    query_lower = query.lower().strip()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True
    return False

def serialize_row(row) -> Dict[str, Any]:
    """データベースの行をJSONシリアライズ可能な形式に変換"""
    result = {}
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        elif isinstance(value, (bytes, bytearray)):
            result[key] = value.hex()
        else:
            result[key] = value
    return result

async def _execute_query_async(
    query: str,
    params: Optional[List] = None,
    safe_mode: bool = True
) -> Union[List[Dict[str, Any]], str]:
    """非同期でSQLクエリを実行"""
    try:
        # 安全モードでの危険なクエリチェック
        if safe_mode and is_dangerous_query(query):
            return "Error: Dangerous query detected. Use safe_mode=False to execute if you're sure."
        
        pool = await get_connection_pool()
        
        async with pool.acquire() as connection:
            # クエリの種類を判断
            query_lower = query.lower().strip()
            
            if query_lower.startswith(('select', 'with')):
                # SELECT クエリ
                if params:
                    rows = await connection.fetch(query, *params)
                else:
                    rows = await connection.fetch(query)
                
                return [serialize_row(row) for row in rows]
            
            elif query_lower.startswith(('insert', 'update', 'delete')):
                # データ変更クエリ
                if params:
                    result = await connection.execute(query, *params)
                else:
                    result = await connection.execute(query)
                return f"Query executed successfully. {result}"
            
            else:
                # その他のクエリ（DDL等）
                if params:
                    result = await connection.execute(query, *params)
                else:
                    result = await connection.execute(query)
                return f"Query executed successfully. {result}"
    
    except Exception as e:
        return f"Database error: {str(e)}"

async def _get_tables_async() -> List[Dict[str, Any]]:
    """非同期でテーブル一覧を取得"""
    try:
        pool = await get_connection_pool()
        
        async with pool.acquire() as connection:
            query = """
            SELECT 
                table_name,
                table_type,
                table_schema
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name;
            """
            rows = await connection.fetch(query)
            return [serialize_row(row) for row in rows]
    
    except Exception as e:
        return [{"error": f"Failed to get tables: {str(e)}"}]

async def _get_schema_async(table_name: str, schema_name: str = 'public') -> List[Dict[str, Any]]:
    """非同期でテーブルスキーマを取得"""
    try:
        pool = await get_connection_pool()
        
        async with pool.acquire() as connection:
            query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = $1 AND table_schema = $2
            ORDER BY ordinal_position;
            """
            rows = await connection.fetch(query, table_name, schema_name)
            return [serialize_row(row) for row in rows]
    
    except Exception as e:
        return [{"error": f"Failed to get schema: {str(e)}"}]

def _execute_with_loop(coro):
    """イベントループでコルーチンを実行"""
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro)
        return loop.run_until_complete(task)
    except RuntimeError:
        return asyncio.run(coro)
    except Exception as e:
        try:
            return asyncio.run(coro)
        except Exception as nested_e:
            return f"Error executing database operation: {str(e)} | Nested error: {str(nested_e)}"

@mcp.tool()
def execute_query(
    query: str,
    params: Optional[List] = None,
    safe_mode: bool = True
) -> str:
    """
    SQLクエリを実行します。

    Args:
        query: 実行するSQLクエリ
        params: クエリのパラメータ（オプション）
        safe_mode: 危険なクエリの実行を防ぐ（デフォルト: True）
    """
    result = _execute_with_loop(_execute_query_async(query, params, safe_mode))
    if isinstance(result, list):
        return json.dumps(result, indent=2, ensure_ascii=False)
    return str(result)

@mcp.tool()
def get_tables() -> str:
    """
    データベース内のテーブル一覧を取得します。
    """
    result = _execute_with_loop(_get_tables_async())
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool()
def get_table_schema(table_name: str, schema_name: str = 'public') -> str:
    """
    指定されたテーブルのスキーマ情報を取得します。

    Args:
        table_name: テーブル名
        schema_name: スキーマ名（デフォルト: public）
    """
    result = _execute_with_loop(_get_schema_async(table_name, schema_name))
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool()
def select_data(
    table_name: str,
    columns: str = "*",
    where_clause: str = "",
    limit: int = 100,
    schema_name: str = 'public'
) -> str:
    """
    テーブルからデータを選択します。

    Args:
        table_name: テーブル名
        columns: 選択する列（デフォルト: *）
        where_clause: WHERE条件（オプション）
        limit: 取得する行数の上限（デフォルト: 100）
        schema_name: スキーマ名（デフォルト: public）
    """
    # クエリを構築
    query = f"SELECT {columns} FROM {schema_name}.{table_name}"
    
    if where_clause:
        query += f" WHERE {where_clause}"
    
    query += f" LIMIT {limit}"
    
    result = _execute_with_loop(_execute_query_async(query, safe_mode=True))
    if isinstance(result, list):
        return json.dumps(result, indent=2, ensure_ascii=False)
    return str(result)

@mcp.tool()
def insert_data(
    table_name: str,
    data: Dict[str, Any],
    schema_name: str = 'public'
) -> str:
    """
    テーブルにデータを挿入します。

    Args:
        table_name: テーブル名
        data: 挿入するデータ（列名: 値の辞書）
        schema_name: スキーマ名（デフォルト: public）
    """
    if not data:
        return "Error: No data provided for insertion"
    
    columns = list(data.keys())
    values = list(data.values())
    placeholders = [f"${i+1}" for i in range(len(values))]
    
    query = f"""
    INSERT INTO {schema_name}.{table_name} ({', '.join(columns)})
    VALUES ({', '.join(placeholders)})
    """
    
    result = _execute_with_loop(_execute_query_async(query, values, safe_mode=True))
    return str(result)

@mcp.tool()
def update_data(
    table_name: str,
    data: Dict[str, Any],
    where_clause: str,
    schema_name: str = 'public'
) -> str:
    """
    テーブルのデータを更新します。

    Args:
        table_name: テーブル名
        data: 更新するデータ（列名: 値の辞書）
        where_clause: WHERE条件（必須）
        schema_name: スキーマ名（デフォルト: public）
    """
    if not data:
        return "Error: No data provided for update"
    
    if not where_clause:
        return "Error: WHERE clause is required for UPDATE operation"
    
    set_clauses = [f"{col} = ${i+1}" for i, col in enumerate(data.keys())]
    values = list(data.values())
    
    query = f"""
    UPDATE {schema_name}.{table_name}
    SET {', '.join(set_clauses)}
    WHERE {where_clause}
    """
    
    result = _execute_with_loop(_execute_query_async(query, values, safe_mode=True))
    return str(result)

@mcp.tool()
def delete_data(
    table_name: str,
    where_clause: str,
    schema_name: str = 'public'
) -> str:
    """
    テーブルからデータを削除します。

    Args:
        table_name: テーブル名
        where_clause: WHERE条件（必須）
        schema_name: スキーマ名（デフォルト: public）
    """
    if not where_clause:
        return "Error: WHERE clause is required for DELETE operation"
    
    query = f"DELETE FROM {schema_name}.{table_name} WHERE {where_clause}"
    
    result = _execute_with_loop(_execute_query_async(query, safe_mode=True))
    return str(result)

@mcp.tool()
def get_database_info() -> str:
    """
    データベースの基本情報を取得します。
    """
    query = """
    SELECT 
        version() as postgresql_version,
        current_database() as database_name,
        current_user as current_user,
        inet_server_addr() as server_address,
        inet_server_port() as server_port
    """
    
    result = _execute_with_loop(_execute_query_async(query, safe_mode=True))
    if isinstance(result, list):
        return json.dumps(result, indent=2, ensure_ascii=False)
    return str(result)

if __name__ == "__main__":
    # 環境変数を読み込み
    from dotenv import load_dotenv
    load_dotenv()
    
    # SSE transport で起動
    mcp.run(transport="sse", host="0.0.0.0", port=8001)