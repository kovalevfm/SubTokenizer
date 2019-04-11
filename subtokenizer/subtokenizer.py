# coding: utf-8
from __future__ import unicode_literals, absolute_import

import io
from subtokenizer.utils import (encode_controls, encode_with_alphabet, unescape,
                                alphabet_from_tokens, encode_tokens_with_alphabet,
                                NOBREAK, ESCAPE_CHARS, normalize_text)
from subtokenizer.subwords import Subwords, RESERVED_TOKENS, EOS, PAD
from subtokenizer.tokenizer import ReTokenizer


def UntilEOS(generator):
    for item in generator:
        if item == EOS:
            break
        yield item

class SubTokenizer(object):

    def __init__(self, subtokens_list):
        self.alphabet = {c for token in subtokens_list for c in token}
        self.subwords = Subwords(subtokens_list)

    def encode_controls(self, text):
        return encode_controls(text)

    def decode(self, text):
        text = text.replace(NOBREAK, '')
        return unescape(text)

    def tokenize(self, text, encode_controls=True, numeric=False, add_eos=False):
        text = normalize_text(text)
        if encode_controls:
            text = self.encode_controls(text)
        words = ReTokenizer.tokenize(text)
        tokens = []
        for w in words:
            tokens.extend(self.subwords.token_to_subtokens(encode_with_alphabet(w, self.alphabet)))
        if add_eos:
            tokens.append(EOS)
        if numeric:
            tokens = self.subwords.subtokens_to_ids(tokens)
        return tokens

    def detokenize(self, tokens, decode=True, numeric=False):
        if numeric:
            tokens = self.subwords.ids_to_subtokens(tokens)
        text = ReTokenizer.detokenize(UntilEOS(tokens))
        if decode:
            text = self.decode(text)
        return text

    def save(self, filename):
        f = io.TextIOWrapper(io.FileIO(filename, "w"), encoding='utf-8')
        for subtoken_string in self.subwords.all_subtoken_strings:
            f.write(subtoken_string + "\n")
        f.close()

    @classmethod
    def load(cls, filename):
        f = io.TextIOWrapper(io.BufferedReader(io.FileIO(filename, "r")), encoding='utf-8')
        subtokens_list = []
        for subtoken in f:
            subtokens_list.append(subtoken.strip('\n'))
        return cls(subtokens_list)

    @classmethod
    def learn(cls, token_counts, size=8000, min_symbol_count=1, reserved_tokens=None):
        reserved_tokens = reserved_tokens or []
        reserved_tokens = RESERVED_TOKENS + reserved_tokens
        alphabet = alphabet_from_tokens(token_counts, min_symbol_count)
        alphabet |= {c for token in reserved_tokens for c in token}
        alphabet |= ESCAPE_CHARS
        token_counts = encode_tokens_with_alphabet(token_counts, alphabet)
        subwords = Subwords.build_to_target_size(size, token_counts, 1, 1e3, reserved_tokens, alphabet)
        return cls(subwords.all_subtoken_strings)
