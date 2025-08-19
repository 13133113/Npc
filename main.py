from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from typing import Optional

app = FastAPI()

# Безопасность
security = HTTPBearer()

# Разрешаем запросы из Minecraft
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NPCSettings(BaseModel):
    appearance: str
    characteristics: str
    height: str
    speed: str
    isDaytime: bool

class NPCResponse(BaseModel):
    success: bool
    message: str
    appliedSettings: Optional[dict] = None

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    # Простая проверка токена
    expected_tokens = os.getenv("ALLOWED_TOKENS", "").split(",")
    if credentials.credentials in expected_tokens:
        return credentials.credentials
    raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/generate-npc")
async def generate_npc(
    settings: NPCSettings, 
    token: str = Security(verify_token)
):
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai.api_key:
            return NPCResponse(
                success=False,
                message="API ключ OpenAI не настроен на сервере"
            )

        prompt = f"""
        Создай NPC для Minecraft с параметрами:
        Внешность: {settings.appearance}
        Характеристики: {settings.characteristics}
        Рост: {settings.height}
        Скорость: {settings.speed}
        Тип: {'Дневной' if settings.isDaytime else 'Ночной'}
        
        Верни ТОЛЬКО JSON без каких-либо пояснений с полями:
        - description: описание внешности
        - model_data: параметры для модели
        - behavior: поведение и характер
        - abilities: особые способности
        - stats: характеристики (health, damage, speed)
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты создаешь NPC для Minecraft. Возвращай ТОЛЬКО валидный JSON без комментариев."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.7
        )

        npc_data = response.choices[0].message.content
        
        return NPCResponse(
            success=True,
            message="NPC создан успешно",
            appliedSettings={
                "npc_data": npc_data,
                "original_settings": settings.dict()
            }
        )

    except Exception as e:
        return NPCResponse(
            success=False,
            message=f"Ошибка сервера: {str(e)}"
        )

@app.get("/")
async def root():
    return {"message": "NPC AI Server is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
