# xword-vim

![Screenshot](screenshot.png)

xword-vim is a terminal interface for solving crossword puzzles with
Vim-like keybindings.

It is a work in progress.

## Keybindings

Like in Vim, you start in *normal mode*, where you can use the following
keys to navigate through the puzzle (these should feel pretty intuitive
if you already use Vim):

- `h` `j` `k` `l`: move left (`h`), down (`j`), up (`k`), or right
  (`l`), skipping over black squares.
- `gg` `G` `0` `$`: jump to the topmost (`gg`), bottommost (`G`),
  leftmost (`0`), or rightmost (`$`) square – if the cursor is in the
  across direction. If it’s in the down direction, the behaviours of
  `gg` `G` and `0` `$` are swapped.
- `<number>G`: jump to the square with the specified clue number.
- `w` `b` `e` `ge`: jump to the next word (`w`), previous word (`b`),
  next end of word (`e`), or previous end of word (`ge`) (“word” meaning
  “run of white squares”). The across words and down words are linked,
  such that if you’re at the last across word and press `w`, you jump to
  the first down word, etc.
- `r<letter>`: replace the current letter with the specified letter.
- `x`: delete the current letter.
- `<Space>`: toggle the direction of the cursor.
- `:q<Enter>`: [quit](https://www.youtube.com/watch?v=TLbfqZBL8t8).

To actually type letters into the puzzle, press `i` to enter *insert
mode*. The cursor turns into an I-beam, and you can type as normal,
using `<Backspace>` to delete mistakes. To leave insert mode and go back
to normal mode, press `<Esc>` or `jk`.

## Todo

In descending order of priority:

- Parse .puz files
- Warn if screen is not big enough
- Exit gracefully on interrupt
- Pencil mode
- Check answers with `:check`
- Reveal answers
- Colours
- Save with `:w`
- More commands
    - `H` `M` `L`
    - `f` `F` `t` `T` `;` `,`
    - `/` `?` `n` `N` (`*` `#` should be pretty useless for crosswords)
    - `incsearch`?
    - `a` to enter insert mode at the next blank square
    - `s` (although it’s only visually different from `i` in our case)
    - `cw` (`ciw`?)
    - `dw` (`diw`?) to delete word, leaving untouched squares that
      belong to a completely filled word in the other direction?
    - `de` `db` `dae`? `d` with any motion??
    - `}` `{` to jump to blank squares and `]]` `[[` to jump to filled
      squares?
    - `]<some letter>` `[<some letter>` to jump to squares marked wrong
    - `u` and `U` or `<C-R>` to undo and redo
    - `<C-O>` `<C-I>`
    - `gi`
- `<Space>` for empty square in insert mode (`r<Space>` should also work
  in normal mode, although `x` is more efficient)
- Count with `h` `j` `k` `l` etc.
- Circled squares
- Rebuses and how on earth to display them
- Config (`.xwordvimrc`?)
    - `set startofline`
    - `inoremap jj <Esc>`
- Marks?
- Edge cases (grid with no white squares?)
- Highlight cross references between clues?
- Visual mode?
- Timer?
