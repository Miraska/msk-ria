import requests

def parse_page(url):
    """Парсинг страницы с использованием пользовательского агента"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[ERROR] Ошибка загрузки страницы: {url}. Код ошибки: {response.status_code}")
            return None

        return response.text  

    except requests.RequestException as e:
        print(f"[ERROR] Произошла ошибка при запросе: {e}")
        return None

if __name__ == "__main__":
    test_url = input("Введите ссылку на статью: ").strip()

    html_content = parse_page(test_url)
    if not html_content:
        print("[ERROR] Парсинг не удался. Проверьте ссылку или структуру страницы.")
    else:
        print("\n=== HTML содержимое страницы ===")
        print(html_content)
