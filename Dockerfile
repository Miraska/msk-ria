FROM python:3.11.0-slim

# Установка рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Создание виртуального окружения и установка зависимостей
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Копирование остальных файлов
COPY . .

# Установка переменной окружения
ENV PATH="/opt/venv/bin:$PATH"

# Команда для запуска приложения
CMD ["python", "main.py"]
