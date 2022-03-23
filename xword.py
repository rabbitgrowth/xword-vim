from __future__ import annotations
from collections.abc import Callable, Iterator
import collections
import copy
import enum
import readline
import string
import struct
import sys
import termios
import textwrap
import typing

import puz

import term

def sign(n: int) -> int:
    return (n > 0) - (n < 0)

class Direction(enum.Enum):
    ACROSS = enum.auto()
    DOWN   = enum.auto()

class Mode(enum.Enum):
    NORMAL = enum.auto()
    INSERT = enum.auto()

class Status(enum.Enum):
    NORMAL       = enum.auto()
    PENCILLED_IN = enum.auto()
    MARKED_WRONG = enum.auto()
    MARKED_RIGHT = enum.auto()
    REVEALED     = enum.auto()

class Shape(enum.Enum):
    DOWN_AND_RIGHT          = enum.auto()
    DOWN_AND_HORIZONTAL     = enum.auto()
    DOWN_AND_LEFT           = enum.auto()
    VERTICAL_AND_RIGHT      = enum.auto()
    VERTICAL_AND_HORIZONTAL = enum.auto()
    VERTICAL_AND_LEFT       = enum.auto()
    UP_AND_RIGHT            = enum.auto()
    UP_AND_HORIZONTAL       = enum.auto()
    UP_AND_LEFT             = enum.auto()
    HORIZONTAL              = enum.auto()
    VERTICAL                = enum.auto()
    NONE                    = enum.auto()

BOX_DRAWING_CHARS = {Shape.DOWN_AND_RIGHT:          {Shape.NONE:           '┌',
                                                     Shape.DOWN_AND_RIGHT: '┏'},
                     Shape.DOWN_AND_HORIZONTAL:     {Shape.NONE:           '┬',
                                                     Shape.DOWN_AND_RIGHT: '┲',
                                                     Shape.DOWN_AND_LEFT:  '┱',
                                                     Shape.HORIZONTAL:     '┯'},
                     Shape.DOWN_AND_LEFT:           {Shape.NONE:           '┐',
                                                     Shape.DOWN_AND_LEFT:  '┓'},
                     Shape.VERTICAL_AND_RIGHT:      {Shape.NONE:           '├',
                                                     Shape.DOWN_AND_RIGHT: '┢',
                                                     Shape.UP_AND_RIGHT:   '┡',
                                                     Shape.VERTICAL:       '┠'},
                     Shape.VERTICAL_AND_HORIZONTAL: {Shape.NONE:           '┼',
                                                     Shape.DOWN_AND_RIGHT: '╆',
                                                     Shape.DOWN_AND_LEFT:  '╅',
                                                     Shape.UP_AND_RIGHT:   '╄',
                                                     Shape.UP_AND_LEFT:    '╃',
                                                     Shape.HORIZONTAL:     '┿',
                                                     Shape.VERTICAL:       '╂'},
                     Shape.VERTICAL_AND_LEFT:       {Shape.NONE:           '┤',
                                                     Shape.DOWN_AND_LEFT:  '┪',
                                                     Shape.UP_AND_LEFT:    '┩',
                                                     Shape.VERTICAL:       '┨'},
                     Shape.UP_AND_RIGHT:            {Shape.NONE:           '└',
                                                     Shape.UP_AND_RIGHT:   '┗'},
                     Shape.UP_AND_HORIZONTAL:       {Shape.NONE:           '┴',
                                                     Shape.UP_AND_RIGHT:   '┺',
                                                     Shape.UP_AND_LEFT:    '┹',
                                                     Shape.HORIZONTAL:     '┷'},
                     Shape.UP_AND_LEFT:             {Shape.NONE:           '┘',
                                                     Shape.UP_AND_LEFT:    '┛'},
                     Shape.HORIZONTAL:              {Shape.NONE:           '─',
                                                     Shape.HORIZONTAL:     '━'},
                     Shape.VERTICAL:                {Shape.NONE:           '│',
                                                     Shape.VERTICAL:       '┃'}}

class Game:
    def __init__(self, data: puz.Puzzle) -> None:
        self.puzzle = Puzzle(data)
        self.cursor = Cursor(self.puzzle.first_square(Direction.ACROSS), Direction.ACROSS, self.puzzle)
        self.mode   = Mode.NORMAL
        self.message: str | None = None

    def run(self) -> None:
        width, height = term.get_window_size()
        min_width  = self.puzzle.displayed_width + 68
        min_height = self.puzzle.displayed_height + 2
        if width < min_width or height < min_height:
            sys.exit(f'Your window needs to be at least {min_width}x{min_height}.')
        old_attributes = termios.tcgetattr(sys.stdin)
        term.enter_raw_mode()
        term.enter_alternate_buffer()
        try:
            while True:
                self.render()
                self.handle_input()
                self.congratulate()
        except KeyboardInterrupt:
            pass
        finally:
            term.leave_alternate_buffer()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attributes)

    def render(self) -> None:
        term.clear_screen()
        term.move_cursor(0, 0)
        for y, line in enumerate(self.puzzle.render_grid(self.cursor)):
            term.move_cursor(0, y)
            term.write(line)
        for direction, x_offset, title in zip(Direction, (2, 36), ('Across', 'Down')):
            for y, line in enumerate([term.bold(title), *self.puzzle.render_clues(self.cursor, direction)]):
                term.move_cursor(self.puzzle.displayed_width + x_offset, y)
                term.write(line)
        if self.message is not None:
            term.move_cursor(0, self.puzzle.displayed_height + 1)
            term.write(self.message)
        term.move_cursor(*self.cursor.displayed_coords())
        term.flush()

    def handle_input(self) -> None:
        chars = []
        def append(char):
            chars.append(char)
            term.save_cursor()
            term.move_cursor(self.puzzle.displayed_width + 60, self.puzzle.displayed_height + 1)
            term.write(''.join(chars[-8:]))
            term.restore_cursor()
            term.flush()
        char = term.read_char()
        if self.mode is Mode.NORMAL:
            while char.isdigit() and not (char == '0' and not chars):
                append(char)
                char = term.read_char()
            count = int(''.join(chars)) if chars else None # distinguish between G and 1G
            if char == 'h':
                self.cursor = self.cursor.h()
            elif char == 'j':
                self.cursor = self.cursor.j()
            elif char == 'k':
                self.cursor = self.cursor.k()
            elif char == 'l':
                self.cursor = self.cursor.l()
            elif char == 'g':
                append(char)
                next_char = term.read_char()
                if next_char == 'e':
                    self.cursor = self.cursor.ge()
                elif next_char == 'g':
                    self.cursor = self.cursor.gg()
            elif char == 'G':
                self.cursor = self.cursor.G(count)
            elif char == '0':
                self.cursor = self.cursor.zero()
            elif char == '$':
                self.cursor = self.cursor.dollar()
            elif char == 'w':
                self.cursor = self.cursor.w()
            elif char == 'b':
                self.cursor = self.cursor.b()
            elif char == 'e':
                self.cursor = self.cursor.e()
            elif char == ']':
                append(char)
                next_char = term.read_char()
                if next_char == ']':
                    self.cursor = self.cursor.double_right_square_bracket()
            elif char == '[':
                append(char)
                next_char = term.read_char()
                if next_char == '[':
                    self.cursor = self.cursor.double_left_square_bracket()
            elif char == '}':
                self.cursor = self.cursor.right_curly_bracket()
            elif char == '{':
                self.cursor = self.cursor.left_curly_bracket()
            elif char == 'r':
                term.underline_cursor()
                term.flush()
                next_char = term.read_char()
                self.cursor = self.cursor.r(next_char)
                term.block_cursor()
            elif char == 'x':
                self.cursor = self.cursor.x()
            elif char == 'c':
                append(char)
                next_char = term.read_char()
                if next_char == 'w':
                    self.cursor = self.cursor.cw()
                self.i()
            elif char == 'd':
                append(char)
                next_char = term.read_char()
                if next_char == 'w':
                    self.cursor = self.cursor.dw()
            elif char == ' ':
                self.cursor = self.cursor.space()
            elif char == '~':
                self.cursor = self.cursor.tilde()
            elif char == ':':
                self.handle_command(self.read_command())
            elif char == 'i':
                self.i()
            elif char == 'a':
                self.a()
            elif char == 's':
                self.s()
        elif self.mode is Mode.INSERT:
            if char == '\x1b':
                self.escape()
            elif char == '\x7f':
                self.cursor = self.cursor.backspace()
            elif char == 'j':
                append(char)
                next_char = term.read_char()
                if next_char == 'k':
                    self.escape()
                else:
                    self.cursor = self.cursor.type(char)
                    self.cursor = self.cursor.type(next_char)
            else:
                self.cursor = self.cursor.type(char)

    def congratulate(self) -> None:
        if self.mode is Mode.NORMAL and all(square.is_filled() for square in self.puzzle.itersquares()):
            if all(square.is_right() for square in self.puzzle.itersquares()):
                self.show_message("Congrats! You've finished the puzzle.")
            else:
                self.show_message("At least one square's amiss.")

    def read_command(self) -> str:
        self.message = None
        term.move_cursor(0, self.puzzle.displayed_height + 1)
        term.clear_rest_of_line()
        term.leave_raw_mode()
        command = input(':')
        term.enter_raw_mode()
        term.hide_cursor() # prevent cursor from briefly appearing under the colon
        term.flush()
        term.show_cursor()
        return command

    def handle_command(self, command: str) -> None:
        if command.isdigit():
            self.cursor = self.cursor.G(int(command))
        elif command in ('cs', 'check square'):
            self.cursor.square.check()
        elif command in ('c', 'cw', 'check', 'check word'):
            word = self.cursor.square.word[self.cursor.direction]
            for square in word:
                square.check()
        elif command in ('cp', 'check puzzle'):
            for square in self.puzzle.itersquares():
                square.check()
        elif command in ('rs', 'reveal square'):
            self.cursor.square.reveal()
        elif command in ('r', 'rw', 'reveal', 'reveal word'):
            word = self.cursor.square.word[self.cursor.direction]
            for square in word:
                square.reveal()
        elif command in ('rp', 'reveal puzzle'):
            for square in self.puzzle.itersquares():
                square.reveal()
        elif command in ('q', 'quit'):
            sys.exit()
        elif command == 'smile':
            self.show_message(':-)')

    def i(self) -> None:
        self.mode = Mode.INSERT
        self.show_message('-- INSERT --')
        term.ibeam_cursor()

    def a(self) -> None:
        self.cursor = self.cursor.go_to_next_square()
        self.i()

    def s(self) -> None:
        # Only visually different from i unlike in Vim
        self.cursor = self.cursor.x()
        self.i()

    def escape(self) -> None:
        self.mode = Mode.NORMAL
        self.hide_message()
        term.block_cursor()

    def show_message(self, message: str) -> None:
        self.message = message

    def hide_message(self) -> None:
        self.message = None

class Puzzle:
    def __init__(self, data: puz.Puzzle) -> None:
        self.grid = [[Square(x, y, solution, None) if solution != '.' else None
                      for x, solution in enumerate(row)]
                     for y, row in enumerate(zip(*[iter(data.solution)]*data.width))]

        self.width            = len(self.grid[0])
        self.height           = len(self.grid)
        self.displayed_width  = self.width  * 4 + 1
        self.displayed_height = self.height * 2 + 1

        numbering = data.clue_numbering()
        self.words: dict[Direction, list[Word]] = collections.defaultdict(list)
        for direction, entries in zip(Direction, (numbering.across, numbering.down)):
            for entry in entries:
                squares = []
                for offset in range(entry['len']):
                    if direction is Direction.DOWN:
                        offset *= self.width
                    y, x = divmod(entry['cell'] + offset, self.width)
                    square = self.get_square(x, y)
                    squares.append(square)
                clue = Clue(entry['num'], entry['clue'])
                word = Word(squares, clue)
                self.words[direction].append(word)

        # Doubly-link words and squares and link squares to words
        for direction, words in self.words.items():
            prev_word   = None
            prev_square = None
            for word in words:
                if prev_word is not None:
                    word.prev = prev_word
                    prev_word.next = word
                for square in word:
                    square.word[direction] = word
                    if prev_square is not None:
                        square.prev[direction] = prev_square
                        prev_square.next[direction] = square
                    prev_square = square
                prev_word = word

    def transpose(self) -> list[list[Square | None]]:
        return list(map(list, zip(*self.grid)))

    def get_row(self, y: int) -> list[Square | None]:
        if not 0 <= y < self.height:
            raise IndexError
        return self.grid[y]

    def get_column(self, x: int) -> list[Square | None]:
        if not 0 <= x < self.width:
            raise IndexError
        return self.transpose()[x]

    def get_square(self, x: int, y: int) -> Square | None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError
        return self.grid[y][x]

    def itersquares(self) -> Iterator[Square]:
        for row in self.grid:
            for square in row:
                if square is not None:
                    yield square

    def iterwords(self, direction: Direction) -> Iterator[Word]:
        for word in self.words[direction]:
            yield word

    def iterclues(self, direction: Direction) -> Iterator[Clue]:
        for word in self.iterwords(direction):
            yield word.clue

    def first_square(self, direction: Direction) -> Square:
        return self.words[direction][0][0]

    def last_square(self, direction: Direction) -> Square:
        return self.words[direction][-1][-1]

    def render_grid(self, cursor: Cursor) -> Iterator[str]:
        boldness = {}
        word = cursor.square.word[cursor.direction]
        x, y = word[0]
        if cursor.direction == Direction.ACROSS:
            boldness[(x, y    )] = Shape.DOWN_AND_RIGHT
            boldness[(x, y + 1)] = Shape.UP_AND_RIGHT
            for x, y in word[1:]:
                boldness[(x, y    )] = Shape.HORIZONTAL
                boldness[(x, y + 1)] = Shape.HORIZONTAL
            boldness[(x + 1, y    )] = Shape.DOWN_AND_LEFT
            boldness[(x + 1, y + 1)] = Shape.UP_AND_LEFT
        else:
            boldness[(x,     y)] = Shape.DOWN_AND_RIGHT
            boldness[(x + 1, y)] = Shape.DOWN_AND_LEFT
            for x, y in word[1:]:
                boldness[(x,     y)] = Shape.VERTICAL
                boldness[(x + 1, y)] = Shape.VERTICAL
            boldness[(x,     y + 1)] = Shape.UP_AND_RIGHT
            boldness[(x + 1, y + 1)] = Shape.UP_AND_LEFT
        for y in range(self.height + 1):
            line = ''
            for x in range(self.width + 1):
                if x == 0:
                    if y == 0:
                        vertex_shape = Shape.DOWN_AND_RIGHT
                    elif y < self.height:
                        vertex_shape = Shape.VERTICAL_AND_RIGHT
                    else:
                        vertex_shape = Shape.UP_AND_RIGHT
                elif x < self.width:
                    if y == 0:
                        vertex_shape = Shape.DOWN_AND_HORIZONTAL
                    elif y < self.height:
                        vertex_shape = Shape.VERTICAL_AND_HORIZONTAL
                    else:
                        vertex_shape = Shape.UP_AND_HORIZONTAL
                else:
                    if y == 0:
                        vertex_shape = Shape.DOWN_AND_LEFT
                    elif y < self.height:
                        vertex_shape = Shape.VERTICAL_AND_LEFT
                    else:
                        vertex_shape = Shape.UP_AND_LEFT
                vertex_boldness = boldness.get((x, y), Shape.NONE)
                vertex = BOX_DRAWING_CHARS[vertex_shape][vertex_boldness]
                line += vertex
                if x < self.width:
                    if vertex_boldness in (Shape.DOWN_AND_RIGHT, Shape.UP_AND_RIGHT, Shape.HORIZONTAL):
                        horizontal_edge_boldness = Shape.HORIZONTAL
                    else:
                        horizontal_edge_boldness = Shape.NONE
                    horizontal_edge_char = BOX_DRAWING_CHARS[Shape.HORIZONTAL][horizontal_edge_boldness]
                    if y < self.height:
                        square = self.get_square(x, y)
                        if square is not None:
                            clue_number = square.clue_number()
                            clue_number_string = str(clue_number) if clue_number is not None else ''
                        else:
                            clue_number_string = ''
                    else:
                        clue_number_string = ''
                    # Can't just use str.ljust because we might add term escape sequence for bold text
                    horizontal_edge = horizontal_edge_char * (3 - len(clue_number_string))
                    if square is word[0]:
                        clue_number_string = term.bold(clue_number_string)
                    line += clue_number_string
                    line += horizontal_edge
            yield line
            if y < self.height:
                line = ''
                for x in range(self.width + 1):
                    vertex_boldness = boldness.get((x, y), Shape.NONE)
                    if vertex_boldness in (Shape.DOWN_AND_RIGHT, Shape.DOWN_AND_LEFT, Shape.VERTICAL):
                        vertical_edge_boldness = Shape.VERTICAL
                    else:
                        vertical_edge_boldness = Shape.NONE
                    vertical_edge = BOX_DRAWING_CHARS[Shape.VERTICAL][vertical_edge_boldness]
                    line += vertical_edge
                    if x < self.width:
                        square = self.get_square(x, y)
                        line += '░░░' if square is None else square.render()
                yield line

    def render_clues(self, cursor: Cursor, direction: Direction) -> list[str]:
        lines = []
        start = 0 # start index, i.e., number of lines to skip
        found = False
        for clue in self.iterclues(direction):
            is_current = clue.number == cursor.square.word[direction].clue.number
            if not (is_current or found):
                start += len(clue.lines)
            else:
                found = True
            for i, line in enumerate(clue.lines):
                if i == 0:
                    arrow = '>' if is_current else ' '
                    line = f'{arrow}{clue.number:>2} {line}'
                else:
                    line = f'    {line}'
                if is_current and direction is cursor.direction:
                    line = term.bold(line)
                lines.append(line)
        height = self.displayed_height - 1
        start = min(start, max(len(lines) - height, 0))
        return lines[start:start+height]

class Square:
    def __init__(self, x: int, y: int, solution: str, guess: str | None) -> None:
        self.x        = x
        self.y        = y
        self.solution = solution
        self.guess    = guess
        self.status   = Status.NORMAL
        self.prev: dict[Direction, Square | None] = dict.fromkeys(Direction)
        self.next: dict[Direction, Square | None] = dict.fromkeys(Direction)
        self.word: dict[Direction, Word] = {}

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y

    def is_start(self, direction: Direction) -> bool:
        return self is self.word[direction][0]

    def is_end(self, direction: Direction) -> bool:
        return self is self.word[direction][-1]

    def is_filled(self) -> bool:
        return self.guess is not None

    def is_right(self) -> bool:
        return self.is_filled() and self.guess == self.solution

    def clue_number(self) -> int | None:
        for direction in Direction:
            if self.is_start(direction):
                return self.word[direction].clue.number
        return None

    def set(self, char: str) -> None:
        # TODO: type !@#$%^&*() to pencil in numbers?
        if not char.isalnum():
            raise ValueError
        self.guess  = char.upper()
        self.status = Status.PENCILLED_IN if char.isupper() else Status.NORMAL

    def unset(self) -> None:
        self.guess  = None
        self.status = Status.NORMAL

    def toggle_pencil(self) -> None:
        if self.is_filled():
            self.status = Status.NORMAL if self.status is Status.PENCILLED_IN else Status.PENCILLED_IN

    def check(self) -> None:
        if self.is_filled():
            self.status = Status.MARKED_RIGHT if self.is_right() else Status.MARKED_WRONG

    def reveal(self) -> None:
        self.guess  = self.solution
        self.status = Status.REVEALED

    def render(self) -> str:
        guess = self.guess if self.is_filled() else ' '
        assert guess is not None
        if self.status is Status.PENCILLED_IN:
            guess = term.dim(guess)
        elif self.status is Status.MARKED_WRONG:
            guess = term.red(guess)
        elif self.status is Status.MARKED_RIGHT:
            guess = term.green(guess)
        elif self.status is Status.REVEALED:
            guess = term.blue(guess)
        return f' {guess} '

class Word:
    def __init__(self, squares: list[Square], clue: Clue) -> None:
        self.squares = squares
        self.clue    = clue
        self.prev: Word | None = None
        self.next: Word | None = None

    @typing.overload
    def __getitem__(self, key: int) -> Square:
        ...
    @typing.overload
    def __getitem__(self, key: slice) -> list[Square]:
        ...
    def __getitem__(self, key):
        return self.squares[key]

    def __len__(self) -> int:
        return len(self.squares)

    def __iter__(self) -> Iterator[Square]:
        yield from self.squares

class Clue:
    def __init__(self, number: int, text: str) -> None:
        self.number = number
        self.text   = text
        self.lines  = textwrap.TextWrapper(width=28).wrap(self.text)

class Cursor:
    def __init__(self, square: Square, direction: Direction, puzzle: Puzzle) -> None:
        self.square    = square
        self.direction = direction
        self.puzzle    = puzzle

    def other_direction(self) -> Direction:
        return Direction.DOWN if self.direction is Direction.ACROSS else Direction.ACROSS

    def move(self, dx: int, dy: int) -> Cursor:
        x, y = self.square
        while True:
            x += dx
            y += dy
            try:
                square = self.puzzle.get_square(x, y)
            except IndexError:
                return self
            if square is not None:
                return Cursor(square, self.direction, self.puzzle)
            else:
                dx = sign(dx)
                dy = sign(dy)

    def topmost(self) -> Square:
        column = self.puzzle.get_column(self.square.x)
        return next(filter(None, column))

    def bottommost(self) -> Square:
        column = self.puzzle.get_column(self.square.x)
        return next(filter(None, reversed(column)))

    def leftmost(self) -> Square:
        row = self.puzzle.get_row(self.square.y)
        return next(filter(None, row))

    def rightmost(self) -> Square:
        row = self.puzzle.get_row(self.square.y)
        return next(filter(None, reversed(row)))

    def next_squares(self) -> Iterator[tuple[Square, Direction]]:
        start = self.square
        square = start.next[self.direction]
        while square is not None:
            yield square, self.direction
            square = square.next[self.direction]
        square = self.puzzle.first_square(self.other_direction())
        while square is not None:
            yield square, self.other_direction()
            square = square.next[self.other_direction()]
        square = self.puzzle.first_square(self.direction)
        while square is not start:
            assert square is not None
            yield square, self.direction
            square = square.next[self.direction]

    def prev_squares(self) -> Iterator[tuple[Square, Direction]]:
        start = self.square
        square = start.prev[self.direction]
        while square is not None:
            yield square, self.direction
            square = square.prev[self.direction]
        square = self.puzzle.last_square(self.other_direction())
        while square is not None:
            yield square, self.other_direction()
            square = square.prev[self.other_direction()]
        square = self.puzzle.last_square(self.direction)
        while square is not start:
            assert square is not None
            yield square, self.direction
            square = square.prev[self.direction]

    def go_to_next_square(self, condition: Callable[[Square, Direction], bool] | None = None) -> Cursor:
        for square, direction in self.next_squares():
            if condition is None or condition(square, direction):
                return Cursor(square, direction, self.puzzle)
        return self

    def go_to_prev_square(self, condition: Callable[[Square, Direction], bool] | None = None) -> Cursor:
        for square, direction in self.prev_squares():
            if condition is None or condition(square, direction):
                return Cursor(square, direction, self.puzzle)
        return self

    def h(self) -> Cursor:
        return self.move(-1, 0)

    def j(self) -> Cursor:
        return self.move(0, 1)

    def k(self) -> Cursor:
        return self.move(0, -1)

    def l(self) -> Cursor:
        return self.move(1, 0)

    def gg(self) -> Cursor:
        square = self.topmost() if self.direction is Direction.ACROSS else self.leftmost()
        return Cursor(square, self.direction, self.puzzle)

    def G(self, count: int | None) -> Cursor:
        # G: go to bottom
        if count is None:
            square = self.bottommost() if self.direction is Direction.ACROSS else self.rightmost()
            return Cursor(square, self.direction, self.puzzle)
        # [count]G: go to square with clue number [count]
        for square in self.puzzle.itersquares():
            if square.clue_number() == count:
                return Cursor(square, self.direction, self.puzzle)
        return self

    def zero(self) -> Cursor:
        square = self.leftmost() if self.direction is Direction.ACROSS else self.topmost()
        return Cursor(square, self.direction, self.puzzle)

    def dollar(self) -> Cursor:
        square = self.rightmost() if self.direction is Direction.ACROSS else self.bottommost()
        return Cursor(square, self.direction, self.puzzle)

    def w(self) -> Cursor:
        return self.go_to_next_square(lambda square, direction: square.is_start(direction))

    def b(self) -> Cursor:
        return self.go_to_prev_square(lambda square, direction: square.is_start(direction))

    def e(self) -> Cursor:
        return self.go_to_next_square(lambda square, direction: square.is_end(direction))

    def ge(self) -> Cursor:
        return self.go_to_prev_square(lambda square, direction: square.is_end(direction))

    def double_right_square_bracket(self) -> Cursor:
        def condition(square: Square, direction: Direction) -> bool:
            return (square.is_filled()
                    and (square.is_start(direction)
                         or ((prev_square := square.prev[direction]) is not None
                             and prev_square.guess is None)))
        return self.go_to_next_square(condition)

    def double_left_square_bracket(self) -> Cursor:
        def condition(square: Square, direction: Direction) -> bool:
            return (square.is_filled()
                    and (square.is_end(direction)
                         or ((next_square := square.next[direction]) is not None
                             and next_square.guess is None)))
        return self.go_to_prev_square(condition)

    def right_curly_bracket(self) -> Cursor:
        def condition(square: Square, direction: Direction) -> bool:
            return (square.guess is None
                    and (square.is_start(direction)
                         or ((prev_square := square.prev[direction]) is not None
                             and prev_square.is_filled())))
        return self.go_to_next_square(condition)

    def left_curly_bracket(self) -> Cursor:
        def condition(square: Square, direction: Direction) -> bool:
            return (square.guess is None
                    and (square.is_end(direction)
                         or ((next_square := square.next[direction]) is not None
                             and next_square.is_filled())))
        return self.go_to_prev_square(condition)

    def r(self, char: str) -> Cursor:
        try:
            self.square.set(char)
        except ValueError:
            pass
        return self

    def x(self) -> Cursor:
        self.square.unset()
        return self

    def cw(self) -> Cursor:
        word = self.square.word[self.direction]
        for square in word:
            square.unset()
        return Cursor(word[0], self.direction, self.puzzle)

    def dw(self) -> Cursor:
        word = self.square.word[self.direction]
        for square in word:
            square.unset()
        return self

    def space(self) -> Cursor:
        return Cursor(self.square, self.other_direction(), self.puzzle)

    def tilde(self) -> Cursor:
        self.square.toggle_pencil()
        return self.go_to_next_square()

    def type(self, char: str) -> Cursor:
        try:
            self.square.set(char)
        except ValueError:
            return self
        else:
            return self.go_to_next_square()

    def backspace(self) -> Cursor:
        cursor = self.go_to_prev_square()
        cursor.square.unset()
        return cursor

    def displayed_coords(self) -> tuple[int, int]:
        x, y = self.square
        return (2 + x * 4, 1 + y * 2)

if __name__ == '__main__':
    Game(puz.read(sys.argv[1])).run()
