from Core.text_processing import preprocess_text, word_window, highlight_indices


def test_preprocess_replaces_newlines_with_spaces():
    assert preprocess_text('a\nb\nc') == 'a b c'


def test_preprocess_replaces_urls_with_placeholder():
    out = preprocess_text('see http://example.com/page now')
    assert 'http' not in out
    assert '[URL]' in out


def test_preprocess_runs_newline_then_url_substitution():
    out = preprocess_text('line1\nhttp://e.com\nline2')
    assert '\n' not in out
    assert '[URL]' in out
    assert out.startswith('line1 ')
    assert out.endswith(' line2')


def test_word_window_basic_slices():
    text = 'the quick brown fox'
    spoken, current, next_ = word_window(text, 4, 5)  # 'quick'
    assert spoken == 'the '
    assert current == 'quick'
    assert next_ == ' brown fox'


def test_word_window_clamps_left_at_zero():
    spoken, current, next_ = word_window('hello world', 0, 5)
    assert spoken == ''
    assert current == 'hello'


def test_word_window_respects_read_trail():
    spoken, current, next_ = word_window('abcdefghij', 5, 1, read_trail=2)
    assert spoken == 'de'
    assert current == 'f'
    assert next_ == 'gh'


def test_highlight_indices_single_line_format():
    assert highlight_indices(4, 5) == ('1.4', '1.9')
