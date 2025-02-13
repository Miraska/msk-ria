import random
import asyncio
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright  # Используем синхронный API Playwright
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

RSS_FEED_URL = "https://rss.stopgame.ru/rss_news.xml"


def parse_page(url):
    """Парсинг страницы Stopgame с использованием Playwright"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=PLAYWRIGHT_PROXY)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        # Добавляем задержку для гарантии полной загрузки контента
        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Извлекаем заголовок
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Заголовок не найден"

    # Извлекаем содержимое статьи
    body = soup.find("div", class_="_content_5hrm4_13")
    paragraphs = body.find_all("p") if body else []
    # Удаляем вложенные SVG, если они есть
    for p in paragraphs:
        for svg in p.find_all("svg"):
            svg.decompose()
    content = "\n\n".join(p.decode_contents() for p in paragraphs)

    # Извлекаем URL изображения
    image_div = soup.find("div", class_="_image-wrapper_5hrm4_173 _image-width_5hrm4_116")
    image_url = image_div.find("img")["src"] if image_div and image_div.find("img") else None

    return title, content, image_url


def process_rss():
    """Обработка RSS для Stopgame с использованием Playwright для загрузки страниц"""
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

        # Если в RSS есть enclosure (изображение), используем его
        if random_article.get("enclosure"):
            enclosure = random_article.get("enclosure")
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
            "Гейминг новости",
            image_url,
        )

        if post_id:
            published_link = get_wordpress_post_url(post_id)
            if published_link:
                asyncio.run(
                    send_report("Stopgame Parser", link, published_link, final_title)
                )
                mark_article_as_processed(link)
            else:
                print(f"[ERROR] Не удалось получить URL для поста с ID: {post_id}")
        else:
            print(f"[ERROR] Публикация не удалась для статьи: {final_title}")

        print()
