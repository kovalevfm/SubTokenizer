# coding: utf-8

from __future__ import unicode_literals, division

import io
import sys
import codecs
import argparse
import itertools
from collections import defaultdict
from subtokenizer.subwords import Subwords, RESERVED_TOKENS
from subtokenizer.tokenizer import ReTokenizer



def learn(args):
    reserved_tokens = None
    if args.reserved:
        reserved_tokens = map(lambda x: x.strip("\n"), codecs.open(args.reserved, "r", "utf-8").readlines())
        reserved_tokens = list(token for token in reserved_tokens if token)
        reserved_tokens = RESERVED_TOKENS + reserved_tokens
    word_count = defaultdict(int)
    for l in sys.stdin:
        l = l.strip('\n')
        for token in ReTokenizer.tokenize(l):
            word_count[token] += 1
    subdict = Subwords.build_to_target_size(args.size, word_count, 1, 1e3, reserved_tokens=reserved_tokens)
    subdict.store_to_file(args.output)


def tokenize(args):
    subdict = None
    if args.subwords:
        subdict = Subwords(args.subwords)
    for l in sys.stdin:
        l = l.strip('\n')
        tokens = ReTokenizer.tokenize(l)
        if subdict:
            if args.numeric:
                tokens = itertools.chain.from_iterable(map(str, subdict.token_to_subtokens_ids(token)) for token in tokens)
            else:
                tokens = itertools.chain.from_iterable(subdict.token_to_subtokens(token) for token in tokens)
        sys.stdout.write(' '.join(tokens))
        sys.stdout.write('\n')


def detokenize(args):
    subdict = None
    if args.subwords:
        subdict = Subwords(args.subwords)
    for l in sys.stdin:
        l = l.strip('\n').split(' ')
        if subdict:
            if args.numeric:
                tokens = subdict.subtoken_ids_to_tokens(map(int, l))
            else:
                tokens = subdict.subtokens_to_tokens(l)
        else:
            tokens = l
        sys.stdout.write(ReTokenizer.detokenize(tokens))
        sys.stdout.write('\n')


def main():
    if sys.version_info < (3, 0):
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin)
    else:
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True, line_buffering=True)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='there are two modes: 1) learn 2) tokenize 3) detokenize', dest="mode")
    parser_learn = subparsers.add_parser('learn', help='a help')
    parser_learn.add_argument('-r', '--reserved',  type=str, help="file with reserved tokens")
    parser_learn.add_argument('-o', '--output', required=True,  type=str, help="subwords dictionary")
    parser_learn.add_argument('-s', '--size', default=30000,  type=int, help="number of subtokens")
    parser_tokenize = subparsers.add_parser('tokenize', help='a help')
    parser_tokenize.add_argument('-s', '--subwords',  default=None, type=str, help="subwords dictionary")
    parser_tokenize.add_argument('-n', '--numeric',  action='store_true', help="numeric output")
    parser_tokenize = subparsers.add_parser('detokenize', help='a help')
    parser_tokenize.add_argument('-s', '--subwords',  default=None, type=str, help="subwords dictionary")
    parser_tokenize.add_argument('-n', '--numeric',  action='store_true', help="numeric output")
    args = parser.parse_args()
    if args.mode == 'learn':
        learn(args)
    elif args.mode == 'tokenize':
        tokenize(args)
    elif args.mode == 'detokenize':
        detokenize(args)
    else:
        print "unknown mode"
    # print "hello"
    # print args
    # for l in sys.stdin:
    #     print ReTokenizer.detokenize(ReTokenizer.tokenize(l.decode('utf8'))).encode('utf8')