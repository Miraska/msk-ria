FROM python:3.11.1

WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Проверка, что виртуальное окружение действительно скопировалось
RUN ls -l /myenv || echo "Директория /myenv не найдена!"
RUN ls -l /myenv/Scripts || echo "Директория /myenv/Scripts не найдена!"

# Установка переменной окружения для Windows-окружения
ENV PATH="/myenv/Scripts:$PATH"

# Проверка используемого Python
RUN which python && python --version && python -m pip list

COPY . .

RUN echo "Сборка завершена."

CMD ["python", "main.py"]
