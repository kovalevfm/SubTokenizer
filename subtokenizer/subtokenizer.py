# coding: utf-8
from __future__ import unicode_literals, absolute_import

import io
import six
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

    def __init__(self, subtokens_list, numeric=False, split_by_alphabets=True, lowercase=False, reversed_bpe=False):
        self.alphabet = {c for token in subtokens_list for c in token}
        self.subwords = Subwords(subtokens_list)
        self.numeric = numeric
        self.split_by_alphabets = split_by_alphabets
        self.lowercase = lowercase
        self.reversed_bpe = reversed_bpe

    def encode_controls(self, text):
        return encode_controls(text)

    def decode(self, text):
        text = text.replace(NOBREAK, '')
        return unescape(text)

    def tokenize(self, text, encode_controls=True, numeric=None, add_eos=False, split_by_alphabets=None, lowercase=None):
        numeric = numeric if numeric is not None else self.numeric
        split_by_alphabets = split_by_alphabets if split_by_alphabets is not None else self.split_by_alphabets
        lowercase = lowercase if lowercase is not None else self.lowercase

        text = normalize_text(text)
        if encode_controls:
            text = self.encode_controls(text)
        words = ReTokenizer.tokenize(text, split_by_alphabets=split_by_alphabets, lowercase=lowercase)
        tokens = []
        for w in words:
            if self.reversed_bpe:
                subtokens = self.subwords.token_to_subtokens(encode_with_alphabet(w, self.alphabet)[::-1])
                for subtoken in subtokens[::-1]:
                    tokens.append(subtoken[::-1])
            else:
                tokens.extend(self.subwords.token_to_subtokens(encode_with_alphabet(w, self.alphabet)))
        if add_eos:
            tokens.append(EOS)
        if numeric:
            tokens = self.subwords.subtokens_to_ids(tokens)
        return tokens

    def detokenize(self, tokens, decode=True, numeric=None, restore_case=None):
        numeric = numeric if numeric is not None else self.numeric
        restore_case = restore_case if restore_case is not None else self.lowercase

        if numeric:
            tokens = self.subwords.ids_to_subtokens(tokens)
        text = ReTokenizer.detokenize(UntilEOS(tokens), restore_case=restore_case)
        if decode:
            text = self.decode(text)
        return text

    def save(self, filename):
        f = io.TextIOWrapper(io.FileIO(filename, "w"), encoding='utf-8')
        for subtoken_string in self.subwords.all_subtoken_strings:
            if self.reversed_bpe:
                f.write(subtoken_string[::-1] + "\n")
            else:
                f.write(subtoken_string + "\n")
        f.close()

    @classmethod
    def load(cls, filename, numeric=False, split_by_alphabets=True, lowercase=False, reversed_bpe=False):
        f = io.TextIOWrapper(io.BufferedReader(io.FileIO(filename, "r")), encoding='utf-8')
        subtokens_list = []
        for subtoken in f:
            if reversed_bpe:
                subtokens_list.append(subtoken.strip('\n')[::-1])
            else:
                subtokens_list.append(subtoken.strip('\n'))
        return cls(subtokens_list, numeric=numeric, split_by_alphabets=split_by_alphabets, lowercase=lowercase, reversed_bpe=reversed_bpe)

    @classmethod
    def learn(cls, token_counts, size=8000, min_symbol_count=1, reserved_tokens=None, reversed_bpe=False):
        reserved_tokens = reserved_tokens or []
        reserved_tokens = RESERVED_TOKENS + reserved_tokens
        alphabet = alphabet_from_tokens(token_counts, min_symbol_count)
        alphabet |= {c for token in reserved_tokens for c in token}
        alphabet |= ESCAPE_CHARS
        token_counts = encode_tokens_with_alphabet(token_counts, alphabet)
        if (reversed_bpe):
            token_counts = dict(map((lambda x: (x[0][::-1], x[1])), six.iteritems(token_counts)))
            reserved_tokens = list(map((lambda x: x[::-1]), reserved_tokens))
        # Upper bound heuristic
        counts = sorted(token_counts.values())
        upper_bound = max(counts[int(len(counts) - size * 0.01)], 1000)
        subwords = Subwords.build_to_target_size(size, token_counts, 1, upper_bound, reserved_tokens, alphabet)
        return cls(subwords.all_subtoken_strings, reversed_bpe=reversed_bpe)
