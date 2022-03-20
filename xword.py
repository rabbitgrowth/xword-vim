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

import term

def sign(n: int) -> int:
    return (n > 0) - (n < 0)

class Direction(enum.Enum):
    ACROSS = enum.auto()
    DOWN   = enum.auto()

class Mode(enum.Enum):
    NORMAL = enum.auto()
    INSERT = enum.auto()

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

class Puzzle:
    def __init__(self, solutions: list[list[str | None]], clues: list[str]) -> None:
        self.grid   = Grid(solutions, clues)
        self.cursor = Cursor(self.grid.first_square(Direction.ACROSS), Direction.ACROSS, self.grid)
        self.clues  = {direction: Clues(direction, self.grid) for direction in Direction}
        self.mode   = Mode.NORMAL
        self.message: str | None = None

    def run(self) -> None:
        old_attributes = termios.tcgetattr(sys.stdin)
        term.enter_raw_mode()
        term.enter_alternate_buffer()
        try:
            while True:
                self.render()
                self.handle_input()
        finally:
            term.leave_alternate_buffer()
            term.show_cursor()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attributes)

    def render(self) -> None:
        term.clear_screen()
        term.move_cursor(0, 0)
        for y, line in enumerate(self.grid.render(self.cursor)):
            term.move_cursor(0, y)
            term.write(line)
        for (direction, clues), x_offset, title in zip(self.clues.items(), (2, 36), ('Across', 'Down')):
            for y, line in enumerate([term.bold(title),
                                      *clues.render(self.cursor, self.grid.displayed_height - 1)]):
                term.move_cursor(self.grid.displayed_width + x_offset, y)
                term.write(line)
        if self.message is not None:
            term.move_cursor(0, self.grid.displayed_height + 1)
            term.write(self.message)
        term.move_cursor(*self.cursor.displayed_coords())
        term.show_cursor()
        term.flush()

    def handle_input(self) -> None:
        chars = []
        def append(char):
            chars.append(char)
            term.save_cursor()
            term.move_cursor(self.grid.displayed_width + 60, self.grid.displayed_height + 1)
            term.write(''.join(chars[-8:]))
            term.restore_cursor()
            term.flush()
        while True:
            char = term.read_char()
            if char.isdigit() and not (char == '0' and not chars):
                append(char)
            else:
                break
        count = int(''.join(chars)) if chars else None # distinguish between G and 1G
        if self.mode is Mode.NORMAL:
            if char == 'i':
                self.enter_insert_mode()
            elif char == 'h':
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
            elif char == 'r':
                term.underline_cursor()
                term.flush()
                next_char = term.read_char()
                self.cursor = self.cursor.r(next_char)
                term.block_cursor()
            elif char == 'x':
                self.cursor = self.cursor.x()
            elif char == ' ':
                self.cursor = self.cursor.toggle_direction()
            elif char == ':':
                self.handle_command(self.read_command())
        elif self.mode is Mode.INSERT:
            if char == '\x1b':
                self.leave_insert_mode()
            elif char == '\x7f':
                self.cursor = self.cursor.backspace()
            elif char == 'j':
                append(char)
                next_char = term.read_char()
                if next_char == 'k':
                    self.leave_insert_mode()
                else:
                    self.cursor = self.cursor.type(char)
                    self.cursor = self.cursor.type(next_char)
            else:
                self.cursor = self.cursor.type(char)

    def read_command(self) -> str:
        self.message = None
        term.move_cursor(0, self.grid.displayed_height + 1)
        term.clear_rest_of_line()
        term.leave_raw_mode()
        command = input(':')
        term.enter_raw_mode()
        term.hide_cursor() # prevent cursor from briefly appearing under the colon
        term.flush()
        return command

    def handle_command(self, command: str) -> None:
        if command.isdigit():
            self.cursor = self.cursor.G(int(command))
        elif command == 'q':
            sys.exit()
        elif command == 'smile':
            self.show_message(':-)')

    def enter_insert_mode(self) -> None:
        self.mode = Mode.INSERT
        self.show_message('-- INSERT --')
        term.ibeam_cursor()

    def leave_insert_mode(self) -> None:
        self.mode = Mode.NORMAL
        self.show_message(None)
        term.block_cursor()

    def show_message(self, message: str | None) -> None:
        self.message = message

class Grid:
    def __init__(self, solutions: list[list[str | None]], clues: list[str]) -> None:
        self.grid = [[Square(x, y, solution, None) if solution is not None else None
                      for x, solution in enumerate(row)]
                     for y, row in enumerate(solutions)]

        self.width            = len(self.grid[0])
        self.height           = len(self.grid)
        self.displayed_width  = self.width  * 4 + 1
        self.displayed_height = self.height * 2 + 1

        # Map starts of runs of white squares to those runs of white squares
        starts: dict[Square, dict[Direction, list[Square]]] = collections.defaultdict(dict)
        for direction, grid in zip(Direction, (self.grid, self.transpose())):
            for row in grid:
                run = []
                for square in row:
                    if square is not None:
                        run.append(square)
                    elif run:
                        starts[run[0]][direction] = run
                        run = []
                if run:
                    starts[run[0]][direction] = run

        # Assign clues to words
        clue_iterator = iter(clues)
        self.words: dict[Direction, list[Word]] = collections.defaultdict(list)
        for clue_number, start in enumerate(sorted(starts, key=lambda square: (square.y, square.x)), start=1):
            for direction in Direction:
                squares = starts[start].get(direction)
                if squares is not None:
                    clue = Clue(clue_number, next(clue_iterator))
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

    def render(self, cursor: Cursor) -> Iterator[str]:
        boldness = {}
        x, y = cursor.word[0]
        if cursor.direction == Direction.ACROSS:
            boldness[(x, y    )] = Shape.DOWN_AND_RIGHT
            boldness[(x, y + 1)] = Shape.UP_AND_RIGHT
            for x, y in cursor.word[1:]:
                boldness[(x, y    )] = Shape.HORIZONTAL
                boldness[(x, y + 1)] = Shape.HORIZONTAL
            boldness[(x + 1, y    )] = Shape.DOWN_AND_LEFT
            boldness[(x + 1, y + 1)] = Shape.UP_AND_LEFT
        else:
            boldness[(x,     y)] = Shape.DOWN_AND_RIGHT
            boldness[(x + 1, y)] = Shape.DOWN_AND_LEFT
            for x, y in cursor.word[1:]:
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
                    if square is cursor.word[0]:
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

class Square:
    def __init__(self, x: int, y: int, solution: str, guess: str | None) -> None:
        self.x        = x
        self.y        = y
        self.solution = solution
        self.guess    = guess
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

    def clue_number(self) -> int | None:
        for direction in Direction:
            if self.is_start(direction):
                return self.word[direction].clue.number
        return None

    def set(self, char: str | None) -> None:
        if char is None:
            self.guess = None
        elif char.isalnum():
            self.guess = char.upper()
        else:
            raise ValueError

    def render(self) -> str:
        guess = self.guess if self.guess is not None else ' '
        return f' {guess} '

class Cursor:
    def __init__(self, square: Square, direction: Direction, grid: Grid) -> None:
        self.square    = square
        self.direction = direction
        self.grid      = grid

    @property
    def word(self) -> Word:
        return self.square.word[self.direction]

    @property
    def other_direction(self) -> Direction:
        return Direction.DOWN if self.direction is Direction.ACROSS else Direction.ACROSS

    def toggle_direction(self) -> Cursor:
        return Cursor(self.square, self.other_direction, self.grid)

    def move(self, dx: int, dy: int) -> Cursor:
        x, y = self.square
        while True:
            x += dx
            y += dy
            try:
                square = self.grid.get_square(x, y)
            except IndexError:
                return self
            if square is not None:
                return Cursor(square, self.direction, self.grid)
            else:
                dx = sign(dx)
                dy = sign(dy)

    def topmost(self) -> Square:
        column = self.grid.get_column(self.square.x)
        return next(filter(None, column))

    def bottommost(self) -> Square:
        column = self.grid.get_column(self.square.x)
        return next(filter(None, reversed(column)))

    def leftmost(self) -> Square:
        row = self.grid.get_row(self.square.y)
        return next(filter(None, row))

    def rightmost(self) -> Square:
        row = self.grid.get_row(self.square.y)
        return next(filter(None, reversed(row)))

    def next_squares(self) -> Iterator[tuple[Square, Direction]]:
        start = self.square
        square = start.next[self.direction]
        while square is not None:
            yield square, self.direction
            square = square.next[self.direction]
        square = self.grid.first_square(self.other_direction)
        while square is not None:
            yield square, self.other_direction
            square = square.next[self.other_direction]
        square = self.grid.first_square(self.direction)
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
        square = self.grid.last_square(self.other_direction)
        while square is not None:
            yield square, self.other_direction
            square = square.prev[self.other_direction]
        square = self.grid.last_square(self.direction)
        while square is not start:
            assert square is not None
            yield square, self.direction
            square = square.prev[self.direction]

    def move_to_next_square(self, condition: Callable[[Square, Direction], bool] | None = None) -> Cursor:
        for square, direction in self.next_squares():
            if condition is None or condition(square, direction):
                return Cursor(square, direction, self.grid)
        return self

    def move_to_prev_square(self, condition: Callable[[Square, Direction], bool] | None = None) -> Cursor:
        for square, direction in self.prev_squares():
            if condition is None or condition(square, direction):
                return Cursor(square, direction, self.grid)
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
        return Cursor(square, self.direction, self.grid)

    def G(self, count: int | None) -> Cursor:
        # G: go to bottom
        if count is None:
            square = self.bottommost() if self.direction is Direction.ACROSS else self.rightmost()
            return Cursor(square, self.direction, self.grid)
        # nG: go to square with clue number n
        for square in self.grid.itersquares():
            if square.clue_number() == count:
                return Cursor(square, self.direction, self.grid)
        return self

    def zero(self) -> Cursor:
        square = self.leftmost() if self.direction is Direction.ACROSS else self.topmost()
        return Cursor(square, self.direction, self.grid)

    def dollar(self) -> Cursor:
        square = self.rightmost() if self.direction is Direction.ACROSS else self.bottommost()
        return Cursor(square, self.direction, self.grid)

    def w(self) -> Cursor:
        return self.move_to_next_square(lambda square, direction: square.is_start(direction))

    def b(self) -> Cursor:
        return self.move_to_prev_square(lambda square, direction: square.is_start(direction))

    def e(self) -> Cursor:
        return self.move_to_next_square(lambda square, direction: square.is_end(direction))

    def ge(self) -> Cursor:
        return self.move_to_prev_square(lambda square, direction: square.is_end(direction))

    def r(self, char: str) -> Cursor:
        try:
            self.square.set(char)
        except ValueError:
            pass
        return self

    def x(self) -> Cursor:
        self.square.set(None)
        return self

    def type(self, char: str) -> Cursor:
        try:
            self.square.set(char)
        except ValueError:
            return self
        else:
            return self.move_to_next_square()

    def backspace(self) -> Cursor:
        cursor = self.move_to_prev_square()
        cursor.square.set(None)
        return cursor

    def displayed_coords(self) -> tuple[int, int]:
        x, y = self.square
        return (2 + x * 4, 1 + y * 2)

class Clues:
    def __init__(self, direction: Direction, grid: Grid) -> None:
        wrap = textwrap.TextWrapper(width=28).wrap
        self.direction = direction
        self.prerender = {clue.number: wrap(clue.text) for clue in grid.iterclues(direction)}
        start_index = 0
        self.start_indices = {}
        for number, clue_lines in self.prerender.items():
            self.start_indices[number] = start_index
            start_index += len(clue_lines)

    def render(self, cursor: Cursor, height: int) -> list[str]:
        lines = []
        current_clue_number = cursor.square.word[self.direction].clue.number
        for number, clue_lines in self.prerender.items():
            for i, clue_line in enumerate(clue_lines):
                if i == 0:
                    arrow = '>' if number == current_clue_number else ' '
                    line = f'{arrow}{number:>2} {clue_line}'
                else:
                    line = f'    {clue_line}'
                if number == current_clue_number and self.direction is cursor.direction:
                    line = term.bold(line)
                lines.append(line)
        start_index = min(self.start_indices[current_clue_number], max(len(lines) - height, 0))
        return lines[start_index:start_index+height]

class Clue:
    def __init__(self, number: int, text: str) -> None:
        self.number = number
        self.text   = text

def parse(file):
    f.seek(0x2c) # skip checksums, file magic, etc.
    width, height, nclues = struct.unpack('<BBH', f.read(4))
    f.seek(4, 1) # skip unknown bitmask and scrambled tag
    solutions = [[None if char == '.' else char
                  for char in f.read(width).decode('iso-8859-1')]
                 for _ in range(height)]
    f.seek(width * height, 1) # skip guesses
    strings = f.read().decode('iso-8859-1').rstrip('\0').split('\0')
    # skip title, author, and copyright information
    clues = strings[3:3+nclues]
    # skip notes
    assert len(clues) == nclues
    return solutions, clues

if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        Puzzle(*parse(f)).run()
