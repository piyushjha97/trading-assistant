import requests

from trading_assistant.market_context import SourceUnavailable


def fetch_object(
    url: str, params: dict[str, str], *, headers: dict[str, str] | None = None,
) -> dict:
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5, allow_redirects=False)
        if response.status_code != 200:
            raise SourceUnavailable("News feed request failed.")
        data = response.json()
    except (requests.RequestException, ValueError):
        # Some providers put credentials in the query string.
        raise SourceUnavailable("News feed request failed.") from None
    if not isinstance(data, dict):
        raise SourceUnavailable("News feed returned an invalid response.")
    return data
