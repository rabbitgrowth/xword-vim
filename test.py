import itertools
import operator
import unittest

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
        solution = [[None if char == '.' else char for char in line]
                    for line in ['.RACED.',
                                 'BELARUS',
                                 'LABTECH',
                                 'ALE.CHE',
                                 'KIRSTIE',
                                 'ESTREET',
                                 '.MAIDS.']]
        self.grid = xword.Grid(solution)

    def test_width_and_height(self):
        self.assertEqual(self.grid.width,  7)
        self.assertEqual(self.grid.height, 7)

    def test_square_runs(self):
        self.assertEqual([''.join(square.solution for square in word)
                          for word in self.grid.words[xword.Direction.ACROSS]],
                         ['RACED', 'BELARUS', 'LABTECH', 'ALE', 'CHE', 'KIRSTIE', 'ESTREET', 'MAIDS'])
        self.assertEqual([''.join(square.solution for square in word)
                          for word in self.grid.words[xword.Direction.DOWN]],
                         ['REALISM', 'ALBERTA', 'CAT', 'ERECTED', 'DUCHIES', 'BLAKE', 'SHEET', 'SRI'])

    def test_word_links(self):
        word = self.grid.words[xword.Direction.ACROSS][0]
        self.assertIsNone(word.prev)
        self.assertIs(word.next.prev, word)
        self.assertEqual(''.join(square.solution for square in word.next), 'BELARUS')

    def test_square_links(self):
        square = self.grid.get(1, 0)
        self.assertIsNone(square.prev[xword.Direction.ACROSS])
        self.assertIs(square.next[xword.Direction.ACROSS].prev[xword.Direction.ACROSS], square)
        for _ in range(10):
            square = square.next[xword.Direction.ACROSS]
        self.assertEqual(square.solution, 'U')
        for _ in range(10):
            square = square.next[xword.Direction.DOWN]
        self.assertEqual(square.solution, 'E')

    def test_up_down_left_right(self):
        cursor = xword.Cursor(self.grid.get(2, 3), xword.Direction.ACROSS, self.grid)
        self.assertEqual(tuple(cursor.h().square), (1, 3))
        self.assertEqual(tuple(cursor.j().square), (2, 4))
        self.assertEqual(tuple(cursor.k().square), (2, 2))
        self.assertEqual(tuple(cursor.l().square), (4, 3)) # skip black square

    def test_next_squares(self):
        cursor = xword.Cursor(self.grid.get(2, 3), xword.Direction.ACROSS, self.grid)
        self.assertEqual([(direction, ''.join(square.solution for square, _ in pairs))
                          for direction, pairs in itertools.groupby(cursor.next_squares(), key=operator.itemgetter(1))],
                         [(xword.Direction.ACROSS, 'CHEKIRSTIEESTREETMAIDS'),
                          (xword.Direction.DOWN,   'REALISMALBERTACATERECTEDDUCHIESBLAKESHEETSRI'),
                          (xword.Direction.ACROSS, 'RACEDBELARUSLABTECHAL')])

    def test_word_motions(self):
        cursor = xword.Cursor(self.grid.get(3, 0), xword.Direction.ACROSS, self.grid)
        cursor = cursor.w()
        self.assertEqual(tuple(cursor.square), (0, 1))
        cursor = cursor.b().b()
        self.assertEqual(tuple(cursor.square), (3, 4))
        cursor = cursor.e().e().e()
        self.assertEqual(tuple(cursor.square), (6, 1))
        cursor = cursor.ge().ge().ge().ge()
        self.assertEqual(tuple(cursor.square), (0, 5))

    def test_rendering(self):
        cursor = xword.Cursor(self.grid.get(6, 3), xword.Direction.DOWN, self.grid)
        self.assertEqual(self.grid.render(cursor), ['┌───┬1──┬2──┬3──┬4──┬5──┬───┐',
                                                    '│░░░│   │   │   │   │   │░░░│',
                                                    '├6──┼───┼───┼───┼───┼───╆7━━┪',
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

if __name__ == '__main__':
    unittest.main()
