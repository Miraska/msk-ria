FROM python:3.11

WORKDIR /app

# Устанавливаем необходимые системные пакеты (пример)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    liblcms2-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libtiff-dev \
    libwebp-dev

# Создаем (или не создаем) виртуальное окружение — зависит от вашей конфигурации
# Если вы НЕ используете venv, можете пропустить эти строки
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install --upgrade pip

# Копируем ваши зависимости
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем ваш код
COPY . .

# Патчим нужный файл, меняя "from collections import" на "from collections.abc import"
# ПУТЬ зависит от того, где реально лежит пакет wordpress_xmlrpc в контейнере.
# Если вы точно знаете, что нужен именно "env/lib/wordpress_xmlrpc/base.py" — 
# используйте именно этот путь.
RUN find / -type f -name base.py | grep "wordpress_xmlrpc" \
    | xargs -I{} sed -i 's/from collections import /from collections.abc import /g' {}

# Запуск
CMD ["python", "main.py"]
