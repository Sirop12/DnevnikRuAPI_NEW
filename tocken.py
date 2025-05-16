import requests
from pydnevnikruapi.dnevnik.exceptions import DiaryError
from urllib.parse import urlparse, parse_qs

# Для получения токена нужно зайти на этот сайт https://login.dnevnik.ru/auth и скопировать оттуда данные куки и вставить сюда, тогда вы получите токен. Перед этим нужно зарегистрироваться на сайте dominika.ru
cookies = {
    'DnevnikAuth_a': "куки https://login.dnevnik.ru/auth",
    'DnevnikAuth_l': "куки https://login.dnevnik.ru/auth",
}

LOGIN_URL = "https://login.dnevnik.ru/login/"
RETURN_URL = (
    "https://login.dnevnik.ru/oauth2?response_type="
    "token&client_id=bb97b3e445a340b9b9cab4b9ea0dbd6f&scope=CommonInfo,ContactInfo,"
    "FriendsAndRelatives,EducationalInfo"
)


def get_token(cookies):
    token = requests.get(LOGIN_URL, params={
        "ReturnUrl": RETURN_URL}, allow_redirects=True, cookies=cookies)

    parsed_url = urlparse(token.url)
    query = parse_qs(parsed_url.query)
    result = query.get("result")

    if result is None or result[0] != "success":
        raise DiaryError("Что-то не так с авторизацией")

    if token.status_code != 200:
        raise DiaryError(
            "Сайт лежит или ведутся технические работы, использование api временно невозможно"
        )

    token = parsed_url.fragment[13:-7]
    return token


token = get_token(cookies)
# ВАШ ТОКЕН ! ! !
print(token)


# Можно раскомментировать чтоб протестить

"""from pydnevnikruapi.dnevnik import dnevnik
dn = dnevnik.DiaryAPI(token=token)
print(dn.get_school())"""