# coding: utf-8

from __future__ import unicode_literals, division

import io
import sys
import codecs
import argparse
import itertools
from collections import defaultdict
from multiprocessing import Process, Pipe
from threading import Thread
from subtokenizer.subwords import Subwords, RESERVED_TOKENS, EOS_ID, EOS
from subtokenizer.tokenizer import ReTokenizer



def multiprocess(func, in_generator, processes=1):
    in_pipes = map(lambda x: Pipe(False), range(processes))
    out_pipes = map(lambda x: Pipe(False), range(processes))

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

    procs = map(lambda x: Process(target=proc_func, args=(func, x)), range(processes))
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


def learn(args):
    reserved_tokens = None
    if args.reserved:
        reserved_tokens = map(lambda x: x.strip("\n"), codecs.open(args.reserved, "r", "utf-8").readlines())
        reserved_tokens = list(token for token in reserved_tokens if token)
        reserved_tokens = RESERVED_TOKENS + reserved_tokens
    word_count = defaultdict(int)
    if args.processes == 1:
        for l in sys.stdin:
            l = ReTokenizer.tokenize(l.strip('\n'))
            for token in l:
                word_count[token] += 1
    else:
        for l in multiprocess(lambda x: ReTokenizer.tokenize(x.strip('\n')), sys.stdin, processes=args.processes):
            for token in l:
                word_count[token] += 1
    subdict = Subwords.build_to_target_size(args.size, word_count, 1, 1e3, reserved_tokens=reserved_tokens)
    subdict.store_to_file(args.output)


def tokenize(args):
    subdict = None
    if args.subwords:
        subdict = Subwords(args.subwords)

    def proc_func(l):
        l = l.strip('\n')
        tokens = ReTokenizer.tokenize(l)
        if subdict:
            if args.numeric:
                tokens = itertools.chain.from_iterable(map(str, subdict.token_to_subtokens_ids(token)) for token in tokens)
            else:
                tokens = itertools.chain.from_iterable(subdict.token_to_subtokens(token) for token in tokens)
        tokens = list(tokens)
        if args.add_end:
            tokens += [str(EOS_ID) if args.numeric else EOS]
        return tokens

    if args.processes == 1:
        for l in sys.stdin:
            tokens = proc_func(l)
            sys.stdout.write(' '.join(tokens))
            sys.stdout.write('\n')
    else:
        for tokens in multiprocess(proc_func, sys.stdin, processes=args.processes):
            sys.stdout.write(' '.join(tokens))
            sys.stdout.write('\n')


def detokenize(args):
    subdict = None
    if args.subwords:
        subdict = Subwords(args.subwords)

    def proc_func(l):
        l = l.strip('\n').split(' ')
        if subdict:
            if args.numeric:
                tokens = subdict.subtoken_ids_to_tokens(int(t) for t in l if t != str(EOS_ID))
            else:
                tokens = subdict.subtokens_to_tokens(t for t in l if t != EOS)
        else:
            tokens = l
        return ReTokenizer.detokenize(tokens)

    if args.processes == 1:
        for l in sys.stdin:
            line = proc_func(l)
            sys.stdout.write(line)
            sys.stdout.write('\n')
    else:
        for line in multiprocess(proc_func, sys.stdin, processes=args.processes):
            sys.stdout.write(line)
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
    parser_learn.add_argument('-p', '--processes', default=1,  type=int, help="number of tokenizer processes")
    parser_tokenize = subparsers.add_parser('tokenize', help='a help')
    parser_tokenize.add_argument('-s', '--subwords',  default=None, type=str, help="subwords dictionary")
    parser_tokenize.add_argument('-n', '--numeric',  action='store_true', help="numeric output")
    parser_tokenize.add_argument('-p', '--processes', default=1,  type=int, help="number of tokenizer processes") 
    parser_tokenize.add_argument('-e', '--add_end', action='store_true', help="add end of line")
    parser_detokenize = subparsers.add_parser('detokenize', help='a help')
    parser_detokenize.add_argument('-s', '--subwords',  default=None, type=str, help="subwords dictionary")
    parser_detokenize.add_argument('-n', '--numeric',  action='store_true', help="numeric output")
    parser_detokenize.add_argument('-p', '--processes', default=1,  type=int, help="number of tokenizer processes")
    args = parser.parse_args()
    if args.mode == 'learn':
        learn(args)
    elif args.mode == 'tokenize':
        tokenize(args)
    elif args.mode == 'detokenize':
        detokenize(args)
    else:
        print('unknown mode')
