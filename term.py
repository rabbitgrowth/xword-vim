import fcntl
import struct
import sys
import termios

def get_window_size() -> tuple[int, int]:
    result = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))
    height, width, _, _ = struct.unpack('HHHH', result)
    return (width, height)

def enter_raw_mode() -> None:
    attributes = termios.tcgetattr(sys.stdout)
    attributes[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(sys.stdout, termios.TCSADRAIN, attributes)

def leave_raw_mode() -> None:
    attributes = termios.tcgetattr(sys.stdout)
    attributes[3] |= termios.ECHO | termios.ICANON
    termios.tcsetattr(sys.stdout, termios.TCSADRAIN, attributes)

def read_char() -> str:
    return sys.stdin.read(1)

def write(text: str) -> None:
    sys.stdout.write(text)

def flush() -> None:
    sys.stdout.flush()

def enter_alternate_buffer() -> None:
    write('\x1b[?1049h')

def leave_alternate_buffer() -> None:
    write('\x1b[?1049l')

def clear_screen() -> None:
    write('\x1b[2J')

def clear_rest_of_line() -> None:
    write(f'\x1b[K')

def move_cursor(x: int, y: int) -> None:
    write(f'\x1b[{y+1};{x+1}H')

def hide_cursor() -> None:
    write('\x1b[?25l')

def show_cursor() -> None:
    write('\x1b[?25h')

def save_cursor() -> None:
    write('\x1b7')

def restore_cursor() -> None:
    write('\x1b8')

def block_cursor() -> None:
    write('\x1b[0 q')

def underline_cursor() -> None:
    write('\x1b[3 q')

def ibeam_cursor() -> None:
    write('\x1b[5 q')

def bold(text: str) -> str:
    return f'\x1b[1m{text}\x1b[22m'

def dim(text: str) -> str:
    return f'\x1b[2m{text}\x1b[22m'

def red(text: str) -> str:
    return f'\x1b[31m{text}\x1b[39m'

def green(text: str) -> str:
    return f'\x1b[32m{text}\x1b[39m'
