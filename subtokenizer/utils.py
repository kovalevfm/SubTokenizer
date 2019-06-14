# coding: utf-8

from __future__ import unicode_literals, division, absolute_import

import io
import six
import regex
import unicodedata
from threading import Thread
from collections import defaultdict
from multiprocessing import Process, Pipe

if six.PY2:
    from HTMLParser import HTMLParser
    HTML_PARSER = HTMLParser()
else:
    import html

NOSPACE = '˿'
ENCODED = '&'
SPACESYMBOL   = '·'
NOBREAK = '¬'
TAGSYMBOL = '@'

ESCAPE_CHARS = set("˿&·¬@#;0123456789")

SPECIALSYMBOLS = set([NOSPACE, ENCODED, SPACESYMBOL, NOBREAK, TAGSYMBOL])
ALLOWEDCONTROLS = set(['\n', ' ', '\t'])
SYMBOLRE = regex.compile(r"&#([0-9]+);")


def unescape(text):
    if six.PY2:
        return HTML_PARSER.unescape(text)
    else:
        return html.unescape(text)


def multiprocess(func, in_generator, processes=1):
    in_pipes = list(map(lambda x: Pipe(False), range(processes)))
    out_pipes = list(map(lambda x: Pipe(False), range(processes)))

    def writer():
        pipe_cnt = 0
        for obj in in_generator:
            in_pipes[pipe_cnt][1].send(obj)
            pipe_cnt += 1
            if pipe_cnt >= processes:
                pipe_cnt = 0
        for conn_recv, conn_send in in_pipes:
            conn_send.close()

    def proc_func(func, proc_num):
        for conn_recv, conn_send in in_pipes:
            conn_send.close()
        conn_recv = in_pipes[proc_num][0]
        conn_send = out_pipes[proc_num][1]
        while True:
            try:
                line = conn_recv.recv()
            except EOFError:
                break
            conn_send.send(func(line))
        conn_send.close()

    procs = list(map(lambda x: Process(target=proc_func, args=(func, x)), range(processes)))
    for i in range(processes):
        procs[i].start()
        out_pipes[i][1].close()
    write_proc = Thread(target=writer)
    write_proc.start()

    current_pipe = 0
    live_pipes = [True] * processes
    while True:
        if not any(live_pipes):
            break
        if live_pipes[current_pipe]:
            try:
                yield out_pipes[current_pipe][0].recv()
            except EOFError:
                live_pipes[current_pipe] = False
        current_pipe = current_pipe + 1
        if current_pipe >= processes:
            current_pipe = 0


if six.PY2:
    class _ReadableWrapper(object):
        def __init__(self, raw):
            self._raw = raw

        def readable(self):
            return True

        def writable(self):
            return False

        def seekable(self):
            return True

        def __getattr__(self, name):
            return getattr(self._raw, name)


def wrap_text_reader(stream, *args, **kwargs):
    # Note: order important here, as 'file' doesn't exist in Python 3
    if six.PY2 and isinstance(stream, file):
        stream = io.BufferedReader(_ReadableWrapper(stream))

    return io.TextIOWrapper(stream, *args, **kwargs)


def normalize_text(text):
    return unicodedata.normalize('NFKC', text)


def encode_symbol(ch):
    return r"&#%d;" % ord(ch)


def encode_control_symbol(ch):
    if ch in SPECIALSYMBOLS:
        return encode_symbol(ch)
    if ch in ALLOWEDCONTROLS:
        return ch
    if unicodedata.category(ch)[0] in set(['C', 'Z']):
        return encode_symbol(ch)
    return ch


def encode_controls(text):
    return "".join(encode_control_symbol(ch) for ch in text)


def encode_with_alphabet_symbol(ch, alphabet):
    if ch not in alphabet:
        return encode_symbol(ch)
    return ch


def encode_with_alphabet(text, alphabet):
    return "".join(encode_with_alphabet_symbol(ch, alphabet) for ch in text)


def alphabet_from_tokens(word_counts, min_count=0):
    symbolcount = defaultdict(int)
    for token, val in six.iteritems(word_counts):
        for ch in token:
            symbolcount[ch] += val
    alphabet = {ch for ch, val in six.iteritems(symbolcount) if val >= min_count}
    alphabet |= ESCAPE_CHARS
    return alphabet


def encode_tokens_with_alphabet(word_counts, alphabet):
    new_word_counts = defaultdict(int)
    for token, val in six.iteritems(word_counts):
        new_word_counts[encode_with_alphabet(token, alphabet)] += val
    return new_word_counts
