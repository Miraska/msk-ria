FROM python:3.11.0-slim

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Установка переменной окружения для использования виртуального окружения
ENV PATH="/myenv/bin:$PATH"

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN echo "Обновление pip..." && \
    pip install --upgrade pip && \
    echo "Установка зависимостей из requirements.txt..." && \
    pip install -r requirements.txt && \
    echo "Зависимости установлены."

# Копирование остальных файлов
COPY . .

# Логирование: завершение сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["python", "main.py"]
