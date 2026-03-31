import argparse
import json
import logging
import types
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.traceback import Traceback

from .core import (
    CustomRichHandler,
    filter_traceback,
    get_formatted_traceback,
    get_traceback_renderable,
)


ExceptionInfo = tuple[type[BaseException], BaseException, types.TracebackType | None]
ExceptionBuilder = Callable[[], ExceptionInfo]
APP_PATHS = [str(Path(__file__).resolve().parent)]


def nested_failure() -> None:
    payload = {"items": [3, 2, 1], "label": "demo"}
    compute_ratio(payload)


def compute_ratio(payload: dict[str, object]) -> float:
    values = payload["items"]
    return divide_total(sum(values), len(values) - 3)


def divide_total(total: int, divisor: int) -> float:
    return total / divisor


def build_local_exception() -> ExceptionInfo:
    try:
        nested_failure()
    except Exception as exc:
        return type(exc), exc, exc.__traceback__
    raise RuntimeError("Expected demo exception was not raised")


def build_stdlib_exception() -> ExceptionInfo:
    try:
        json.loads("{")
    except Exception as exc:
        return type(exc), exc, exc.__traceback__
    raise RuntimeError("Expected stdlib exception was not raised")


def build_third_party_exception() -> ExceptionInfo:
    try:
        Console().print("x", style="not-a-style[")
    except Exception as exc:
        return type(exc), exc, exc.__traceback__
    raise RuntimeError("Expected third-party exception was not raised")


def build_chained_stdlib_exception() -> ExceptionInfo:
    try:
        json.loads("{")
    except Exception as exc:
        exc = exc.with_traceback(filter_traceback(exc.__traceback__, APP_PATHS))
        try:
            raise RuntimeError("Application wrapper failed after stdlib error") from exc
        except Exception as chained_exc:
            return type(chained_exc), chained_exc, chained_exc.__traceback__
    raise RuntimeError("Expected chained stdlib exception was not raised")


def build_chained_third_party_exception() -> ExceptionInfo:
    try:
        Console().print("x", style="not-a-style[")
    except Exception as exc:
        exc = exc.with_traceback(filter_traceback(exc.__traceback__, APP_PATHS))
        try:
            raise RuntimeError("Application wrapper failed after third-party error") from exc
        except Exception as chained_exc:
            return type(chained_exc), chained_exc, chained_exc.__traceback__
    raise RuntimeError("Expected chained third-party exception was not raised")


EXAMPLES: dict[str, tuple[str, ExceptionBuilder]] = {
    "local": ("Local", build_local_exception),
    "stdlib": ("Stdlib", build_stdlib_exception),
    "third-party": ("Third-Party", build_third_party_exception),
    "chained-stdlib": ("Chained Stdlib", build_chained_stdlib_exception),
    "chained-third-party": ("Chained Third-Party", build_chained_third_party_exception),
}


def show_default(
    console: Console,
    width: int,
    show_locals: bool,
    label: str,
    build_exception: ExceptionBuilder,
) -> None:
    exc_type, exc_value, exc_tb = build_exception()
    console.rule(f"[bold blue]Rich Default ({label})")
    console.print(
        Traceback.from_exception(
            exc_type,
            exc_value,
            exc_tb,
            width=width,
            show_locals=show_locals,
        )
    )


def show_custom(
    console: Console,
    width: int,
    show_locals: bool,
    label: str,
    build_exception: ExceptionBuilder,
) -> None:
    exc_type, exc_value, exc_tb = build_exception()
    console.rule(f"[bold green]Customized Renderable ({label})")
    console.print(
        get_traceback_renderable(
            exc_type,
            exc_value,
            exc_tb,
            width=width,
            show_locals=show_locals,
        )
    )


def show_formatted_string(
    console: Console,
    width: int,
    show_locals: bool,
    label: str,
    build_exception: ExceptionBuilder,
) -> None:
    exc_type, exc_value, exc_tb = build_exception()
    console.rule(f"[bold magenta]Customized ANSI String ({label})")
    print(
        get_formatted_traceback(
            exc_type,
            exc_value,
            exc_tb,
            width=width,
            show_locals=show_locals,
        ),
        end="",
    )


def show_logging_demo(
    width: int,
    show_locals: bool,
    label: str,
    build_exception: ExceptionBuilder,
) -> None:
    logger = logging.getLogger("rich-traceback-preview")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.ERROR)

    handler = CustomRichHandler(
        rich_tracebacks=True,
        tracebacks_width=width,
        tracebacks_show_locals=show_locals,
        show_level=False,
        show_time=False,
        show_path=False,
    )
    logger.addHandler(handler)
    logger.error(f"Custom handler output ({label})", exc_info=build_exception())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview Rich traceback customizations from this package."
    )
    parser.add_argument(
        "--mode",
        choices=("all", "default", "custom", "string", "logging"),
        default="all",
        help="Which traceback rendering mode to show.",
    )
    parser.add_argument(
        "--example",
        choices=tuple(EXAMPLES),
        default="local",
        help="Which kind of traceback to generate.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=120,
        help="Traceback render width.",
    )
    parser.add_argument(
        "--no-locals",
        action="store_true",
        help="Disable local variable display.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    show_locals = not args.no_locals
    console = Console()
    label, build_exception = EXAMPLES[args.example]

    if args.mode in {"all", "default"}:
        show_default(console, args.width, show_locals, label, build_exception)

    if args.mode in {"all", "custom"}:
        show_custom(console, args.width, show_locals, label, build_exception)

    if args.mode in {"all", "string"}:
        show_formatted_string(console, args.width, show_locals, label, build_exception)

    if args.mode in {"all", "logging"}:
        console.rule(f"[bold yellow]Custom Logging Handler ({label})")
        show_logging_demo(args.width, show_locals, label, build_exception)
