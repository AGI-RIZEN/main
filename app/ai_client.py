from flask import current_app
from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq, RateLimitError

from app.utils import AIUnavailable


def call_groq(prompt, response_schema):
    api_key = current_app.config.get("GROQ_API_KEY") or ""
    if not api_key:
        raise AIUnavailable("Configure GROQ_API_KEY on the server to use AI features.")
    if not isinstance(prompt, str) or len(prompt) > 20_000:
        raise AIUnavailable("The request was too large to send.")
    if not isinstance(response_schema, dict):
        raise AIUnavailable("The AI response format is not configured.")

    try:
        timeout = current_app.config["GROQ_TIMEOUT_SECONDS"]
        cached_client = current_app.extensions.get("groq_client")
        if cached_client is None or cached_client[:2] != (api_key, timeout):
            cached_client = (
                api_key,
                timeout,
                Groq(api_key=api_key, timeout=timeout, max_retries=0),
            )
            current_app.extensions["groq_client"] = cached_client
        client = cached_client[2]
        response = client.chat.completions.create(
            model=current_app.config["GROQ_MODEL"],
            messages=[
                {
                    "role": "system",
                    "content": "Return only content that conforms to the supplied JSON schema.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "portal_response",
                    "strict": True,
                    "schema": response_schema,
                },
            },
            max_completion_tokens=4096,
        )
    except RateLimitError as exc:
        current_app.logger.warning("Groq request rate-limited")
        raise AIUnavailable("Groq is rate-limiting requests. Wait briefly and try again.") from exc
    except APITimeoutError as exc:
        current_app.logger.warning("Groq request timed out")
        raise AIUnavailable("Groq did not respond in time. Nothing was saved.") from exc
    except (APIConnectionError, APIStatusError) as exc:
        current_app.logger.warning("Groq request failed: %s", type(exc).__name__)
        raise AIUnavailable("Groq is unavailable or rejected the request. Nothing was saved.") from exc

    choices = getattr(response, "choices", None) or []
    text = choices[0].message.content if choices else None
    if not isinstance(text, str) or not text.strip():
        raise AIUnavailable("Groq returned an empty response. Nothing was saved.")
    if len(text) > 100_000:
        raise AIUnavailable("The AI response was too large. Nothing was saved.")
    return text
