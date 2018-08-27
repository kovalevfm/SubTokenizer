# coding: utf-8

import regex
#     ■ - unbreakeble space inside token
#     ￭ - no space joiner
#     ＠＠ - placeholder

class ReTokenizer(object):
    JOINER_SYMBOL = u'￭'
    SPACE_SYMBOL = u'■'
    LANGUAGES = [u"Arabic",u"Armenian",u"Bengali",u"Bopomofo",u"Braille",u"Buhid",
                 u"Canadian_Aboriginal",u"Cherokee",u"Cyrillic",u"Devanagari",u"Ethiopic",u"Georgian",
                 u"Greek",u"Gujarati",u"Gurmukhi",u"Han",u"Hangul",u"Hanunoo",u"Hebrew",u"Hiragana",
                 u"Inherited",u"Kannada",u"Katakana",u"Khmer",u"Lao",u"Latin",u"Limbu",u"Malayalam",
                 u"Mongolian",u"Myanmar",u"Ogham",u"Oriya",u"Runic",u"Sinhala",u"Syriac",u"Tagalog",
                 u"Tagbanwa",u"TaiLe",u"Tamil",u"Telugu",u"Thaana",u"Thai",u"Tibetan",u"Yi",u"N"]
    WORD = u'(?P<WORD>' + u'|'.join(u'[\p{{{0}}}][\p{{{0}}}\p{{M}}■]*'.format(lang) for lang in LANGUAGES) + u')'
    PLACEHOLDER = ur'(?P<PLACEHOLDER>＠＠[A-Za-z0-9]*)'
    SPACE = ur'(?P<SPACE>[\p{Z}]+)'
    REST = ur'(?P<REST>[^\p{Z}\p{L}\p{M}\p{N}＠]+|(?<!＠)＠(?!＠))'
    TOKENIZER_RE = regex.compile(ur'(?V1p)' + u'|'.join((WORD, PLACEHOLDER, SPACE, REST)))
    JOINER_RE = regex.compile(ur'(?V1p)' + JOINER_SYMBOL)
    SPACE_RE = regex.compile(ur'(?V1p)' + SPACE_SYMBOL)


    @classmethod
    def tokenize_with_types(cls, sentence):
        tokens = []
        token_types = []
        privous_token_type = u'REST'
        for w_it in cls.TOKENIZER_RE.finditer(sentence):
            word = sentence[w_it.start():w_it.end()]
            token_type = next(k for k, v in w_it.groupdict().iteritems() if v is not None)
            if token_type in (u'WORD', u'PLACEHOLDER'):
                if privous_token_type in (u'WORD', u'PLACEHOLDER'):
                    tokens.append(cls.JOINER_SYMBOL)
                    token_types.append(u'REST')
                tokens.append(word)
                token_types.append(token_type)
            elif token_type  == u'REST':
                if privous_token_type == u'SPACE':
                    word = u''.join((cls.SPACE_SYMBOL, word))
                tokens.append(word)
                token_types.append(token_type)
            elif token_type == u'SPACE':
                if privous_token_type == u'REST' and tokens:
                    tokens[-1] = u''.join((tokens[-1], cls.SPACE_SYMBOL)) 
            privous_token_type = token_type
        return tokens, token_types
    
    
    @classmethod
    def tokenize(cls, sentence):
        tokens, token_types = cls.tokenize_with_types(sentence)
        return tokens

    @classmethod
    def detokenize(cls, tokens):
        words = []
        privous_token_type = u'REST'
        for t in tokens:
            token_type = next(k for k, v in cls.TOKENIZER_RE.match(t).groupdict().iteritems() if v is not None)
            if privous_token_type in (u'WORD', u'PLACEHOLDER') and token_type in (u'WORD', u'PLACEHOLDER'):
                words.append(u' ')
            words.append(t)
            privous_token_type = token_type
        return cls.SPACE_RE.sub(u' ', cls.JOINER_RE.sub(u'', u''.join(words)))

