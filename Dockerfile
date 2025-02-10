FROM python:3.11.0-slim

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Копирование зависимостей
COPY requirements.txt .

# Активация виртуального окружения и установка зависимостей
RUN echo "Активация виртуального окружения..." && \
    . /myenv/bin/activate && \
    echo "Виртуальное окружение активировано." && \
    echo "Обновление pip..." && \
    pip install --upgrade pip && \
    echo "Установка зависимостей из requirements.txt..." && \
    pip install -r requirements.txt && \
    echo "Зависимости установлены."

# Копирование остальных файлов
COPY . .

# Установка переменной окружения
ENV PATH="/myenv/bin:$PATH"

# Логирование: завершение сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["python", "main.py"]
