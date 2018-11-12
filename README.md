# SubTokenizer
[![Build status](https://travis-ci.org/kovalevfm/SubTokenizer.svg?master)](https://travis-ci.org/kovalevfm)

Subwords tokenizer based on google code from tensor2tensor. It supports tags and combined tokens in addition to google tokenizer.
* Tags are tokens starting from `@`, they are not splited on parts.
* No break symbol `¬` `'\xac'` allows to join several words in one token.

Tokenizer does unicode normalization and controls characters escaping. It's also possible to encode rare symbols so they can be splited on parts by subwords algorithm.

Original google subwords tokenizer: https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/data_generators/text_encoder.py

By default before learning and tokenizing SubTokenizer encodes all control characters and `@` `¬` symbols. To use tags it's needed to run encoding first then add tags and after learn/tokenize with `encode_controls=Flase` or `--no_encode_controls` in command line mode.

Install:
```bash
 pip install subtokenizer
```

Usage:
```bash
cat text_file.txt | subtokenizer learn -o bpe.file -s 1000 -r reserved_tokens.txt
cat text_file.txt | subtokenizer tokenize -s bpe.file > tokenized_file.txt
cat tokenized_file.txt | subtokenizer detokenize -s bpe.file > text_file.txt
```
Or:
```python
from subtokenizer import SubTokenizer

tokenizer = SubTokenizer.learn(words_count)
tokenizer.save(subwords_filename)

tokenizer = SubTokenizer.load(subwords_filename)
tokens = tokenizer.tokenize(line)
line = tokenizer.detokenize(tokens)

```
