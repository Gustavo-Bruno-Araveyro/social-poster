# 🔐 НАСТРОЙКА GOOGLE OAUTH ДЛЯ АВТОРИЗАЦИИ ПОЛЬЗОВАТЕЛЕЙ

## ⚡ БЫСТРЫЙ СПОСОБ (используем тот же OAuth Client, что для YouTube)

Если у тебя уже есть `YOUTUBE_CLIENT_ID` и `YOUTUBE_CLIENT_SECRET` в Railway, просто добавь redirect URI в Google Cloud Console.

---

## 📋 ШАГ 1: Открыть Google Cloud Console

**Ссылка:** https://console.cloud.google.com/apis/credentials

1. Войди в свой Google аккаунт
2. Выбери проект (или создай новый)

---

## 📋 ШАГ 2: Найти существующий OAuth Client

1. На странице **Credentials** найди свой OAuth Client ID (который используешь для YouTube)
2. **Нажми на название** этого OAuth Client (или на иконку карандаша ✏️ для редактирования)

---

## 📋 ШАГ 3: Добавить Redirect URI для авторизации пользователей

В разделе **"Authorized redirect URIs"** добавь:

```
https://web-production-e92c4.up.railway.app/authorize/google
```

**Как добавить:**
1. Нажми **"+ ADD URI"**
2. Вставь: `https://web-production-e92c4.up.railway.app/authorize/google`
3. Нажми **"SAVE"** внизу страницы

---

## 📋 ШАГ 4: Проверить Railway Variables

**Ссылка:** https://railway.app → твой проект → сервис `web` → вкладка **"Variables"**

Убедись, что есть:
- `YOUTUBE_CLIENT_ID` 
- `YOUTUBE_CLIENT_SECRET`

**Если их нет** - добавь:
1. Нажми **"+ New Variable"**
2. Name: `YOUTUBE_CLIENT_ID`
3. Value: вставь Client ID из Google Cloud Console
4. Нажми **"Add"**
5. Повтори для `YOUTUBE_CLIENT_SECRET`

---

## ✅ ГОТОВО!

После этого:
- Подожди 1-2 минуты (Railway перезапустится)
- Открой сайт: https://web-production-e92c4.up.railway.app
- Нажми "Войти через Google"
- Авторизуйся
- Система запомнит тебя!

---

## 🔄 ЕСЛИ ХОЧЕШЬ ОТДЕЛЬНЫЙ OAuth Client (не обязательно)

Если хочешь отдельный OAuth Client для авторизации пользователей:

### ШАГ 1: Создать новый OAuth Client

**Ссылка:** https://console.cloud.google.com/apis/credentials

1. Нажми **"+ CREATE CREDENTIALS"**
2. Выбери **"OAuth client ID"**
3. Application type: **"Web application"**
4. Name: `User Authentication`
5. **Authorized JavaScript origins:**
   ```
   https://web-production-e92c4.up.railway.app
   ```
6. **Authorized redirect URIs:**
   ```
   https://web-production-e92c4.up.railway.app/authorize/google
   ```
7. Нажми **"CREATE"**
8. Скопируй **Client ID** и **Client Secret**

### ШАГ 2: Добавить в Railway

**Ссылка:** https://railway.app → проект → сервис `web` → **"Variables"**

Добавь:
- `GOOGLE_CLIENT_ID` = твой новый Client ID
- `GOOGLE_CLIENT_SECRET` = твой новый Client Secret

---

## ❓ ЕСЛИ НЕ РАБОТАЕТ

**Ошибка "redirect_uri_mismatch":**
- Проверь, что в Google Cloud Console добавлен ТОЧНЫЙ URI:
  ```
  https://web-production-e92c4.up.railway.app/authorize/google
  ```
- Без слеша в конце!
- Без пробелов!

**Ошибка "invalid_client":**
- Проверь, что переменные добавлены в Railway правильно
- Проверь, что нет лишних пробелов в значениях

