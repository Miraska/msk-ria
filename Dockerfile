FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Подмена системного Python на Python из виртуального окружения
RUN ln -sf /myenv/bin/python /usr/local/bin/python

# Проверка используемого Python и установленных пакетов
RUN python -c "import sys; print('Используемый Python:', sys.executable)" && \
    python -m pip list

# Копирование остальных файлов
COPY . .

# Логирование завершения сборки
RUN echo "Сборка завершена."

# Запуск приложения
CMD ["python", "main.py"]
