import random
import asyncio
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

RSS_FEED_URL = "https://ria.ru/export/rss2/archive/index.xml"


def parse_page(url):
    """Парсинг страницы RIA с использованием Playwright"""
    with sync_playwright() as p:
        # Запускаем Chromium в headless-режиме
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        # При необходимости можно добавить задержку, чтобы контент точно загрузился
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Извлекаем заголовок
    title_div = soup.find("div", class_="article__title")
    title = title_div.get_text(strip=True) if title_div else "Заголовок не найден"

    # Извлекаем тело статьи: находим div с классом "article__body"
    body = soup.find("div", class_="article__body")
    paragraphs = body.find_all("div", class_="article__text") if body else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

    # Извлекаем URL изображения: ищем div с классом "media__size" и затем тег <img>
    image_div = soup.find("div", class_="media__size")
    image_url = image_div.find("img")["src"] if image_div and image_div.find("img") else None

    return title, content, image_url


def process_rss():
    """Обработка RSS для RIA с использованием Playwright для загрузки страниц"""
    articles = fetch_rss(RSS_FEED_URL)
    print(f"[DEBUG] Найдено {len(articles)} статей.")

    if not articles:
        print("[DEBUG] Нет статей для обработки.")
        return

    # Обрабатываем одну случайную статью (для примера)
    for i in range(1):
        random_article = random.choice(articles)
        link = random_article["link"]

        # Если статья уже обработана, выбираем другую
        while is_article_processed(link):
            random_article = random.choice(articles)
            link = random_article["link"]
            print(f"[DEBUG] Статья уже обработана: {link}")

        parsed_data = parse_page(link)
        if not parsed_data:
            return

        title, raw_content, image_url = parsed_data
        print(f"[DEBUG] Заголовок статьи: {title}")

        # Если в RSS есть enclosure (изображение), используем его, если содержит "image/jpeg"
        if random_article.get("enclosure"):
            enclosure = random_article.get("enclosure")
            if "image/jpeg" in enclosure:
                image_url = enclosure

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
            "Российские новости",
            image_url,
        )

        if post_id:
            published_link = get_wordpress_post_url(post_id)
            if published_link:
                asyncio.run(
                    send_report("Ria Parser", link, published_link, final_title)
                )
                mark_article_as_processed(link)
            else:
                print(f"[ERROR] Не удалось получить URL для поста с ID: {post_id}")
        else:
            print(f"[ERROR] Публикация не удалась для статьи: {final_title}")

        print()
