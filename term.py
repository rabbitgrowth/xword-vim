import sys
import termios

def enter_raw_mode() -> None:
    attributes = termios.tcgetattr(sys.stdin)
    attributes[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attributes)

def leave_raw_mode() -> None:
    attributes = termios.tcgetattr(sys.stdin)
    attributes[3] |= termios.ECHO | termios.ICANON
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attributes)

def enter_alternate_buffer() -> None:
    sys.stdout.write(f'\x1b[?1049h')

def leave_alternate_buffer() -> None:
    sys.stdout.write(f'\x1b[?1049l')

def clear_screen() -> None:
    sys.stdout.write(f'\x1b[2J')

def move_cursor(x: int, y: int) -> None:
    sys.stdout.write(f'\x1b[{y+1};{x+1}H')

def bold(text: str) -> str:
    return f'\x1b[1m{text}\x1b[0m'
