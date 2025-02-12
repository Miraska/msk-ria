import asyncio
import random
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright  # Синхронный API Playwright
from telegram_bot import send_report

from utils import (
    fetch_rss,
    is_article_processed,
    mark_article_as_processed,
    publish_to_wordpress,
    clean_text,
    clean_title,
    rewrite_text,
    generate_meta,
    get_wordpress_post_url,
    check_and_crop_image
)

# Если хотите подключить прокси:
PLAYWRIGHT_PROXY = {
    "server": "http://163.5.39.69:2966",
    "username": "user215587",
    "password": "rfqa06"
}

RSS_FEED_URL = "https://www.moscowtimes.ru/rss/news"

print(45546)

def parse_page(url):
    """
    Парсинг страницы The Moscow Times при помощи Playwright.
    Возвращает (title, content, image_url), как и раньше.
    """
    # Создаём контекст Playwright в синхронном режиме
    with sync_playwright() as p:
        # Запускаем Chromium (headless=True – без граф. интерфейса)
        # Если нужна прокси — передаём её в параметр `proxy`.
        browser = p.chromium.launch(
            headless=True,
            proxy=PLAYWRIGHT_PROXY  # Если прокси не нужен, закомментируйте эту строку
        )
        page = browser.new_page()

        # Переходим на страницу
        page.goto(url, wait_until="domcontentloaded")
        # Можно добавить небольшую задержку, если сайт грузится долго
        # page.wait_for_timeout(3000)

        # Получаем HTML-код после рендеринга
        html = page.content()

        # Закрываем браузер (в рамках with-блока он закроется автоматически, но лишний раз не помешает)
        browser.close()

    # Теперь парсим полученный HTML как и раньше
    soup = BeautifulSoup(html, "html.parser")

    # Извлекаем заголовок
    header = soup.find("header", class_="article__header")
    title_tag = header.find("h1") if header else None
    title = title_tag.get_text(strip=True) if title_tag else "Заголовок не найден"

    # Извлекаем контент
    content_div = soup.find("div", class_="article__content")
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

    # Извлекаем изображение
    image_tag = soup.find("figure", class_="article__featured-image")
    image_url = None
    if image_tag and image_tag.find("img"):
        img = image_tag.find("img")
        srcset = img.get("srcset")
        if srcset:
            image_url = srcset.split(",")[0].split(" ")[0].strip()
        else:
            image_url = img.get("src")

    return title, content, image_url


def process_rss():
    """Обработка RSS для The Moscow Times"""
    articles = fetch_rss(RSS_FEED_URL)
    print(f"[DEBUG] Найдено {len(articles)} статей.")

    if not articles:
        print("[DEBUG] Нет статей для обработки.")
        return

    for i in range(1):
        # Выбираем случайную статью
        random_article = random.choice(articles)
        link = random_article["link"]

        # Проверка, не обработана ли статья ранее
        while True:
            if is_article_processed(link):
                random_article = random.choice(articles)
                link = random_article["link"]
                print(f"[DEBUG] Статья уже обработана: {link}")
                continue
            break

        # Парсим страницу через Playwright
        parsed_data = parse_page(link)
        if not parsed_data:
            return  # или continue

        title, raw_content, image_url = parsed_data
        print(f"[DEBUG] Заголовок статьи: {title}")

        # Если в RSS есть enclosure (изображение), используем его
        if random_article.get("enclosure"):
            image_url = random_article["enclosure"]

        # Если нет изображения, пропускаем
        if not image_url:
            mark_article_as_processed(link)
            i -= 1
            continue

        # Проверка и обрезка изображения (если у вас такая логика есть)
        image_url = check_and_crop_image(image_url)

        # Чистим и переписываем контент
        cleaned_content = clean_text(raw_content)

        rewritten_title = rewrite_text(
            f"Заголовок: {title}\n\nТекст: {cleaned_content}",
            "Создай уникальный заголовок на основе следующего текста статьи и исходного заголовка:",
        )
        rewritten_content = rewrite_text(
            cleaned_content,
            "Перепиши этот текст с уникальными формулировками, сохраняя смысл:",
        )

        final_title = clean_title(rewritten_title)

        meta_title, meta_description = generate_meta(final_title, rewritten_content)
        final_meta_title = clean_title(meta_title)

        # Отмечаем как обработанную
        mark_article_as_processed(link)

        # Публикуем в WordPress (остаётся прежний метод)
        post_id = publish_to_wordpress(
            final_title,
            rewritten_content,
            final_meta_title,
            meta_description,
            "Мировые новости",
            image_url,
        )

        # Проверяем результат публикации
        if post_id:
            published_link = get_wordpress_post_url(post_id)
            if published_link:
                asyncio.run(
                    send_report("Moscow Times Parser", link, published_link, final_title)
                )
                mark_article_as_processed(link)
            else:
                print(f"[ERROR] Не удалось получить URL для поста с ID: {post_id}")
        else:
            print(f"[ERROR] Публикация не удалась для статьи: {final_title}")

        print()
