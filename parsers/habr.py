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

RSS_FEED_URL = "https://habr.com/ru/rss/news/?fl=ru"


def parse_page(url):
    """Парсинг страницы Habr с использованием Playwright"""
    with sync_playwright() as p:
        # Запускаем Chromium в headless-режиме
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Переходим на страницу и ждём загрузки DOM
        page.goto(url, wait_until="domcontentloaded")
        # Ждём, чтобы страница полностью прогрузилась (при необходимости можно увеличить время)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Извлекаем заголовок: ищем <h1> и затем его дочерний <span> (если есть)
    h1_tag = soup.find("h1")
    if h1_tag:
        span_tag = h1_tag.find("span")
        title = span_tag.get_text(strip=True) if span_tag else h1_tag.get_text(strip=True)
    else:
        title = "Заголовок не найден"

    # Извлекаем основной контент: div с классом "tm-article-body"
    body = soup.find("div", class_="tm-article-body")
    paragraphs = body.find_all("p") if body else []
    content = "\n\n".join(p.decode_contents() for p in paragraphs)

    # Извлекаем URL изображения: ищем первый <figure> и затем тег <img>
    image_div = soup.find("figure")
    if image_div:
        img_tag = image_div.find("img")
        image_url = img_tag.get("data-src") if img_tag else None
    else:
        image_url = None

    return title, content, image_url


def process_rss():
    """Обработка RSS для Habr с использованием Playwright для загрузки страниц"""
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

        # Если в RSS есть enclosure (изображение), используем его
        if random_article.get("enclosure"):
            image_url = random_article["enclosure"]

        if not image_url:
            print("[DEBUG] Пропускаем статью, т.к. не найдено изображение")
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
            "Технологичные новости",
            image_url,
        )

        if post_id:
            published_link = get_wordpress_post_url(post_id)
            if published_link:
                asyncio.run(
                    send_report("Habr Parser", link, published_link, final_title)
                )
                mark_article_as_processed(link)
            else:
                print(f"[ERROR] Не удалось получить URL для поста с ID: {post_id}")
        else:
            print(f"[ERROR] Публикация не удалась для статьи: {final_title}")

        print()
