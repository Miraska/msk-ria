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
    check_and_crop_image
)

RSS_FEED_URL = "https://www.moscowtimes.ru/rss/news"


def parse_page(url):
    """Парсинг страницы The Moscow Times"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[ERROR] Ошибка загрузки страницы: {url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    title_tag = soup.find("header", class_="article__header").find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Заголовок не найден"

    content_div = soup.find("div", class_="article__content")
    paragraphs = content_div.find_all("p") if content_div else []
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

    image_tag = soup.find("figure", class_="article__featured-image")
    if image_tag and image_tag.find("img"):
        img = image_tag.find("img")
        image_url = img.get("src")
        srcset = img.get("srcset")
        if srcset:
            image_url = srcset.split(",")[0].split(" ")[0].strip()
        else:
            image_url = img.get("src")
    else:
        image_url = None

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
            mark_article_as_processed(link)
            i -= 1
            continue

        # Проверка и обрезка изображения
        image_url = check_and_crop_image(image_url)

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
            "Мировые новости",
            image_url,
        )

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