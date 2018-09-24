# coding: utf-8
from __future__ import unicode_literals

import regex
from six import iteritems
#     ■ - unbreakeble space inside token
#     ￭ - no space joiner
#     ＠＠ - placeholder

class ReTokenizer(object):
    JOINER_SYMBOL = '￭'
    SPACE_SYMBOL = '■'
    LANGUAGES = ["Arabic","Armenian","Bengali","Bopomofo","Braille","Buhid",
                 "Canadian_Aboriginal","Cherokee","Cyrillic","Devanagari","Ethiopic","Georgian",
                 "Greek","Gujarati","Gurmukhi","Han","Hangul","Hanunoo","Hebrew","Hiragana",
                 "Inherited","Kannada","Katakana","Khmer","Lao","Latin","Limb","Malayalam",
                 "Mongolian","Myanmar","Ogham","Oriya","Runic","Sinhala","Syriac","Tagalog",
                 "Tagbanwa","TaiLe","Tamil","Thaana","Thai","Tibetan","Yi","N"]
    WORD = '(?P<WORD>' + '|'.join(r'[\p{{{0}}}][\p{{{0}}}\p{{M}}■]*'.format(lang) for lang in LANGUAGES) + ')'
    PLACEHOLDER = '(?P<PLACEHOLDER>＠＠[A-Za-z0-9]*)'
    SPACE = r'(?P<SPACE>[\p{Z}])'
    REST = r'(?P<REST>[^\p{Z}\p{L}\p{M}\p{N}＠]+|(?<!＠)＠(?!＠))'
    TOKENIZER_RE = regex.compile(r'(?V1p)' + '|'.join((WORD, PLACEHOLDER, SPACE, REST)))
    JOINER_RE = regex.compile(r'(?V1p)' + JOINER_SYMBOL)
    SPACE_RE = regex.compile(r'(?V1p)' + SPACE_SYMBOL)


    @classmethod
    def tokenize_with_types(cls, sentence):
        tokens = []
        token_types = []
        privous_token_type = 'SPACE'
        space_added = True
        for w_it in cls.TOKENIZER_RE.finditer(sentence):
            word = sentence[w_it.start():w_it.end()]
            token_type = next(k for k, v in iteritems(w_it.groupdict()) if v is not None)
            if token_type in ('WORD', 'PLACEHOLDER'):
                if privous_token_type in ('WORD', 'PLACEHOLDER'):
                    tokens.append(cls.JOINER_SYMBOL)
                    token_types.append('REST')
                tokens.append(word)
                token_types.append(token_type)
                space_added = False
            elif token_type  == 'REST':
                if privous_token_type == 'SPACE' and not space_added:
                    word = ''.join((cls.SPACE_SYMBOL, word))
                tokens.append(word)
                token_types.append(token_type)
                space_added = False
            elif token_type == 'SPACE':
                if privous_token_type == 'REST':
                    tokens[-1] = ''.join((tokens[-1], cls.SPACE_SYMBOL))
                    space_added = True
                if privous_token_type == 'SPACE':
                    tokens.append(cls.SPACE_SYMBOL)
                    space_added = True
            privous_token_type = token_type
        return tokens, token_types
    
    
    @classmethod
    def tokenize(cls, sentence):
        tokens, token_types = cls.tokenize_with_types(sentence)
        return tokens

    @classmethod
    def detokenize(cls, tokens):
        words = []
        privous_token_type = 'REST'
        for t in tokens:
            token_type = next(k for k, v in iteritems(cls.TOKENIZER_RE.match(t).groupdict()) if v is not None)
            if privous_token_type in ('WORD', 'PLACEHOLDER') and token_type in ('WORD', 'PLACEHOLDER'):
                words.append(' ')
            words.append(t)
            privous_token_type = token_type
        return cls.SPACE_RE.sub(' ', cls.JOINER_RE.sub('', ''.join(words)))

