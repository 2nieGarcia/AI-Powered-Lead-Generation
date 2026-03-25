from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_supabase
from supabase import Client

router = APIRouter()

@router.get("/blacklist")
def get_blacklist(supabase: Client = Depends(get_supabase)):
    try:
        response = supabase.table("blacklist").select("*").execute()
        names = [item['name'] for item in response.data]
        return {"blacklist": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



