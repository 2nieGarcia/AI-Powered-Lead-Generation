from supabase import create_client, Client
from core.config import Config
from services.evaluator.embedding import embed_text
import logging
import asyncio

logger = logging.getLogger(__name__)

def get_supabase() -> Client:
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

async def get_rag_context(business_name: str, category: str = "") -> dict:
    default = {
        "success_synthesis": "No historical reference available.",
        "success_business": None,
        "success_score": None,
        "success_similarity": 0.0,
        "blacklist_synthesis": "No historical reference available.",
        "blacklist_name": None,
        "blacklist_reason": None,
        "blacklist_similarity": 0.0
    }

    try:
        query_text = f"{business_name} {category}".strip()
        
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(None, embed_text, query_text)
        
        supabase = get_supabase()

        success_res = await loop.run_in_executor(
            None,
            lambda: supabase.rpc(
                'match_historical_leads',
                {'query_embedding': query_embedding, 'match_count': 1, 'target_status': 'success'}
            ).execute()
        )

        blacklist_res = await loop.run_in_executor(
            None,
            lambda: supabase.rpc(
                'match_historical_leads',
                {'query_embedding': query_embedding, 'match_count': 1, 'target_status': 'blacklist'}
            ).execute()
        )

        if success_res.data:
            row = success_res.data[0]
            default["success_synthesis"] = row.get("the_reasoning", default["success_synthesis"])
            default["success_business"] = row.get("business_name")
            default["success_score"] = row.get("agency_fit_score")
            default["success_similarity"] = round(row.get("similarity", 0.0), 3)

        if blacklist_res.data:
            row = blacklist_res.data[0]
            default["blacklist_synthesis"] = row.get("the_reasoning", default["blacklist_synthesis"])
            default["blacklist_name"] = row.get("business_name")
            default["blacklist_reason"] = row.get("the_reasoning")
            default["blacklist_similarity"] = round(row.get("similarity", 0.0), 3)

        logger.info(f"RAG context fetched for: {business_name}")
        return default

    except Exception as e:
        logger.warning(f"RAG query failed (cold start safe): {e}")
        return default


async def update_record_vector(table_name: str, record_id: int, text: str) -> bool:
    try:
        supabase = get_supabase()
        
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, embed_text, text)

        await loop.run_in_executor(
            None,
            lambda: supabase.table(table_name)\
                .update({"vector_layer": embedding})\
                .eq("id", record_id)\
                .execute()
        )
        
        logger.info(f"Vector saved to {table_name} ID: {record_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save vector: {e}")
        raise