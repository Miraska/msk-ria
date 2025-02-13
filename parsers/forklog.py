import random
import asyncio
import time
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
)

# Прокси для Playwright (формат отличается от requests)
PLAYWRIGHT_PROXY = {
    "server": "http://163.5.39.69:2966",
    "username": "user215587",
    "password": "rfqa06"
}

RSS_FEED_URL = "https://forklog.com/feed"


def parse_page(url):
    """Парсинг страницы Forklog с использованием Playwright"""
    with sync_playwright() as p:
        # Запускаем Chromium в headless-режиме с прокси
        browser = p.chromium.launch(headless=True, proxy=PLAYWRIGHT_PROXY)
        page = browser.new_page()
        # Переходим на страницу и ждём загрузки DOM
        page.goto(url, wait_until="domcontentloaded")
        # Добавляем небольшую задержку, если требуется (например, 3 секунды)
        page.wait_for_timeout(3000)
        # Получаем HTML-код после рендеринга
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Извлекаем заголовок (ищем первый тег <h1>)
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Заголовок не найден"

    # Извлекаем основной контент: div с классом "post_content"
    body = soup.find("div", class_="post_content")
    paragraphs = body.find_all("p") if body else []
    # Сохраняем содержимое тегов (в т.ч. внутренние ссылки) и исключаем абзацы, где встречается слово "forklog"
    content = "\n\n".join(
        p.decode_contents() for p in paragraphs if "forklog" not in p.get_text(strip=True).lower()
    )

    # Извлекаем URL изображения: div с классом "article_image"
    image_div = soup.find("div", class_="article_image")
    image_url = image_div.find("img")["src"] if image_div and image_div.find("img") else None

    return title, content, image_url


def process_rss():
    """Обработка RSS для Forklog с использованием Playwright для загрузки страниц"""
    # Если внутри fetch_rss используются запросы, возможно потребуется передать прокси и туда.
    articles = fetch_rss(RSS_FEED_URL)
    print(f"[DEBUG] Найдено {len(articles)} статей.")

    if not articles:
        print("[DEBUG] Нет статей для обработки.")
        return

    for i in range(1):
        # Выбираем случайную статью
        random_article = random.choice(articles)
        link = random_article["link"]

        # Если статья уже обработана – выбираем другую
        while is_article_processed(link):
            random_article = random.choice(articles)
            link = random_article["link"]
            print(f"[DEBUG] Статья уже обработана: {link}")
        
        parsed_data = parse_page(link)
        if not parsed_data:
            return

        title, raw_content, image_url = parsed_data
        print(f"[DEBUG] Заголовок статьи: {title}")

        # Если в RSS есть enclosure (изображение), используем его вместо полученного
        if random_article.get("enclosure"):
            image_url = random_article["enclosure"]

        if not image_url:
            print("[Warning] Статья не опубликована из-за отсутствия изображения")
            mark_article_as_processed(link)
            i -= 1
            continue

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

        mark_article_as_processed(link)

        post_id = publish_to_wordpress(
            final_title,
            rewritten_content,
            final_meta_title,
            meta_description,
            "Крипто новости",
            image_url,
        )

        if post_id:
            published_link = get_wordpress_post_url(post_id)
            if published_link:
                asyncio.run(
                    send_report("Forklog Parser", link, published_link, final_title)
                )
                mark_article_as_processed(link)
            else:
                print(f"[ERROR] Не удалось получить URL для поста с ID: {post_id}")
        else:
            print(f"[ERROR] Публикация не удалась для статьи: {final_title}")

        print()
