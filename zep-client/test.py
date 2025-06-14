import os
import asyncio
from zep_python.client import AsyncZep
from zep_python.types import Message
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("ZEP_API_SECRET")
if not API_KEY:
    raise ValueError("ZEP_API_SECRET environment variable is required")

BASE_URL = "http://localhost:8000"

async def main():
    zep = AsyncZep(
        api_key=API_KEY,
        base_url=BASE_URL
    )

    user_id = uuid.uuid4().hex

    new_user = await zep.user.add(
        user_id=user_id,
        email="yamada.taro@example.com",
        first_name="太郎",
        last_name="山田",
        metadata={
            "gender": "male",
            "age": 30,
        },
    )
    print(new_user.dict())

    # セッション作成
    session_id = uuid.uuid4().hex
    session = await zep.memory.add_session(
        session_id=session_id,
        user_id=user_id
    )
    print(session.dict())

    # チャット履歴を追加
    await zep.memory.add(
        session_id=session_id,
        messages=[
            Message(
                role="Taka",
                content="私はラーメンが好きです",
                role_type="user",
            ),
            Message(
                role="AI Assistant",
                content="ラーメンがお好きなんですね！",
                role_type="assistant",
            )
        ]
    )
    
    # メモリ取得
    memory = await zep.memory.get(session_id=session_id)
    # メッセージ取得（会話履歴のリスト）
    messages = memory.messages
    for m in messages:
        print(m.role_type, ":", m.content)
    # メッセージから取り出された事実の取得（最近のメッセージに関連する事実のリスト）
    relevant_facts = memory.relevant_facts
    for fact in relevant_facts:
        print(fact.fact)
    
    # メモリ検索
    search_response = await zep.memory.search_sessions(
        user_id=user_id,
        search_scope="facts",
        text="趣味は何？",
    )
    facts = [r.fact for r in search_response.results]
    for fact in facts:
        print(fact.fact)

if __name__ == "__main__":
    asyncio.run(main())