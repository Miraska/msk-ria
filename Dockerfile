FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Проверка содержимого виртуального окружения
RUN ls -l /myenv/bin/

# Установка переменной окружения для использования виртуального окружения
ENV PATH="/myenv/bin:$PATH"

# Проверка используемого Python и установленных пакетов
RUN which python && python --version && python -m pip list

# Копирование остальных файлов
COPY . .

# Логирование завершения сборки
RUN echo "Сборка завершена."

# Запуск приложения
CMD ["python", "main.py"]
