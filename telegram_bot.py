from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

async def send_report(parser_name, original_link, published_link, title):
    """
    Отправляет отчёт в Telegram.
    """
    message = (
        f"<b>Парсер:</b> {parser_name}\n"
        f"<b>Исходная ссылка:</b> <a href='{original_link}'>{original_link}</a>\n"
        f"<b>Опубликованная ссылка:</b> <a href='{published_link}'>{published_link}</a>\n"
        f"<b>Название статьи:</b> {title}"
    )
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
        print(f"[DEBUG] Отчёт отправлен в Telegram")
    except Exception as e:
        print(f"[ERROR] Ошибка отправки отчёта в Telegram: {e}")

if __name__ == "__main__":
    async def main():
        await send_report(
            parser_name="Test Parser",
            original_link="https://example.com/original",
            published_link="https://example.com/published",
            title="Тестовая статья"
        )
    executor.start(dp, main())
