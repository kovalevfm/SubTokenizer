# coding: utf-8
from __future__ import unicode_literals, absolute_import

import regex
from six import iteritems
from subtokenizer.utils import NOSPACE, ENCODED, SPACESYMBOL, NOBREAK, TAGSYMBOL



class ReTokenizer(object):
    LANGUAGES = ["Arabic","Armenian","Bengali","Bopomofo","Braille","Buhid",
                 "Canadian_Aboriginal","Cherokee","Cyrillic","Devanagari","Ethiopic","Georgian",
                 "Greek","Gujarati","Gurmukhi","Han","Hangul","Hanunoo","Hebrew","Hiragana",
                 "Inherited","Kannada","Katakana","Khmer","Lao","Latin","Limb","Malayalam",
                 "Mongolian","Myanmar","Ogham","Oriya","Runic","Sinhala","Syriac","Tagalog",
                 "Tagbanwa","TaiLe","Tamil","Thaana","Thai","Tibetan","Yi","N"]
    WORD = '(?P<WORD>' + '|'.join(r'{0}?[\p{{{1}}}][\p{{{1}}}\p{{M}}]*{2}?'.format(NOBREAK, lang, SPACESYMBOL) for lang in LANGUAGES) + ')'
    ENCODED = '(?P<ENCODED>&#[0-9]+;)'
    TAG = '(?P<TAG>'+TAGSYMBOL+'[a-zA-Z0-9_]+'+SPACESYMBOL+'?)'
    TOKENIZER_RE = regex.compile(r'(?V1p)' + '|'.join((WORD, ENCODED, TAG)))
    REMOVE_SPACE_RE = regex.compile(r'(?V1p) ' + NOBREAK + '?' + NOSPACE)


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
    def tokenize(cls, text):
        words = []
        position = 0
        text = text.replace(' ', SPACESYMBOL)
        for w_it in cls.TOKENIZER_RE.finditer(text):
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
    def detokenize(cls, words):
        text = cls.REMOVE_SPACE_RE.sub('', ''.join(words).replace(SPACESYMBOL, ' '))
        return text


    @classmethod
    def encode_combined_word(cls, word):
        subwords = cls.tokenize(word)
        for i in range(1, len(subwords)):
            subwords[i] = NOBREAK + subwords[i]
        word = ''.join(subwords)
        word = cls.REMOVE_SPACE_RE.sub('', word.replace(SPACESYMBOL, ' '))
        return word
