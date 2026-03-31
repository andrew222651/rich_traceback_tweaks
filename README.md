# rich_traceback_tweaks

`rich_traceback_tweaks` is a small package that customizes Rich tracebacks for local application code:

- strips frames from the standard library and installed site-packages
- adds clickable absolute `file://` URIs beside each frame


## Usage

```python
import sys

from rich.console import Console
from rich_traceback_tweaks import CustomRichHandler, get_formatted_traceback, get_traceback_renderable


try:
    raise RuntimeError("boom")
except Exception:
    exc_type, exc_value, exc_tb = sys.exc_info()

    console = Console()
    console.print(get_traceback_renderable(exc_type, exc_value, exc_tb))

    ansi_text = get_formatted_traceback(exc_type, exc_value, exc_tb)
    print(ansi_text, end="")
```

## Preview CLI

Install the package and run:
```bash
python -m rich_traceback_tweaks
```

Options:

- `--example {local,stdlib,third-party,chained-stdlib,chained-third-party}`
- `--mode {all,default,custom,string,logging}`
- `--width 120`
- `--no-locals`
