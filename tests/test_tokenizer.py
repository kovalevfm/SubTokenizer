# coding: utf-8
from __future__ import unicode_literals, division, absolute_import

from builtins import str
from collections import defaultdict
from subtokenizer.subtokenizer import SubTokenizer
from subtokenizer.subwords import PAD_ID
from subtokenizer.tokenizer import ReTokenizer
from subtokenizer.utils import TAGSYMBOL

TEXT = ('The store is just across from my house.\r\n'
            'The store is close to my house.\n'
            'The store is not open today.\n'
            'The store is closed today.\n'
            'The shop is open from today to tomorrow.\n'
            'The store is just across from the store.\n'
            'This is a store that sells food.\n'
            'We went into a shop to get some food.\n'
            'The store closes at 7.\n'
            'That store sells food.\n'
            'That store sells a wide range of goods.\r\n'
            'I have been to the store.\n'
            'I like to shop at that store.\n'
            'I bought some food at that shop.\n'
            'I bought a hat at that shop.\n'
            'The shop was closed.\n'
            'I am waiting for the store to open.\n'
            'I had my watch repaired at the store.\n'
            'I picked out a hat at the store.\n'
            'She bought a hat at the shop.\n'
            "This shop is open from 7 to 7 o'clock.\n"
            'I am going to the shop.\n' + TAGSYMBOL + 'name went to a store.')

def test_tokenizer():
    s = 'The store is just across from my house and McDonalds. Some rare symbols: ¦~. Email abc@site.com, Hi Alex!'
    tokens = ReTokenizer.tokenize(s)
    assert s == ReTokenizer.detokenize(tokens)
    # lowercasing
    tokens = ReTokenizer.tokenize(s, lowercase=True)
    assert s == ReTokenizer.detokenize(tokens, restore_case=True)
    # Split by alphabet
    s = "щиążе сиę рóщниеż з дещалуацйą мациерзыńстща"
    tokens = ReTokenizer.tokenize(s, split_by_alphabets=False)
    assert len(tokens) == 7
    assert s == ReTokenizer.detokenize(tokens)


def test_subtokenizer():
    words_count = defaultdict(int)
    for l in TEXT.splitlines():
        res = ReTokenizer.tokenize(l.strip('\n'))
        for r in res:
            words_count[r] += 1

    st_test = SubTokenizer.learn(words_count, min_symbol_count=2, size=70, reserved_tokens=[TAGSYMBOL + 'name'])
    assert TAGSYMBOL + 'name' in st_test.subwords.subtoken_string_to_id

    # Detokenization
    s = 'Some rare symbols: ¦~. Email house@store.com'
    tokens = st_test.tokenize(s)
    assert not TAGSYMBOL + 'store' in tokens
    assert s == st_test.detokenize(tokens)

    # Tags
    s = TAGSYMBOL + 'name is just across from store.'
    tokens = st_test.tokenize(s, encode_controls=False)
    assert TAGSYMBOL + 'name' in tokens

    # EOS
    s = 'Some rare symbols: ¦~. Email house@store.com'
    tokens = st_test.tokenize(s, add_eos=True)
    assert not TAGSYMBOL + 'store' in tokens
    assert s == st_test.detokenize(tokens)

    # lowercase
    words_count = defaultdict(int)
    for l in TEXT.splitlines():
        res = ReTokenizer.tokenize(l.strip('\n'), lowercase=True)
        for r in res:
            words_count[r] += 1
    s = 'The store is just across from my house and McDonalds. Some rare symbols: ¦~. Email abc@site.com, Hi Alex!'
    st_test = SubTokenizer.learn(words_count, min_symbol_count=2, size=70, reserved_tokens=[TAGSYMBOL + 'name'])
    tokens = st_test.tokenize(s, lowercase=True)
    assert s == st_test.detokenize(tokens, restore_case=True)


def test_numeric():
    words_count = defaultdict(int)
    for l in TEXT.splitlines():
        res = ReTokenizer.tokenize(l.strip('\n'))
        for r in res:
            words_count[r] += 1

    st_test = SubTokenizer.learn(words_count, min_symbol_count=2, size=70, reserved_tokens=[TAGSYMBOL + 'name'])

    # Detokenization
    s = 'Some rare symbols: ¦~. Email house@store.com'
    tokens = st_test.tokenize(s, numeric=True)
    assert all(map(lambda x: isinstance(x, int), tokens))
    assert s == st_test.detokenize(tokens, numeric=True)

    # EOS
    s = 'Some rare symbols: ¦~. Email house@store.com'
    tokens = st_test.tokenize(s, numeric=True, add_eos=True)
    tokens.append(PAD_ID)
    assert all(map(lambda x: isinstance(x, int), tokens))
    assert s == st_test.detokenize(tokens, numeric=True)

    # Generator
    s = 'Some rare symbols: ¦~. Email house@store.com'
    tokens = st_test.tokenize(s)
    assert not TAGSYMBOL + 'store' in tokens
    assert s == st_test.detokenize(tokens.__iter__())
