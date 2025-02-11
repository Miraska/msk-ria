import requests
from bs4 import BeautifulSoup
from telegram_bot import send_report
import asyncio
import random
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

RSS_FEED_URL = "https://www.championat.com/rss/news/"


def parse_page(url):
    """Парсинг страницы Championat"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code != 200:
        print(
            f"[ERROR] Ошибка загрузки страницы со статусом {response.status_code}: {url}"
        )
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    title = soup.find("div", "article-head__title")
    title = title.get_text(strip=True) if title else "Заголовок не найден"

    body = soup.find("div", class_="article-content")

    paragraphs = body.find_all("p") if body else []
    content = "\n\n".join(
        p.decode_contents() for p in paragraphs
    )  # Сохраняем теги <a> в содержимом

    image_div = soup.find("div", "article-head__photo")
    image_url = (
        image_div.find("img")["src"] if image_div and image_div.find("img") else None
    )

    return title, content, image_url


def process_rss():
    """Обработка RSS для Championat"""
    articles = fetch_rss(RSS_FEED_URL)
    print(f"[DEBUG] Найдено {len(articles)} статей.")

    if not articles:
        print("[DEBUG] Нет статей для обработки.")
        return

    for i in range(1):
        # Выбираем случайную статью
        random_article = random.choice(articles)
        link = random_article["link"]

        while True:
            if is_article_processed(link):
                random_article = random.choice(articles)
                link = random_article["link"]
                print(f"[DEBUG] Статья уже обработана: {link}")
                continue
            break

        parsed_data = parse_page(link)
        if not parsed_data:
            return

        title, raw_content, image_url = parsed_data
        print(f"[DEBUG] Заголовок статьи: {title}")

        # Если в RSS есть enclosure (изображение), используем его
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
            "Спортивные новости",
            image_url,
        )

        if post_id:
            published_link = get_wordpress_post_url(post_id)

            if published_link:
                asyncio.run(
                    send_report("Championat Parser", link, published_link, final_title)
                )
                mark_article_as_processed(link)
            else:
                print(f"[ERROR] Не удалось получить URL для поста с ID: {post_id}")
        else:
            print(f"[ERROR] Публикация не удалась для статьи: {final_title}")

        print()
