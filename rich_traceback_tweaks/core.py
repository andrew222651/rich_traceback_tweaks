import io
import logging
import os
import site
import sysconfig
import types
from pathlib import Path
from typing import Optional

from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.traceback import Traceback

DEFAULT_WIDTH = 100


def get_suppress_paths() -> list[str]:
    """
    Build the list of standard library and third-party paths to suppress.
    """
    suppress_paths: list[str] = site.getsitepackages()
    stdlib_path: str | None = sysconfig.get_path("stdlib")

    if stdlib_path:
        suppress_paths.append(stdlib_path)

    return suppress_paths


SUPPRESS_PATHS: list[str] = get_suppress_paths()


def _is_suppressed_frame(frame_file: str, suppress_paths: list[str]) -> bool:
    """
    Check suppression using normalized path ancestry instead of string prefixes.
    """
    if frame_file.startswith("<") and frame_file.endswith(">"):
        return False

    frame_path = Path(frame_file).resolve()

    return any(frame_path.is_relative_to(Path(path).resolve()) for path in suppress_paths)


def filter_traceback(
    tb: types.TracebackType | None,
    suppress_paths: list[str],
) -> types.TracebackType | None:
    """
    Return a filtered traceback chain without mutating the original traceback.
    """
    current_old: types.TracebackType | None = tb
    kept_frames: list[types.TracebackType] = []
    suppressed_any = False

    while current_old is not None:
        frame_file: str = current_old.tb_frame.f_code.co_filename
        is_suppressed: bool = _is_suppressed_frame(frame_file, suppress_paths)

        if not is_suppressed:
            kept_frames.append(current_old)
        else:
            suppressed_any = True

        current_old = current_old.tb_next

    if not suppressed_any or not kept_frames:
        return tb

    filtered_tb: types.TracebackType | None = None

    for frame_tb in reversed(kept_frames):
        filtered_tb = types.TracebackType(
            filtered_tb,
            frame_tb.tb_frame,
            frame_tb.tb_lasti,
            frame_tb.tb_lineno,
        )

    return filtered_tb


def get_traceback_renderable(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: types.TracebackType | None,
    width: int = DEFAULT_WIDTH,
    show_locals: bool = True,
) -> Traceback:
    """
    Return a Rich traceback renderable with filtered frames and clickable URIs.
    """
    filtered_tb: types.TracebackType | None = filter_traceback(exc_tb, SUPPRESS_PATHS)
    trace = Traceback.extract(
        exc_type,
        exc_value,
        filtered_tb,
        show_locals=show_locals,
    )

    cwd: Path = Path.cwd()

    for stack in trace.stacks:
        for frame in stack.frames:
            abs_path = Path(frame.filename).resolve()
            frame.filename = os.path.relpath(abs_path, start=cwd)
            frame.name = f"{frame.name}  ({abs_path.as_uri()}:{frame.lineno})"

    return Traceback(trace=trace, width=width)


def get_formatted_traceback(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: types.TracebackType | None,
    width: int = DEFAULT_WIDTH,
    show_locals: bool = True,
) -> str:
    """
    Return the filtered Rich traceback as ANSI-formatted terminal text.
    """
    rich_tb = get_traceback_renderable(
        exc_type,
        exc_value,
        exc_tb,
        width=width,
        show_locals=show_locals,
    )

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=width)
    console.print(rich_tb)
    return buf.getvalue()


class CustomRichHandler(RichHandler):
    """
    Rich logging handler that swaps in the customized traceback renderer.
    """

    def render(
        self,
        *,
        record: logging.LogRecord,
        traceback: Optional[Traceback],
        message_renderable: ConsoleRenderable,
    ) -> ConsoleRenderable:
        if traceback is not None and record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            traceback = get_traceback_renderable(
                exc_type,
                exc_value,
                exc_tb,
                width=self.tracebacks_width or DEFAULT_WIDTH,
                show_locals=self.tracebacks_show_locals,
            )

        return super().render(
            record=record,
            traceback=traceback,
            message_renderable=message_renderable,
        )
