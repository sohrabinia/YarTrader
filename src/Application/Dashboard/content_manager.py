import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("ContentManager")

class ContentManager:
    """
    Manages persistent online data for Blog, News, FAQ, Guide articles, and admin management.
    Saves state persistently to file-based database runtime_logs/content.json.
    """
    def __init__(self, filepath: str = "runtime_logs/content.json") -> None:
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.data: Dict[str, Any] = self._load_db()

    def _get_default_content(self) -> Dict[str, Any]:
        return {
            "blog": [
                {
                    "id": "1",
                    "title": "Decoupling Market Reality: The Death of Classical Technical Indicators",
                    "category": "Algorithmic Research",
                    "author": "Dr. Aras Noori",
                    "published_at": "2026-08-15",
                    "content": "Classical indicators like RSI, EMA, and MACD fail because they compress non-linear tick sequences into delayed, lossy broker candles. In v3.2, YarTrader replaces MT5 standard timeframes entirely with integer tick-bar structures, enabling raw price-action similarity detection without subjective bias.",
                    "summary": "Classical indicators fail. YarTrader replaces timeframes with integer tick-bar structures.",
                    "slug": "decoupling-market-reality",
                    "published": True
                },
                {
                    "id": "2",
                    "title": "Implementing Autonomous Shadow Execution under APES-Standard Guidelines",
                    "category": "Platform Governance",
                    "author": "SRE Architecture Lead",
                    "published_at": "2026-08-10",
                    "content": "To meet strict simulation-only constraints, YarTrader operates a virtual wallet position lifecycle tracker called the Shadow Trading Engine. Closed positions are retrospectively audited by an independent Judge Brain and stored to cumulative Experience Memory databases.",
                    "summary": "Virtual wallet position lifecycle tracker under simulation-only constraints.",
                    "slug": "shadow-execution-apes",
                    "published": True
                }
            ],
            "news": [
                {
                    "id": "news-2026-03-30",
                    "title": "انتشار نسخه جدید YarTrader v7.0 با پشتیبانی از هوش مصنوعی فرکتال",
                    "source": "YarTrader Newsroom",
                    "published_at": "2026-03-30T10:00:00Z",
                    "category": "Platform Update",
                    "summary": "پلتفرم هوشمند YarTrader نسخه 7.0 خود را با قابلیت‌های پیشرفته تحلیل ساختاری و احراز هویت تلگرام عرضه کرد.",
                    "content": "امروز سامانه YarTrader v7.0 به‌طور رسمی راه‌اندازی شد. این نسخه شامل به‌روزرسانی‌های زیرساختی SRE، ارتباطات امن تلگرام و رابط کاربری ۵ زبانه است.",
                    "slug": "yartrader-v7-release"
                }
            ],
            "faq": [
                {
                    "id": "faq-1",
                    "category": "General",
                    "question": "سامانه YarTrader چیست و چه تفاوتی با ترمینال‌های سنتی دارد؟",
                    "answer": "YarTrader یک پلتفرم خودکار مدیریت و پژوهش هوشمند ساختار بازار است که به‌جای اندیکاتورهای تأخیری، از تحلیل فرکتال دیتای خام و مدل‌های پیشرفته شناختی استفاده می‌کند."
                },
                {
                    "id": "faq-2",
                    "category": "Trading Safety",
                    "question": "آیا معاملات در این سامانه دارای ریسک سرمایه واقعی است؟",
                    "answer": "خیر، سامانه به صورت سخت‌افزاری بر روی حالت شبیه‌سازی (Shadow/DEMO) قفل شده است (LIVE_TRADING_ENABLED=False) و هیچ اردر واقعی اجرا نمی‌شود."
                }
            ],
            "guide": [
                {
                    "id": "getting-started",
                    "title": "راهنمای شروع سریع با YarTrader",
                    "category": "Getting Started",
                    "summary": "چگونه حساب کاربری بسازیم، وارد سامانه شویم و سیگنال‌های فرکتال را بررسی کنیم.",
                    "content": "گام ۱: از طریق فرم ثبت‌نام یا ورود تلگرام وارد حساب خود شوید.\nگام ۲: بخش هوش اجرای ساختاری را جهت مشاهده سیگنال‌های فعال بررسی کنید."
                }
            ]
        }

    def _load_db(self) -> Dict[str, Any]:
        if not os.path.exists(self.filepath):
            defaults = self._get_default_content()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(defaults, f, indent=4, ensure_ascii=False)
            return defaults
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                defaults = self._get_default_content()
                for k, default_list in defaults.items():
                    if k not in loaded or not loaded[k]:
                        loaded[k] = default_list
                    else:
                        existing_ids = {item.get("id") for item in loaded[k]}
                        for def_item in default_list:
                            if def_item.get("id") not in existing_ids:
                                loaded[k].append(def_item)
                return loaded
        except Exception as e:
            logger.error(f"Error loading content database: {e}")
            return self._get_default_content()

    def save_db(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving content database: {e}")

    def get_blog_articles(self) -> List[Dict[str, Any]]:
        return self.data.get("blog", [])

    def get_news(self) -> List[Dict[str, Any]]:
        return self.data.get("news", [])

    def get_faqs(self) -> List[Dict[str, Any]]:
        return self.data.get("faq", [])

    def get_guides(self) -> List[Dict[str, Any]]:
        return self.data.get("guide", [])

    def add_content_item(self, domain: str, item: Dict[str, Any]) -> Dict[str, Any]:
        if domain not in self.data:
            self.data[domain] = []
        if not item.get("id"):
            item["id"] = f"{domain}-{int(datetime.now(timezone.utc).timestamp())}"
        self.data[domain].insert(0, item)
        self.save_db()
        return item
