# Используем базовый образ Python
FROM python:3.11.1

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем виртуальное окружение
COPY myenv /myenv

# Устанавливаем переменные окружения для использования виртуального окружения
ENV VIRTUAL_ENV="/myenv"
ENV PATH="$VIRTUAL_ENV/Scripts:$PATH"

# Проверяем, что используется Python из виртуального окружения
RUN echo "Проверка используемого Python:" && \
    which python && python --version && \
    echo "Список установленных пакетов:" && \
    python -m pip list

# Копируем остальные файлы проекта
COPY . .

# Логирование завершения сборки
RUN echo "Сборка завершена."

# Команда для запуска приложения
CMD ["/myenv/Scripts/python", "main.py"]
