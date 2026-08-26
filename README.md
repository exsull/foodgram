# Foodgram

Foodgram — веб-приложение для публикации и хранения рецептов.

Пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов.  
Зарегистрированным пользователям также будет доступен сервис «Список покупок».  
Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Возможности

- регистрация и авторизация пользователей;
- создание, редактирование и удаление рецептов;
- загрузка изображений рецептов в Base64;
- добавление рецептов в избранное;
- добавление рецептов в список покупок;
- скачивание списка покупок;
- подписка на авторов;
- поиск ингредиентов;
- фильтрация рецептов по тегам;
- короткие ссылки на рецепты;
- административная панель Django;
- импорт ингредиентов из CSV.

## Стек

- Python
- Django
- Django REST Framework
- Djoser
- PostgreSQL
- React
- Docker / Docker Compose
- Nginx

## Запуск

Клонировать репозиторий:

```bash
git clone git@github.com:exsull/foodgram.git
cd foodgram
```

Создать файл `.env`.  
Скопировать `.env.example` в `.env` и заполнить значения переменных окружения.

Запустить проект:

```bash
docker compose up -d
```

После запуска выполнить миграции:

```bash
docker compose exec backend python manage.py migrate
```
Собрать статику Django:
```bash
docker compose exec backend python manage.py collectstatic
```
Статика приложения в контейнере backend 
будет собрана в директорию /app/collected_static/.

Теперь из этой директории скопировать статику в /backend_static/static/;  
Эта статика попадёт на volume static в папку /static/:
```bash
docker compose exec backend cp -r /app/collected_static/. /backend_static/static/
```
Импортировать ингредиенты:

```bash
docker compose exec backend python manage.py import_csv
```

Создать администратора:

```bash
docker compose exec backend python manage.py createsuperuser
```

## API

Документация API доступна по адресу:

```text
/api/docs/redoc/
```

## Админ-панель

```text
/admin/
```

## Коллекция запросов для Postman
В директории `postman_collection` сохранена коллекция запросов для отладки и проверки работы текущей версии API для проекта Foodgram.  
Импортируйте коллекцию в Postman и выполняйте запросы.
Подробная инструкция по работе с коллекцией находится в файле
```bash
/postman_collection/README.md
```
## Автор
GitHub: [**exsull**](https://github.com/exsull)
