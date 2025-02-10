import requests
from bs4 import BeautifulSoup
import openai
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.methods.media import UploadFile
import re
import xml.etree.ElementTree as ET
import sqlite3
import schedule
import time

RSS_FEED_URL = 'URL' 
WP_URL = 'URL'
WP_USERNAME = 'USER'
WP_PASSWORD = 'PASS'
openai.api_key = 'KEY'
DB_NAME = r'DB'  

wp_client = Client(WP_URL, WP_USERNAME, WP_PASSWORD)

def setup_database():
    """Создание таблицы для хранения обработанных статей"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DEBUG] База данных '{DB_NAME}' готова к использованию.")

def is_article_processed(article_link):
    """Проверка, была ли статья уже обработана"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_articles WHERE link = ?", (article_link,))
    result = cursor.fetchone()
    conn.close()
    if result:
        print(f"[DEBUG] Статья уже обработана: {article_link}")
    else:
        print(f"[DEBUG] Статья не обработана: {article_link}")
    return result is not None

def mark_article_as_processed(article_link):
    """Пометка статьи как обработанной"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO processed_articles (link) VALUES (?)", (article_link,))
        conn.commit()
        print(f"[DEBUG] Статья помечена как обработанная: {article_link}")
    except sqlite3.IntegrityError:
        print(f"[WARNING] Статья уже помечена: {article_link}")
    except Exception as e:
        print(f"[ERROR] Ошибка записи в базу данных: {e}")
    finally:
        conn.close()

def fetch_rss():
    """Получение и разбор RSS-ленты"""
    print("[DEBUG] Получение RSS-ленты...")
    response = requests.get(RSS_FEED_URL)
    if response.status_code != 200:
        print(f"[ERROR] Ошибка загрузки RSS: {response.status_code}")
        return []

    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title = item.find("title").text
        link = item.find("link").text
        pub_date = item.find("pubDate").text
        items.append({"title": title, "link": link, "pubDate": pub_date})
    print(f"[DEBUG] Найдено {len(items)} статей в RSS.")
    return items

def parse_page(url):
    """Парсинг страницы по URL"""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Ошибка загрузки страницы: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('div', class_='article__title')
    title = title.get_text(strip=True) if title else "Заголовок не найден"

    body_div = soup.find('div', class_='article__body')
    if body_div:
        paragraphs = body_div.find_all('div', class_='article__text')
        content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
    else:
        content = "Контент статьи не найден"

    image_div = soup.find('div', class_='media__size')
    image_url = image_div.find('img')['src'] if image_div and image_div.find('img') else None

    return title, content, image_url

def clean_text(content):
    """
    Убирает первое предложение, заканчивающееся на 'РИА Новости'.
    """
    match = re.match(r'^[^.!?]*?РИА Новости[.!?]', content)
    if match:
        content = content[match.end():].strip()
    return content

def clean_title(title):
    """
    Удаляет "Заголовок: ", кавычки и другие ненужные элементы из заголовка.
    """
    title = title.replace("Заголовок: ", "").strip()  
    title = title.replace('"', '').replace("'", "")  
    return title

def rewrite_text(text, prompt):
    """Рерайт текста через OpenAI Chat API"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ]
        )
        rewritten_text = response['choices'][0]['message']['content'].strip()
        return rewritten_text if rewritten_text else text
    except Exception as e:
        print(f"[ERROR] Ошибка рерайта текста: {e}")
        return text

def generate_meta(title, content):
    """Генерация мета-тегов title и description"""
    meta_title_prompt = "Создай короткий и информативный SEO-заголовок на основе следующего текста:"
    meta_description_prompt = "Создай описание длиной до 160 символов на основе следующего текста:"
    
    meta_title = rewrite_text(title, meta_title_prompt)
    meta_description = rewrite_text(content, meta_description_prompt)

    return meta_title, meta_description

def upload_image_to_wordpress(image_url):
    """Загрузка изображения в WordPress"""
    if not image_url:
        print(f"[DEBUG] URL изображения отсутствует.")
        return None, None

    print(f"[DEBUG] Загрузка изображения с URL: {image_url}")
    response = requests.get(image_url)
    if response.status_code != 200:
        print(f"[ERROR] Ошибка загрузки изображения: {response.status_code}")
        return None, None

    image_data = {
        'name': image_url.split('/')[-1],
        'type': 'image/jpeg',
        'bits': response.content,
    }

    try:
        upload_response = wp_client.call(UploadFile(image_data))
        print(f"[DEBUG] Изображение загружено: ID={upload_response['id']}, URL={upload_response['url']}")
        return upload_response['id'], upload_response['url']
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки изображения в WordPress: {e}")
        return None, None

def publish_to_wordpress(title, content, meta_title, meta_description, image_url=None):
    """Публикация на WordPress"""
    post = WordPressPost()
    post.title = title
    post.content = content
    post.post_status = 'publish'  

    post.custom_fields = [
        {'key': '_yoast_wpseo_title', 'value': meta_title},
        {'key': '_yoast_wpseo_metadesc', 'value': meta_description},
    ]

    if image_url:
        image_id, _ = upload_image_to_wordpress(image_url)
        if image_id:
            post.thumbnail = image_id  

    try:
        wp_client.call(NewPost(post))
        print(f"Статья '{title}' успешно опубликована.")
    except Exception as e:
        print(f"[ERROR] Ошибка публикации статьи: {e}")

def process_rss():
    """Основной процесс обработки RSS"""
    articles = fetch_rss()
    print(f"Начинаем обработку статей, найдено: {len(articles)}")

    for article in articles:
        link = article['link']

        if is_article_processed(link):
            print(f"Статья уже обработана: {link}")
            continue

        parsed_data = parse_page(link)
        if not parsed_data:
            print(f"Ошибка парсинга страницы: {link}")
            continue

        title, raw_content, image_url = parsed_data
        print(f"Заголовок статьи: {title}")

        cleaned_content = clean_text(raw_content)

        title_prompt = "Создай уникальный заголовок на основе следующего текста статьи и исходного заголовка:"
        rewritten_title = rewrite_text(f"Заголовок: {title}\n\nТекст: {cleaned_content}", title_prompt)
        rewritten_title = clean_title(rewritten_title)  

        content_prompt = "Перепиши этот текст с уникальными формулировками, сохраняя смысл:"
        rewritten_content = rewrite_text(cleaned_content, content_prompt)

        meta_title, meta_description = generate_meta(rewritten_title, rewritten_content)

        publish_to_wordpress(rewritten_title, rewritten_content, meta_title, meta_description, image_url)

        mark_article_as_processed(link)

setup_database() 
schedule.every(1).minutes.do(process_rss)  

print("Запуск мониторинга RSS...")
while True:
    schedule.run_pending()
    time.sleep(1)
