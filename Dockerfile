FROM python:3.11.1

# Установка рабочей директории
WORKDIR /app

# Копирование виртуального окружения
COPY myenv /myenv

# Создаем директорию, если она не существует, и копируем исполнимый файл Python
RUN mkdir -p /myenv/bin && cp /usr/local/bin/python /myenv/bin/python

# Устанавливаем переменные окружения для использования виртуального окружения
ENV VIRTUAL_ENV="/myenv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

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
CMD ["/myenv/bin/python", "main.py"] 
