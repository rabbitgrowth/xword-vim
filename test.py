import itertools
import operator
import pathlib
import unittest

import puz

import term
import xword

class TestHelpers(unittest.TestCase):
    def test_sign(self):
        self.assertEqual(xword.sign(2),   1)
        self.assertEqual(xword.sign(1),   1)
        self.assertEqual(xword.sign(0),   0)
        self.assertEqual(xword.sign(-1), -1)
        self.assertEqual(xword.sign(-2), -1)

class TestMiniPuzzle(unittest.TestCase):
    def setUp(self):
        self.puzzle = xword.Puzzle(puz.read('test.puz'))

    def test_width_and_height(self):
        self.assertEqual(self.puzzle.width,  7)
        self.assertEqual(self.puzzle.height, 7)

    def test_bounds_checking(self):
        with self.assertRaises(IndexError):
            self.puzzle.get_square(7, 6)
        with self.assertRaises(IndexError):
            self.puzzle.get_square(0, -1)

    def test_words(self):
        self.assertEqual([''.join(square.solution for square in word)
                          for word in self.puzzle.iterwords(xword.Direction.ACROSS)],
                         ['RACED', 'BELARUS', 'LABTECH', 'ALE', 'CHE', 'KIRSTIE', 'ESTREET', 'MAIDS'])
        self.assertEqual([''.join(square.solution for square in word)
                          for word in self.puzzle.iterwords(xword.Direction.DOWN)],
                         ['REALISM', 'ALBERTA', 'CAT', 'ERECTED', 'DUCHIES', 'BLAKE', 'SHEET', 'SRI'])

    def test_clues(self):
        self.assertEqual([(clue.number, clue.text)
                          for clue in self.puzzle.iterclues(xword.Direction.ACROSS)],
                         [(1,  'Competed in the downhill or super-G'),
                          (6,  'Country between Ukraine and Lithuania'),
                          (8,  'Worker in a bio building'),
                          (9,  'The "A" of I.P.A.'),
                          (10, 'Michael of "S.N.L."'),
                          (11, 'Alley who\'s a spokesperson for Jenny Craig'),
                          (13, '___ Band, backers of Bruce Springsteen'),
                          (14, 'Hotel cleaners')])
        self.assertEqual([(clue.number, clue.text)
                          for clue in self.puzzle.iterclues(xword.Direction.DOWN)],
                         [(1,  'Painting style of Winslow Homer and Edward Hopper'),
                          (2,  'Canadian province that borders Montana'),
                          (3,  'Sofa scratcher'),
                          (4,  'Put up, as a building'),
                          (5,  'Territories for English nobility'),
                          (6,  'Country star Shelton'),
                          (7,  'Unit of fabric or ice'),
                          (12, '___ Lanka')])

    def test_word_links(self):
        word = next(self.puzzle.iterwords(xword.Direction.ACROSS))
        self.assertIsNone(word.prev)
        self.assertIs(word.next.prev, word)
        self.assertEqual(''.join(square.solution for square in word.next), 'BELARUS')

    def test_square_links(self):
        square = next(self.puzzle.itersquares())
        self.assertIsNone(square.prev[xword.Direction.ACROSS])
        self.assertIs(square.next[xword.Direction.ACROSS].prev[xword.Direction.ACROSS], square)
        for _ in range(10):
            square = square.next[xword.Direction.ACROSS]
        self.assertEqual(square.solution, 'U')
        for _ in range(10):
            square = square.next[xword.Direction.DOWN]
        self.assertEqual(square.solution, 'E')

    def test_next_squares(self):
        square = self.puzzle.get_square(2, 3)
        cursor = xword.Cursor(square, xword.Direction.ACROSS, self.puzzle)
        self.assertEqual([(direction, ''.join(square.solution for square, _ in pairs))
                          for direction, pairs in itertools.groupby(cursor.next_squares(), key=operator.itemgetter(1))],
                         [(xword.Direction.ACROSS, 'CHEKIRSTIEESTREETMAIDS'),
                          (xword.Direction.DOWN,   'REALISMALBERTACATERECTEDDUCHIESBLAKESHEETSRI'),
                          (xword.Direction.ACROSS, 'RACEDBELARUSLABTECHAL')])

    def test_up_down_left_right(self):
        square = self.puzzle.get_square(2, 3)
        cursor = xword.Cursor(square, xword.Direction.ACROSS, self.puzzle)
        self.assertEqual(tuple(cursor.h().square), (1, 3))
        self.assertEqual(tuple(cursor.j().square), (2, 4))
        self.assertEqual(tuple(cursor.k().square), (2, 2))
        self.assertEqual(tuple(cursor.l().square), (4, 3)) # skip black square

    def test_word_motions(self):
        square = self.puzzle.get_square(3, 0)
        cursor = xword.Cursor(square, xword.Direction.ACROSS, self.puzzle)
        cursor = cursor.w()
        self.assertEqual(tuple(cursor.square), (0, 1))
        cursor = cursor.b().b()
        self.assertEqual(tuple(cursor.square), (3, 4))
        cursor = cursor.e().e().e()
        self.assertEqual(tuple(cursor.square), (6, 1))
        cursor = cursor.ge().ge().ge().ge()
        self.assertEqual(tuple(cursor.square), (0, 5))

    def test_text_editing(self):
        square = next(self.puzzle.itersquares())
        word   = next(self.puzzle.iterwords(xword.Direction.ACROSS))
        cursor = xword.Cursor(square, xword.Direction.ACROSS, self.puzzle)
        self.assertEqual(tuple(cursor.square), (1, 0))
        self.assertEqual([square.guess for square in word], [None, None, None, None, None])
        cursor = cursor.type('s').type('k').type('i').type('d')
        self.assertEqual(tuple(cursor.square), (5, 0))
        self.assertEqual([square.guess for square in word], ['S', 'K', 'I', 'D', None])
        cursor = cursor.backspace()
        self.assertEqual(tuple(cursor.square), (4, 0))
        self.assertEqual([square.guess for square in word], ['S', 'K', 'I', None, None])
        cursor = cursor.type('e').type('d')
        self.assertEqual(tuple(cursor.square), (0, 1))
        self.assertEqual([square.guess for square in word], ['S', 'K', 'I', 'E', 'D'])
        cursor = cursor.b().type('r')
        self.assertEqual(tuple(cursor.square), (2, 0))
        self.assertEqual([square.guess for square in word], ['R', 'K', 'I', 'E', 'D'])
        cursor = cursor.x()
        self.assertEqual(tuple(cursor.square), (2, 0))
        self.assertEqual([square.guess for square in word], ['R', None, 'I', 'E', 'D'])
        cursor = cursor.type('a').r('c')
        self.assertEqual(tuple(cursor.square), (3, 0))
        self.assertEqual([square.guess for square in word], ['R', 'A', 'C', 'E', 'D'])

    def test_pencilling(self):
        square = next(self.puzzle.itersquares())
        word   = next(self.puzzle.iterwords(xword.Direction.ACROSS))
        cursor = xword.Cursor(square, xword.Direction.ACROSS, self.puzzle)
        cursor = cursor.type('S').type('K').type('I').type('e').type('d')
        self.assertEqual([(square.status, square.guess) for square in word],
                         [(xword.Status.PENCILLED_IN, 'S'),
                          (xword.Status.PENCILLED_IN, 'K'),
                          (xword.Status.PENCILLED_IN, 'I'),
                          (xword.Status.NORMAL,       'E'),
                          (xword.Status.NORMAL,       'D')])
        cursor = cursor.b().tilde().tilde().tilde().tilde().tilde()
        self.assertEqual([(square.status, square.guess) for square in word],
                         [(xword.Status.NORMAL,       'S'),
                          (xword.Status.NORMAL,       'K'),
                          (xword.Status.NORMAL,       'I'),
                          (xword.Status.PENCILLED_IN, 'E'),
                          (xword.Status.PENCILLED_IN, 'D')])
        self.assertEqual(tuple(cursor.square), (0, 1))
        cursor = cursor.tilde() # should have no effect on an empty square
        self.assertEqual(tuple(cursor.square), (1, 1))
        square = self.puzzle.get_square(0, 1)
        self.assertEqual((square.status, square.guess), (xword.Status.NORMAL, None))

    def test_toggle_direction(self):
        square = next(self.puzzle.itersquares())
        cursor = xword.Cursor(square, xword.Direction.ACROSS, self.puzzle)
        cursor = cursor.space()
        self.assertIs(cursor.direction, xword.Direction.DOWN)
        cursor = cursor.space()
        self.assertIs(cursor.direction, xword.Direction.ACROSS)

    def test_rendering(self):
        square = self.puzzle.get_square(6, 3)
        cursor = xword.Cursor(square, xword.Direction.DOWN, self.puzzle)
        self.assertEqual(list(self.puzzle.render_grid(cursor)),
                         ['┌───┬1──┬2──┬3──┬4──┬5──┬───┐',
                          '│░░░│   │   │   │   │   │░░░│',
                          '├6──┼───┼───┼───┼───┼───╆7━━┪'.replace('7', term.bold('7')),
                          '│   │   │   │   │   │   ┃   ┃',
                          '├8──┼───┼───┼───┼───┼───╂───┨',
                          '│   │   │   │   │   │   ┃   ┃',
                          '├9──┼───┼───┼───┼10─┼───╂───┨',
                          '│   │   │   │░░░│   │   ┃   ┃',
                          '├11─┼───┼───┼12─┼───┼───╂───┨',
                          '│   │   │   │   │   │   ┃   ┃',
                          '├13─┼───┼───┼───┼───┼───╂───┨',
                          '│   │   │   │   │   │   ┃   ┃',
                          '├───┼14─┼───┼───┼───┼───╄━━━┩',
                          '│░░░│   │   │   │   │   │░░░│',
                          '└───┴───┴───┴───┴───┴───┴───┘'])
        self.assertEqual(cursor.displayed_coords(), (26, 7))

if __name__ == '__main__':
    unittest.main()
