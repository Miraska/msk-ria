FROM python:3.11.0-slim

# Установка рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Активация виртуального окружения и установка зависимостей
RUN echo "Активация виртуального окружения..." && \
    . /opt/myenv/bin/activate && \
    echo "Виртуальное окружение активировано." && \
    echo "Обновление pip..." && \
    pip install --upgrade pip && \
    echo "Зависимости установлены."

# Копирование остальных файлов
COPY . .

# Установка переменной окружения
ENV PATH="/opt/myenv/bin:$PATH"

# Логирование: завершение сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["python", "main.py"]
