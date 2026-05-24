import aiohttp

TAVILY_API_URL = "https://api.tavily.com/search"

# Ключевые слова которые говорят что нужен актуальный поиск
SEARCH_TRIGGERS = [
    "вчера", "сегодня", "сейчас", "последние", "свежие", "новости",
    "недавно", "только что", "на этой неделе", "в этом месяце", "в этом году",
    "2024", "2025", "2026",
    "матч", "игра", "результат", "счёт", "победил", "выиграл", "проиграл",
    "трансфер", "чемпионат", "турнир", "выборы", "война", "конфликт",
    "курс", "цена акций", "биржа",
    "вышел", "анонс", "релиз", "запустили", "открыли", "закрыли",
    "who won", "latest", "recent", "today", "yesterday", "this week",
    "score", "match", "news", "update"
]


def needs_search(text: str) -> bool:
    """Определяет нужен ли веб-поиск для ответа на вопрос"""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in SEARCH_TRIGGERS)


async def web_search(query: str, api_key: str, max_results: int = 3) -> str | None:
    """Выполняет поиск через Tavily и возвращает краткий результат"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True
            }
            async with session.post(
                TAVILY_API_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

                # Если Tavily дал готовый ответ — используем его
                if data.get("answer"):
                    return data["answer"]

                # Иначе собираем из результатов
                results = data.get("results", [])
                if not results:
                    return None

                snippets = []
                for r in results[:max_results]:
                    title = r.get("title", "")
                    content = r.get("content", "")[:300]
                    snippets.append(f"• {title}: {content}")

                return "\n".join(snippets)
    except Exception:
        return None
