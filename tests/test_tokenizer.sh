#!/bin/bash
set -e
set -o pipefail


! read -r -d '' TEXT << EOM
The store is just across from my house.
The store is close to my house.
The store is not open today.
The store is closed today.
The shop is open from today to tomorrow.\r\n
The store is just across from the store.
This is a store that sells food.
We went into a shop to get some food.
The store closes at 7.
That store sells food.\r\n
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
McDonalds Donald HEY ordinary TTx oOo aAA
John went to a store.
EOM

ENDOFLINES=$'The store is just across from my house.\r\nThe store is close to my house.\r\nThe store is closed today.\nThe store closes at 7.\r\n'

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

# lowercasing
echo "$TEXT" | python -m subtokenizer tokenize --lowercase | python -m subtokenizer detokenize --lowercase | diff - <( echo "$TEXT" )
echo "$TEXT" | python -m subtokenizer learn --lowercase -o bpe_l.file -s 70 -m 2
echo "$TEXT" | python -m subtokenizer tokenize --lowercase -s bpe_l.file | python -m subtokenizer detokenize --lowercase -s bpe_l.file | diff - <( echo "$TEXT" )

# reversed bpe
echo "$TEXT" | python -m subtokenizer learn --reversed_bpe -o bpe_r.file -s 70 -m 2
echo "$TEXT" | python -m subtokenizer tokenize --reversed_bpe -s bpe_r.file | python -m subtokenizer detokenize --reversed_bpe -s bpe_r.file | diff - <( echo "$TEXT" )

# test windows end of lines
echo "$ENDOFLINES" | python -m subtokenizer learn -o eof.file -s 70 -m 2
cat eof.file | awk '{if (match($0, /\r/)) {print NR, $0; exit 1}}'
