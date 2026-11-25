import time
from dataclasses import dataclass
from typing import Any

import litellm
from litellm import Cache

from .config import settings


# Enable LiteLLM's built-in in-memory cache.
litellm.cache = Cache(type="local")


# Provider errors that should trigger automatic key fallback.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


@dataclass
class LLMResult:
    reply: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int
    resolution_source: str


def parse_failure_header(
    header_value: str | None,
) -> dict[str, int]:
    """
    Parse the X-Simulate-Failure header.

    Examples:
        key_1=429
        key_1=429,key_2=500
        *=429
    """
    failures: dict[str, int] = {}

    if not header_value:
        return failures

    for item in header_value.split(","):
        item = item.strip()

        if not item or "=" not in item:
            continue

        key_id, status_text = item.split("=", 1)

        key_id = key_id.strip()
        status_text = status_text.strip()

        try:
            status = int(status_text)
        except ValueError:
            continue

        if status not in RETRYABLE_STATUS_CODES:
            continue

        if key_id:
            failures[key_id] = status

    return failures


def should_simulate_failure(
    key_id: str,
    simulated_failures: dict[str, int],
) -> int | None:
    """
    Return the simulated HTTP failure status for a key
    when failure simulation is enabled.
    """
    if not settings.enable_failure_simulation:
        return None

    if "*" in simulated_failures:
        return simulated_failures["*"]

    return simulated_failures.get(key_id)


def get_status_code(
    exception: Exception,
) -> int | None:
    """
    Extract an HTTP status code from a LiteLLM/provider
    exception when available.
    """
    status_code = getattr(
        exception,
        "status_code",
        None,
    )

    if isinstance(status_code, int):
        return status_code

    response = getattr(
        exception,
        "response",
        None,
    )

    if response is not None:
        response_status = getattr(
            response,
            "status_code",
            None,
        )

        if isinstance(response_status, int):
            return response_status

    return None


def is_retryable_exception(
    exception: Exception,
) -> bool:
    """
    Determine whether a provider failure should cause
    fallback to the next API key.
    """
    status_code = get_status_code(exception)

    if status_code in RETRYABLE_STATUS_CODES:
        return True

    exception_name = (
        exception.__class__.__name__.lower()
    )

    message = str(exception).lower()

    retryable_terms = (
        "ratelimit",
        "rate limit",
        "quota",
        "resource exhausted",
        "429",
        "500",
        "502",
        "503",
        "service unavailable",
        "internal server error",
    )

    return any(
        term in exception_name
        or term in message
        for term in retryable_terms
    )


def extract_usage(
    response: Any,
) -> tuple[int, int]:
    """
    Extract input and output token usage from the
    LiteLLM response.
    """
    usage = getattr(
        response,
        "usage",
        None,
    )

    if usage is None:
        return 0, 0

    if isinstance(usage, dict):
        input_tokens = usage.get(
            "prompt_tokens",
            usage.get(
                "input_tokens",
                0,
            ),
        )

        output_tokens = usage.get(
            "completion_tokens",
            usage.get(
                "output_tokens",
                0,
            ),
        )

        return (
            int(input_tokens or 0),
            int(output_tokens or 0),
        )

    input_tokens = getattr(
        usage,
        "prompt_tokens",
        getattr(
            usage,
            "input_tokens",
            0,
        ),
    )

    output_tokens = getattr(
        usage,
        "completion_tokens",
        getattr(
            usage,
            "output_tokens",
            0,
        ),
    )

    return (
        int(input_tokens or 0),
        int(output_tokens or 0),
    )


def was_cache_hit(
    response: Any,
) -> bool:
    """
    Check LiteLLM response metadata to determine
    whether the response came from cache.
    """
    hidden_params = getattr(
        response,
        "_hidden_params",
        {},
    ) or {}

    if not isinstance(
        hidden_params,
        dict,
    ):
        return False

    if hidden_params.get("cache_hit") is True:
        return True

    if (
        hidden_params.get(
            "cached_response"
        )
        is True
    ):
        return True

    return False


async def generate_response(
    messages: list[dict[str, str]],
    simulate_failure_header: str | None = None,
) -> LLMResult:
    """
    Generate an LLM response using the configured
    API-key pool.

    Retryable failures automatically move to the next
    API key.

    LiteLLM caching is enabled for identical model
    and message-list requests.
    """
    api_keys = settings.api_keys

    if len(api_keys) < 2:
        raise RuntimeError(
            "At least two API keys must be "
            "configured in LLM_API_KEYS."
        )

    simulated_failures = parse_failure_header(
        simulate_failure_header
    )

    fallback_attempts = 0
    last_exception: Exception | None = None

    for index, api_key in enumerate(api_keys):
        key_id = f"key_{index + 1}"

        simulated_status = (
            should_simulate_failure(
                key_id,
                simulated_failures,
            )
        )

        # Simulate provider failure for assignment testing.
        if simulated_status is not None:
            fallback_attempts += 1

            last_exception = RuntimeError(
                "Simulated provider failure: "
                f"{key_id} returned "
                f"{simulated_status}"
            )

            continue

        started_at = time.perf_counter()

        try:
            response = await litellm.acompletion(
                model=settings.llm_model,
                messages=messages,
                api_key=api_key,
                caching=True,
            )

            latency_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            reply = (
                response
                .choices[0]
                .message
                .content
            )

            if not reply:
                raise RuntimeError(
                    "LLM returned an empty response."
                )

            (
                input_tokens,
                output_tokens,
            ) = extract_usage(response)

            cache_hit = was_cache_hit(response)

            # Cached responses must not expose a key ID.
            if cache_hit:
                return LLMResult(
                    reply=reply,
                    model=settings.llm_model,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    key_id=None,
                    fallback_attempts=0,
                    resolution_source="LLM_CACHE",
                )

            return LLMResult(
                reply=reply,
                model=settings.llm_model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                key_id=key_id,
                fallback_attempts=fallback_attempts,
                resolution_source="LIVE_INFERENCE",
            )

        except Exception as exc:
            last_exception = exc

            if is_retryable_exception(exc):
                fallback_attempts += 1
                continue

            raise

    raise RuntimeError(
        "all providers unavailable"
    ) from last_exception