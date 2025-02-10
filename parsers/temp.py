import requests
from bs4 import BeautifulSoup

def parse_page(url):
    """Парсинг страницы The Moscow Times"""
    response = requests.get(url)
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
        srcset = img.get("srcset")
        if srcset:
            image_url = srcset.split(",")[0].split(" ")[0].strip()
        else:
            image_url = img.get("src")
    else:
        image_url = None


    return title, content, image_url

if __name__ == "__main__":
    test_url = input("Введите ссылку на статью: ").strip()

    parsed_data = parse_page(test_url)
    if not parsed_data:
        print("[ERROR] Парсинг не удался. Проверьте ссылку или структуру страницы.")
    else:
        title, content, image_url = parsed_data
        print("\n=== Результаты парсинга ===")
        print(f"Заголовок: {title}")
        print("\nТекст статьи:")
        print(content)
        print("\nСсылка на изображение:")
        print(image_url)
