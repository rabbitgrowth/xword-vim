from __future__ import annotations
from collections.abc import Callable, Iterator
import collections
import enum
import itertools

def sign(n: int) -> int:
    return (n > 0) - (n < 0)

class Direction(enum.Enum):
    ACROSS = enum.auto()
    DOWN   = enum.auto()

class Grid:
    def __init__(self, solution: list[list[str | None]]) -> None:
        self.grid = [[Square(x, y, solution) for x, solution in enumerate(row)]
                     for y, row in enumerate(solution)]

        self.width  = len(self.grid[0])
        self.height = len(self.grid)

        # Map starts of runs of white squares to those runs of white squares
        starts: dict[Square, dict[Direction, list[Square]]] = collections.defaultdict(dict)
        for direction, grid in zip(Direction, (self.grid, self.transpose())):
            for row in grid:
                for is_white, square_group in itertools.groupby(row, lambda square: square.is_white()):
                    if is_white:
                        square_list = list(square_group)
                        start = square_list[0]
                        starts[start][direction] = square_list

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
                for square in word.squares:
                    square.word[direction] = word
                    if prev_square is not None:
                        square.prev[direction] = prev_square
                        prev_square.next[direction] = square
                    prev_square = square
                prev_word = word

    def transpose(self) -> list[list[Square]]:
        return list(map(list, zip(*self.grid)))

    def within_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> Square | None:
        if self.within_bounds(x, y):
            return self.grid[y][x]
        return None

    def first_word(self, direction: Direction) -> Word:
        return self.words[direction][0]

    def last_word(self, direction: Direction) -> Word:
        return self.words[direction][-1]

    def first_square(self, direction: Direction) -> Square:
        return self.first_word(direction).first_square()

    def last_square(self, direction: Direction) -> Square:
        return self.last_word(direction).last_square()

class Word:
    def __init__(self, squares: list[Square], clue_number: int) -> None:
        self.squares     = squares
        self.clue_number = clue_number

        self.prev: Word | None = None
        self.next: Word | None = None

    def first_square(self) -> Square:
        return self.squares[0]

    def last_square(self) -> Square:
        return self.squares[-1]

class Square:
    def __init__(self, x: int, y: int, solution: str | None) -> None:
        self.x = x
        self.y = y
        self.solution = solution

        self.prev: dict[Direction, Square | None] = {direction: None for direction in Direction}
        self.next: dict[Direction, Square | None] = {direction: None for direction in Direction}
        self.word: dict[Direction, Word   | None] = {direction: None for direction in Direction}

    @property
    def coords(self) -> tuple[int, int]:
        return self.x, self.y

    def is_black(self) -> bool:
        return self.solution is None

    def is_white(self) -> bool:
        return not self.is_black()

    def is_start(self, direction: Direction) -> bool:
        word = self.word[direction]
        if word is None:
            return False
        return self is word.squares[0]

    def is_end(self, direction: Direction) -> bool:
        word = self.word[direction]
        if word is None:
            return False
        return self is word.squares[-1]

class Cursor:
    def __init__(self, square: Square, direction: Direction, grid: Grid) -> None:
        self.square    = square
        self.direction = direction
        self.grid      = grid

    @property
    def other_direction(self) -> Direction:
        return Direction.DOWN if self.direction is Direction.ACROSS else Direction.ACROSS

    def move(self, dx: int, dy: int) -> Cursor:
        x, y = self.square.coords
        while True:
            x += dx
            y += dy
            square = self.grid.get(x, y)
            if square is None:
                return self
            elif square.is_white():
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
