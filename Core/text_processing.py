import re

URL_PATTERN = re.compile(r'http\S+')


def preprocess_text(text):
    """Normalize text for single-line speaking.

    Order matches the original speak() pipeline: newlines are replaced with
    spaces first, then URLs are collapsed to ``[URL]``. The text is treated as a
    single line so that the ``"1.{offset}"`` highlight indices stay valid.
    """
    text = text.replace('\n', ' ')
    text = URL_PATTERN.sub(' [URL] ', text)
    return text


def word_window(spoken_text, location, length, read_trail=100):
    """Return the ``(spoken, current, next_)`` slices around the current word.

    ``spoken`` is up to ``read_trail`` chars before ``location`` (clamped at 0),
    ``current`` is the word being spoken, and ``next_`` is up to ``read_trail``
    chars after it.
    """
    left_index = location - read_trail
    if left_index < 0:
        left_index = 0
    spoken = spoken_text[left_index:location]
    current = spoken_text[location:location + length]
    next_ = spoken_text[location + length:location + length + read_trail]
    return spoken, current, next_


def highlight_indices(location, length):
    """Single-line tkinter Text indices for the current word."""
    return "1.{}".format(location), "1.{}".format(location + length)
