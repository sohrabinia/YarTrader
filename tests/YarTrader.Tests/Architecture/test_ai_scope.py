from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Research.Brain.live_brain import LiveAnalysisBrain
from src.Research.Brain.cognitive_loop import CognitiveReplayLoop


def test_yartrader_keeps_only_trading_brain_in_product_ai_surface():
    client = TestClient(app)

    # Generic assistant/chat is owned by YarOperator, not YarTrader.
    assert client.post("/api/chat/assistant", json={"message": "hello", "lang": "en"}).status_code == 404

    # Generic growth/content agent APIs are not mounted in the trading product.
    assert client.get("/api/growth/newsletter/weekly").status_code == 404
    assert client.post("/api/growth/content/generate", json={"title": "x", "body": "y", "channels": []}).status_code == 404

    # The actual YarTrader Trading Brain remains part of the product codebase.
    assert LiveAnalysisBrain is not None
    assert CognitiveReplayLoop is not None


def test_trading_brain_has_no_execution_api_dependency():
    import inspect

    source = inspect.getsource(LiveAnalysisBrain)
    forbidden = ("order_send", "send_order", "execute_order", "broker.order")
    assert not any(token in source for token in forbidden)
