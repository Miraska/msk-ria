FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Настройка переменной окружения для использования виртуального окружения
ENV PATH="/myenv/bin:$PATH"

# Проверка Python и pip
RUN python -c "import sys; print('Используемый Python:', sys.executable)" && \
    python -m pip list

# Копирование остальных файлов
COPY . .

# Логирование: завершение сборки
RUN echo "Сборка завершена."

# Запуск приложения
CMD ["python", "main.py"]
