import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI()

# Раздаём статику (наш index.html)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище сессий в памяти (в реальном проекте – Redis)
sessions = {}

# ----- "NLU" и генерация ответов (заглушка) -----
def detect_intent(text: str) -> str:
    """Простой детектор намерений по ключевым словам."""
    t = text.lower()
    if any(word in t for word in ["цена", "стоит", "прайс"]):
        return "узнать_цену"
    elif any(word in t for word in ["хар", "характеристики", "описание"]):
        return "характеристики"
    elif any(word in t for word in ["контакт", "телефон", "адрес"]):
        return "контакты"
    else:
        return "общий_вопрос"

def generate_response(intent: str, session: dict) -> dict:
    """
    Генерирует ответ с текстом и UI-командами.
    Возвращает словарь: {"message": str, "commands": list[dict]}.
    """
    # Сохраняем намерение в сессии для демонстрации контекста
    session["last_intent"] = intent

    if intent == "узнать_цену":
        return {
            "message": "Цены на iPhone 15 указаны в карточке товара ниже. Я подсветил её для вас.",
            "commands": [
                {
                    "action": "highlight",
                    "selector": "#product-iphone",
                    "duration": 3000
                },
                {
                    "action": "scrollTo",
                    "selector": "#product-iphone"
                }
            ]
        }
    elif intent == "характеристики":
        return {
            "message": "Характеристики товара можно посмотреть прямо на странице. Я прокрутил к блоку с характеристиками.",
            "commands": [
                {
                    "action": "scrollTo",
                    "selector": "#product-iphone .specs"
                }
            ]
        }
    elif intent == "контакты":
        return {
            "message": "Наши контакты вы видите внизу страницы. Также я открываю форму обратной связи.",
            "commands": [
                {
                    "action": "scrollTo",
                    "selector": "#contacts"
                },
                {
                    "action": "openModal",
                    "selector": "#contact-modal"
                }
            ]
        }
    else:
        return {
            "message": "Я пока не знаю ответа на этот вопрос. Но вы можете задать другой.",
            "commands": []
        }

# ----- WebSocket-эндпоинт -----
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    # Инициализируем сессию (в реальном проекте связываем с ID пользователя)
    sessions[client_id] = {"last_intent": None}
    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_json()
            user_message = data.get("text", "")

            # 1. Определяем намерение
            intent = detect_intent(user_message)

            # 2. Генерируем ответ (текст + UI-команды)
            response = generate_response(intent, sessions[client_id])

            # 3. Отправляем ответ обратно в браузер
            await websocket.send_json(response)

    except WebSocketDisconnect:
        # Удаляем сессию при отключении
        sessions.pop(client_id, None)
    except Exception as e:
        print(f"Error: {e}")
        sessions.pop(client_id, None)

# Корневой эндпоинт отдаёт наш тестовый сайт
@app.get("/")
async def get():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)