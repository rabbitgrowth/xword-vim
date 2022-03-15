from __future__ import annotations
from collections.abc import Callable, Iterator
import collections
import copy
import enum
import sys
import termios
import typing

import ansi

def sign(n: int) -> int:
    return (n > 0) - (n < 0)

class Direction(enum.Enum):
    ACROSS = enum.auto()
    DOWN   = enum.auto()

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
    def __init__(self, solutions: list[list[str | None]]) -> None:
        self.grid   = Grid(solutions)
        self.cursor = Cursor(self.grid.first_square(Direction.ACROSS), Direction.ACROSS, self.grid)

    def run(self) -> None:
        old_attributes = termios.tcgetattr(sys.stdin)
        new_attributes = copy.deepcopy(old_attributes)
        new_attributes[3] &= ~(termios.ECHO | termios.ICANON) # lflags
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_attributes)
        ansi.enter_alternate_buffer()
        try:
            while True:
                self.render()
                self.handle_input()
        finally:
            ansi.leave_alternate_buffer()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attributes)

    def render(self) -> None:
        ansi.clear_screen()
        ansi.move_cursor(0, 0)
        grid_lines, cursor_coords = self.grid.render(self.cursor)
        sys.stdout.write('\r\n'.join(grid_lines))
        ansi.move_cursor(*cursor_coords)
        sys.stdout.flush()

    def read_char(self) -> str:
        return sys.stdin.read(1)

    def handle_input(self) -> None:
        char = self.read_char()
        if char == 'h':
            self.cursor = self.cursor.h()
        elif char == 'j':
            self.cursor = self.cursor.j()
        elif char == 'k':
            self.cursor = self.cursor.k()
        elif char == 'l':
            self.cursor = self.cursor.l()
        elif char == 'w':
            self.cursor = self.cursor.w()
        elif char == 'b':
            self.cursor = self.cursor.b()
        elif char == 'e':
            self.cursor = self.cursor.e()
        elif char == 'g':
            char = self.read_char()
            if char == 'e':
                self.cursor = self.cursor.ge()
        elif char == ' ':
            self.cursor = self.cursor.toggle_direction()

class Grid:
    def __init__(self, solutions: list[list[str | None]]) -> None:
        self.grid = [[Square(x, y, solution) if solution is not None else None
                      for x, solution in enumerate(row)]
                     for y, row in enumerate(solutions)]
        self.width  = len(self.grid[0])
        self.height = len(self.grid)

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

        # Assign clue numbers to words
        self.words: dict[Direction, list[Word]] = collections.defaultdict(list)
        for clue_number, start in enumerate(sorted(starts, key=lambda square: (square.y, square.x)), start=1):
            for direction in Direction:
                squares = starts[start].get(direction)
                if squares is not None:
                    word = Word(squares, clue_number)
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

    def within_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> Square | None:
        if not self.within_bounds(x, y):
            raise IndexError
        return self.grid[y][x]

    def first_square(self, direction: Direction) -> Square:
        return self.words[direction][0][0]

    def last_square(self, direction: Direction) -> Square:
        return self.words[direction][-1][-1]

    def render(self, cursor: Cursor) -> tuple[list[str], tuple[int, int]]:
        grid_lines = []
        boldness   = {}
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
                        square = self.get(x, y)
                        if square is not None:
                            clue_number = square.clue_number()
                            clue_number_string = str(clue_number) if clue_number is not None else ''
                        else:
                            clue_number_string = ''
                    else:
                        clue_number_string = ''
                    horizontal_edge = clue_number_string.ljust(3, horizontal_edge_char)
                    line += horizontal_edge
            grid_lines.append(line)
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
                        square = self.get(x, y)
                        line += '░░░' if square is None else square.render()
                grid_lines.append(line)
        x, y = cursor.square
        cursor_coords = (2 + x * 4, 1 + y * 2)
        return grid_lines, cursor_coords

class Word:
    def __init__(self, squares: list[Square], clue_number: int) -> None:
        self.squares     = squares
        self.clue_number = clue_number
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
    def __init__(self, x: int, y: int, solution: str) -> None:
        self.x = x
        self.y = y
        self.solution = solution
        self.prev: dict[Direction, Square | None] = dict.fromkeys(Direction)
        self.next: dict[Direction, Square | None] = dict.fromkeys(Direction)
        self.word: dict[Direction, Word   | None] = dict.fromkeys(Direction)

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y

    def is_start(self, direction: Direction) -> bool:
        word = self.word[direction]
        if word is None:
            return False
        return self is word[0]

    def is_end(self, direction: Direction) -> bool:
        word = self.word[direction]
        if word is None:
            return False
        return self is word[-1]

    def clue_number(self) -> int | None:
        for direction in Direction:
            if self.is_start(direction):
                word = self.word[direction]
                assert word is not None
                return word.clue_number
        return None

    def render(self) -> str:
        return f'   ' # TODO: hard-code to be blank for now

class Cursor:
    def __init__(self, square: Square, direction: Direction, grid: Grid) -> None:
        self.square    = square
        self.direction = direction
        self.grid      = grid

    @property
    def word(self) -> Word:
        word = self.square.word[self.direction]
        assert word is not None
        return word

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
                square = self.grid.get(x, y)
            except IndexError:
                return self
            if square is not None:
                return Cursor(square, self.direction, self.grid)
            else:
                dx = sign(dx)
                dy = sign(dy)

    def h(self) -> Cursor:
        return self.move(-1, 0)

    def j(self) -> Cursor:
        return self.move(0, 1)

    def k(self) -> Cursor:
        return self.move(0, -1)

    def l(self) -> Cursor:
        return self.move(1, 0)

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

    def jump_to_next_square(self, condition: Callable[[Square, Direction], bool]) -> Cursor:
        for square, direction in self.next_squares():
            if condition(square, direction):
                return Cursor(square, direction, self.grid)
        return self

    def jump_to_prev_square(self, condition: Callable[[Square, Direction], bool]) -> Cursor:
        for square, direction in self.prev_squares():
            if condition(square, direction):
                return Cursor(square, direction, self.grid)
        return self

    def w(self) -> Cursor:
        return self.jump_to_next_square(lambda square, direction: square.is_start(direction))

    def b(self) -> Cursor:
        return self.jump_to_prev_square(lambda square, direction: square.is_start(direction))

    def e(self) -> Cursor:
        return self.jump_to_next_square(lambda square, direction: square.is_end(direction))

    def ge(self) -> Cursor:
        return self.jump_to_prev_square(lambda square, direction: square.is_end(direction))
