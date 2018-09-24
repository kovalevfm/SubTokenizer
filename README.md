# SubTokenizer
Subwords tokenizer based on google code from tensor2tensor

Standalone subwords tokenizer from https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/data_generators/text_encoder.py

Install:
```bash
 pip install git+https://github.com/kovalevfm/SubTokenizer.git
```

Usage:
```bash
cat text_file.txt | subtokenizer learn -o bpe.file -s 1000 -r reserved_tokens.txt
cat text_file.txt | subtokenizer tokenize -s bpe.file > tokenized_file.txt
```
Or:
```python
import itertools
from subtokenizer import ReTokenizer
from subtokenizer import Subwords, EOS

subdict = Subwords(subwords_filename)
tokens = itertools.chain.from_iterable(subdict.token_to_subtokens(token) for token in ReTokenizer.tokenize(line))
line = ReTokenizer.detokenize(subdict.subtokens_to_tokens(t for t in tokens if t != EOS))

```