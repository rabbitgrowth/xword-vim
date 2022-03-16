import sys

def enter_alternate_buffer() -> None:
    sys.stdout.write(f'\033[?1049h')

def leave_alternate_buffer() -> None:
    sys.stdout.write(f'\033[?1049l')

def clear_screen() -> None:
    sys.stdout.write(f'\033[2J')

def move_cursor(x: int, y: int) -> None:
    sys.stdout.write(f'\033[{y+1};{x+1}H')

def bold(text: str) -> str:
    return f'\033[1m{text}\033[0m'
