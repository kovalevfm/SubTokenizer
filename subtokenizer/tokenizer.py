# coding: utf-8
from __future__ import unicode_literals, absolute_import

import regex
from six import iteritems
from subtokenizer.utils import NOSPACE, ENCODED, SPACESYMBOL, NOBREAK, TAGSYMBOL, ONEUPPER, ALLUPPER



class ReTokenizer(object):
    LANGUAGES = ["Arabic","Armenian","Bengali","Bopomofo","Braille","Buhid",
                 "Canadian_Aboriginal","Cherokee","Cyrillic","Devanagari","Ethiopic","Georgian",
                 "Greek","Gujarati","Gurmukhi","Han","Hangul","Hanunoo","Hebrew","Hiragana",
                 "Inherited","Kannada","Katakana","Khmer","Lao","Latin","Limb","Malayalam",
                 "Mongolian","Myanmar","Ogham","Oriya","Runic","Sinhala","Syriac","Tagalog",
                 "Tagbanwa","TaiLe","Tamil","Thaana","Thai","Tibetan","Yi","N"]
    WORD = '(?P<WORD>' + '|'.join(r'{0}?[\p{{{1}}}][\p{{{1}}}\p{{M}}]*{2}?'.format(NOBREAK, lang, SPACESYMBOL) for lang in LANGUAGES) + ')'
    ALL_ALPH = ''.join(r'\p{{{0}}}'.format(lang) for lang in LANGUAGES)
    WORD_NO_ALPH_SPLIT = r'(?P<WORD>{0}?[{1}][{1}\p{{M}}]*{2}?)'.format(NOBREAK,ALL_ALPH,  SPACESYMBOL)
    ENCODED = '(?P<ENCODED>&#[0-9]+;)'
    TAG = '(?P<TAG>'+TAGSYMBOL+'[a-zA-Z0-9_]+'+SPACESYMBOL+'?)'
    TOKENIZER_RE = regex.compile(r'(?V1p)' + '|'.join((WORD, ENCODED, TAG)))
    TOKENIZER_NO_ALPH_SPLIT = regex.compile(r'(?V1p)' + '|'.join((WORD_NO_ALPH_SPLIT, ENCODED, TAG)))
    REMOVE_SPACE_RE = regex.compile(r'(?V1p) ' + NOBREAK + '?' + NOSPACE)
    LOWER_RE = regex.compile(r'(?V1p)(?P<CAPITAL>\p{Lu}+[\p{L}--\p{Lu}])|(?P<UPPER>\p{Lu}+)')
    UPPER_RE = regex.compile(r'(?V1p)({0}\p{{L}})|({1}\p{{L}}+(?!p{{L}}))'.format(ONEUPPER, ALLUPPER))

    @staticmethod
    def _do_lower(t):
        val = t.group(0)
        if t.groupdict()['UPPER']:
            return ''.join((ONEUPPER if len(val) == 1 else ALLUPPER, val.lower()))
        if len(val) > 2:
            return ''.join((ALLUPPER, val[:-2].lower(), ONEUPPER, val[-2:].lower()))
        return ''.join((ONEUPPER, val.lower()))

    @staticmethod
    def _do_upper(t):
        return t.group(0)[1:].upper()

    @classmethod
    def _add_punctuation(cls, words, punctuation):
        if punctuation[0] == NOBREAK and words:
            words[-1] = words[-1] + punctuation
        else:
            if words and words[-1][-1] != SPACESYMBOL:
                words[-1] = words[-1] + SPACESYMBOL
                punctuation = NOSPACE + punctuation
            words.append(punctuation)
        return words
    
    @classmethod
    def tokenize(cls, text, split_by_alphabets=True, lowercase=False):
        words = []
        position = 0
        if lowercase:
            text = cls.LOWER_RE.sub(cls._do_lower, text)
        text = text.replace(' ', SPACESYMBOL)
        w_iter = cls.TOKENIZER_RE.finditer(text) if split_by_alphabets else cls.TOKENIZER_NO_ALPH_SPLIT.finditer(text)
        for w_it in w_iter:
            token_type = next(k for k, v in iteritems(w_it.groupdict()) if v is not None)
            if token_type == 'ENCODED':
                continue
            word = text[w_it.start():w_it.end()]
            if position < w_it.start():
                punctuation = text[position:w_it.start()]
                words = cls._add_punctuation(words, punctuation)
            if word[0] == NOBREAK and words:
                words[-1] = words[-1] + word
            else:
                words.append(word)
            position = w_it.end()
        if position != len(text):
            punctuation = text[position:len(text)]
            words = cls._add_punctuation(words, punctuation)
        elif words and words[-1][-1] != SPACESYMBOL:
            words[-1] = words[-1] + SPACESYMBOL
            words.append(NOSPACE)
        return words


    @classmethod
    def detokenize(cls, words, restore_case=False):
        text = cls.REMOVE_SPACE_RE.sub('', ''.join(words).replace(SPACESYMBOL, ' '))
        if (restore_case):
            text = cls.UPPER_RE.sub(cls._do_upper, text)
        return text


    @classmethod
    def encode_combined_word(cls, word):
        subwords = cls.tokenize(word)
        for i in range(1, len(subwords)):
            subwords[i] = NOBREAK + subwords[i]
        word = ''.join(subwords)
        word = cls.REMOVE_SPACE_RE.sub('', word.replace(SPACESYMBOL, ' '))
        return word
