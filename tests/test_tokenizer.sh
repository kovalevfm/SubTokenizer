#!/bin/bash
set -e
set -o pipefail


! read -r -d '' TEXT << EOM
The store is just across from my house.
The store is close to my house.
The store is not open today.
The store is closed today.
The shop is open from today to tomorrow.
The store is just across from the store.
This is a store that sells food.
We went into a shop to get some food.
The store closes at 7.
That store sells food.
That store sells a wide range of goods.
I have been to the store.
I like to shop at that store.
I bought some food at that shop.
I bought a hat at that shop.
The shop was closed.
I am waiting for the store to open.
I had my watch repaired at the store.
I picked out a hat at the store.
She bought a hat at the shop.
This shop is open from 7 to 7 o'clock.
I am going to the shop.
John went to a store.
EOM

echo "$TEXT" | python -m subtokenizer learn -o bpe.file -s 70 -m 2

# just tokenizer
echo "$TEXT" | python -m subtokenizer tokenize | python -m subtokenizer detokenize | diff - <( echo "$TEXT" )
# subwords
echo "$TEXT" | python -m subtokenizer tokenize -s bpe.file | python -m subtokenizer detokenize -s bpe.file | diff - <( echo "$TEXT" )
# eos
echo "$TEXT" | python -m subtokenizer tokenize -s bpe.file -e | python -m subtokenizer detokenize -s bpe.file | diff - <( echo "$TEXT" )
# numeric
echo "$TEXT" | python -m subtokenizer tokenize -s bpe.file -n | python -m subtokenizer detokenize -s bpe.file -n | diff - <( echo "$TEXT" )
# numeric + eos
echo "$TEXT" | python -m subtokenizer tokenize -s bpe.file -n -e | python -m subtokenizer detokenize -s bpe.file -n | diff - <( echo "$TEXT" )
# python2 multyprocessing
echo "$TEXT" | python -m subtokenizer tokenize -p 2 | python -m subtokenizer detokenize -p 2 | diff - <( echo "$TEXT" )
# python3 multyprocessing
#echo "$TEXT" | python3 -m subtokenizer tokenize -p 2 | python3 -m subtokenizer detokenize -p 2 | diff - <( echo "$TEXT" )