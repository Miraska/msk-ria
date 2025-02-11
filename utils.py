import sqlite3
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import xml.etree.ElementTree as ET
from config import DB_NAME, WP_URL, WP_USERNAME, WP_PASSWORD, openai_api_key
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.methods.media import UploadFile
from wordpress_xmlrpc.methods.posts import GetPost
from wordpress_xmlrpc.methods.taxonomies import GetTerms
import re
import time
import logging
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

wp_client = Client(WP_URL, WP_USERNAME, WP_PASSWORD)

# Создание объекта PoolManager с отключенной проверкой сертификатов
http = urllib3.PoolManager(
    cert_reqs='CERT_NONE',  # Отключаем проверку сертификатов
    assert_hostname=False    # Отключаем проверку хоста
)
urllib3.disable_warnings(InsecureRequestWarning)

def setup_database():
    """Создание таблицы для хранения обработанных статей"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()

def is_article_processed(link):
    """Проверка, была ли статья уже обработана"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_articles WHERE link = ?", (link,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_article_as_processed(link):
    """Пометка статьи как обработанной"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO processed_articles (link) VALUES (?)", (link,)
    )
    conn.commit()
    conn.close()

def fetch_rss(rss_url):
    """Получение и разбор RSS"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    try:
        response = http.requests('GET', rss_url, headers=headers, timeout=10)
        
        if response.status != 200:
            logger.error(f"Ошибка загрузки RSS: {response.status}")
            return []

        root = ET.fromstring(response.data)

        return [
            {
                "title": item.find("title").text,
                "link": item.find("link").text,
                "enclosure": (
                    item.find("enclosure").attrib.get("url")
                    if item.find("enclosure") is not None
                    else None
                ),
                "pubDate": item.find("pubDate").text,
            }
            for item in root.findall(".//item")
        ]
    except Exception as e:
        logger.error(f"Ошибка получения RSS: {e}")
        return []

def clean_text(content):
    """Очищает текст от ненужных элементов"""
    match_ria = re.match(r"^[^.!?]*?РИА Новости[.!?]", content)
    if match_ria:
        content = content[match_ria.end() :].strip()

    match_reuters = re.match(
        r"^[^.!?]*?[А-ЯЁ][а-яё]+, \d{1,2} \w+ \(Рейтер\) —", content
    )
    if match_reuters:
        content = content[match_reuters.end() :].strip()

    return content

def clean_title(title):
    """Очищает заголовки"""
    title = title.replace("Заголовок: ", "").strip()
    title = title.replace("**Заголовок:**", "").strip()
    title = title.replace("**", "").strip()
    title = title.replace('"', "").replace("'", "").strip()
    return title

def rewrite_text(text, prompt):
    import openai

    openai.api_key = openai_api_key

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": f"{prompt}\n\n{text}"}]
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Ошибка рерайта текста: {e}")
        return text

def generate_meta(title, content):
    """Генерация SEO мета-тегов"""
    meta_title = rewrite_text(title, "Создай короткий SEO-заголовок:")
    meta_description = rewrite_text(content, "Создай описание длиной до 160 символов:")
    return meta_title, meta_description

# Публикация поста с отлавливанием ошибок
def publish_to_wordpress(title, content, meta_title, meta_description, category=None, image_url=None):
    post = WordPressPost()
    post.title = title
    post.content = content
    post.post_status = "publish"
    post.custom_fields = [
        {"key": "_yoast_wpseo_title", "value": meta_title},
        {"key": "_yoast_wpseo_metadesc", "value": meta_description},
    ]

    if image_url:
        image_id, _ = upload_image_to_wordpress(image_url)
        if image_id:
            post.thumbnail = image_id
    else:
        logger.warning("Статья не опубликована из-за отсутствия изображения")
        return

    if category:
        category_id = get_category_id_by_name(category)
        if category_id:
            post.terms_names = {"category": [category]}  # Указываем категорию
        else:
            logger.warning(f"Категория '{category}' не будет добавлена к посту.")
            return

    try:
        post_id = wp_client.call(NewPost(post))
        logger.info(f"Статья '{title}' успешно опубликована. ID: {post_id}")
        return post_id
    except Exception as e:
        logger.error(f"Ошибка публикации статьи: {e}")
        return None

def get_wordpress_post_url(post_id):
    """
    Получение URL опубликованного поста по его ID.
    """
    try:
        post = wp_client.call(GetPost(post_id))
        return post.link
    except Exception as e:
        logger.error(f"Не удалось получить URL поста: {e}")
        return None

def get_category_id_by_name(category_name):
    """Получает ID категории по её названию."""
    try:
        categories = wp_client.call(GetTerms("category", search=category_name))
        for category in categories:
            if category.name == category_name:
                return category.id
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении категории: {e}")
        return None

def download_image(image_url):
    """
    Загружает изображение по URL, игнорируя SSL-ошибки.
    """
    try:
        response = requests.get(image_url, timeout=10, verify=False)
        response.raise_for_status()  # Проверяем, что статус 200 OK
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка загрузки изображения: {e}")
        return None
def upload_image_to_wordpress(image_url):
    """
    Загружает изображение в WordPress.
    Возвращает ID изображения и его URL, если успешно.
    """
    try:
        img_data = download_image(image_url)

        if not img_data:
            logger.error("Не удалось загрузить изображение, отмена публикации.")
            return None, None

        image_name = image_url.split("/")[-1]  # Извлекаем имя файла
        image_data = {
            "name": image_name,
            "type": "image/jpeg",
            "bits": img_data,
        }

        # Загрузка изображения в WordPress
        upload_response = wp_client.call(UploadFile(image_data))
        logger.info(f"Изображение '{image_name}' успешно загружено в WordPress: {upload_response['url']}")
        
        return upload_response["id"], upload_response["url"]
    
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения в WordPress: {e}")
        return None, None

def check_and_crop_image(image_url):
    """Проверка изображения на наличие слова 'Reuters' и обрезка на 10% сверху и снизу"""
    try:
        # Здесь вы можете раскомментировать код для обработки изображений, если это необходимо.
        return image_url
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        return image_url
