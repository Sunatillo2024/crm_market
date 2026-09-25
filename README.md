# ECO Mini CRM

MiniMarket/ECO uchun Django asosidagi CRM: marketlar, owner va kassir rollari, mahsulot katalogi, ombor harakatlari, POS savdo terminali, hisobotlar va audit jurnali.

## Texnik stek

- Python 3.11
- Django 5.2
- PostgreSQL 16
- Gunicorn va WhiteNoise
- Bootstrap 5, Bootstrap Icons
- `openpyxl` orqali Excel hisobot
- Docker Compose

## Asosiy imkoniyatlar

- `accounts`: login, owner/cassir rollari, kassirlarni boshqarish, parolni almashtirish va bloklash.
- `stores`: owner dashboard va market holati.
- `products`: marketga bog‘liq mahsulotlar, barkod, narx, qoldiq va arxivlash.
- `inventory`: kirim, chiqim, qoldiqni to‘g‘rilash va harakat tarixi.
- `sales`: POS savdo, naqd/karta to‘lov, chek, savdo ro‘yxati va bekor qilish.
- `reports`: davr bo‘yicha savdo/foyda hisoboti, CSV va Excel eksporti.
- `audit`: kassir o‘zgarishlari, savdo bekori va muhim harakatlar jurnali.

## Loyiha tuzilmasi

`config` — Django sozlamalari va umumiy URL’lar; `accounts` — foydalanuvchilar; `stores` — marketlar; `products` — katalog; `inventory` — qoldiq harakatlari; `sales` — savdo oqimi; `reports` — hisobotlar; `audit` — faoliyat jurnali. Shablonlar `templates/`, CSS/JS esa `static/` ichida.

Muhim URL’lar:

- `/login/`
- `/dashboard/`
- `/pos/`
- `/products/`, `/inventory/`, `/reports/`, `/activity/`
- `/employees/`

## Mahalliy ishga tushirish

1. Python 3.11 va PostgreSQL 16 o‘rnatilgan bo‘lishi kerak.
2. Loyiha ildizida virtual muhit yaratish:

```bash
cd /Users/macbook/Desktop/ECO_MINI_CRM/crm_market
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

3. `.env` ichidagi `DJANGO_SECRET_KEY` va DB qiymatlarini o‘zgartiring. Hech qachon `.env` faylini Git’ga qo‘shmang.
4. PostgreSQL’da `DB_NAME`, `DB_USER`, `DB_PASSWORD` mos database va foydalanuvchisini yarating.
5. Migration va static fayllarni tayyorlang:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Local server odatda `http://127.0.0.1:8000/` manzilida ochiladi.

## Docker bilan ishga tushirish

`.env.example` dan `.env` yarating va secretlarni to‘ldiring. Keyin:

```bash
cd /Users/macbook/Desktop/ECO_MINI_CRM/crm_market
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Web odatda `http://127.0.0.1:8001/`, PostgreSQL esa host porti `5434` orqali ochiladi. Entry point PostgreSQL’ni kutadi, migration’ni bajaradi, static fayllarni yig‘adi va superuser sozlamalari berilgan bo‘lsa idempotent superuser yaratadi.

Holat va loglarni tekshirish:

```bash
docker compose logs --tail=100 db web
curl -I http://127.0.0.1:8001/login/
```

Superuser yaratishni avtomatlashtirmasdan foydalanish ham mumkin:

```bash
docker compose exec web python manage.py createsuperuser
```

`docker compose down` database volume’larini saqlaydi. Ma’lumotlarni butunlay o‘chirish uchun `docker compose down -v` ishlatilmasligidan oldin tasdiqlang.

## Test va tekshiruv

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python -m compileall -q .
.venv/bin/python manage.py test --verbosity 1 --noinput
.venv/bin/pip check
```

Testlar PostgreSQL’da transactional xavfsizlik va `select_for_update` oqimlarini tekshiradi. Docker ichida ham testni shu shaklda ishga tushirish mumkin:

```bash
docker compose run --rm web python manage.py test --verbosity 1 --noinput
```

## Production bo‘yicha keyingi qadamlar

- `DJANGO_DEBUG=False`, aniq `DJANGO_ALLOWED_HOSTS`, HTTPS reverse proxy, secure session/CSRF cookie va HSTS sozlang.
- Default superuser yaratilmasin; `DJANGO_SUPERUSER_*` qiymatlarini faqat lokal `.env`da saqlang.
- PostgreSQL’ni muntazam backup va monitoring bilan boshqaring.
- Audit loglarni o‘chirilmaslik va ma’lumot retention siyosati bilan himoyalang.
- CI’da `check`, `makemigrations --check`, test va Docker build’ni majburiy qiling.
- Keyingi funksional yo‘nalishlar: doimiy backup/restore oqimi, kassir hisoblarini hisobotda kengaytirish, mahsulot import/export va operatsion monitoring.
