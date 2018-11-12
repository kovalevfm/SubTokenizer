# coding: utf-8
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import re
import six
import collections
from builtins import str
from itertools import chain

# Reserved tokens for things like padding and EOS symbols.
PAD = "<pad>"
EOS = "<EOS>"
RESERVED_TOKENS = [PAD, EOS]
NUM_RESERVED_TOKENS = len(RESERVED_TOKENS)
PAD_ID = RESERVED_TOKENS.index(PAD)  # Normally 0
EOS_ID = RESERVED_TOKENS.index(EOS)  # Normally 1



class Subwords(object):
    def __init__(self, subtokens_list):
        self.all_subtoken_strings = subtokens_list
        self.max_subtoken_len = max([len(s) for s in subtokens_list])
        self.cache_size = 2 ** 20
        self.cache = [(None, None)] * self.cache_size
        self.subtoken_string_to_id = {s: i for i, s in enumerate(subtokens_list) if s}

    @property
    def vocab_size(self):
        """The subtoken vocabulary size."""
        return len(self.all_subtoken_strings)

    def token_to_subtokens(self, token):
        """Converts an token string to a list of subtoken strings.
        Args:
            token: An token as a unicode string.
        Returns:
            A list of subtokens as unicode strings.
        """
    # NOTE: This algorithm is greedy; it won't necessarily produce the "best"
    # list of subtokens.
        cache_location = hash(token) % self.cache_size
        cache_key, cache_value = self.cache[cache_location]
        if cache_key == token:
            return cache_value
        start = 0
        ret = []
        token_len = len(token)
        while start < token_len:
            for end in range(min(token_len, start + self.max_subtoken_len), start, -1):
                subtoken = token[start:end]
                if subtoken in self.subtoken_string_to_id:
                    ret.append(subtoken)
                    start = end
                    break
            else:  # Did not break, impossible and would be indicative of a bug.
                assert False, "Token substring not found in subtoken vocabulary."
        self.cache[cache_location] = (token, ret)
        return ret

    def subtokens_to_ids(self, subtokens):
        return list(self.subtoken_string_to_id[subtoken] for subtoken in subtokens)

    def ids_to_subtokens(self, subtokens):
        return list(self.all_subtoken_strings[subtoken] for subtoken in subtokens)

    @classmethod
    def build_from_token_counts(cls, token_counts, min_count, reserved_tokens, alphabet,
                                num_iterations=4,  subtoken_length_limit=None):
        """Train a Subwords based on a dictionary of word counts.
        Args:
          token_counts: a dictionary of Unicode strings to int.
          min_count: an integer - discard subtokens with lower counts.
          reserved_tokens: List of reserved tokens. The global variable
            `RESERVED_TOKENS` must be a prefix of `reserved_tokens`.
          alphabet: allowed unicode symbols, all other symbols have to be encoded
          num_iterations: an integer.  how many iterations of refinement.
          subtoken_length_limit: Maximum length of a subtoken. If this is not set,
            then the runtime and memory use of creating the vocab is quadratic in
            the length of the longest token. If this is set, then it is instead
            O(subtoken_length_limit * length of longest token).
        Returns:
          A Subword instance.
        """
        subwords_instance = cls(reserved_tokens + list(alphabet))
        # We build iteratively.  On each iteration, we segment all the words,
        # then count the resulting potential subtokens, keeping the ones
        # with high enough counts for our new vocabulary.
        min_count = max(1, min_count)
        for i in range(num_iterations):
            # Collect all substrings of the encoded token that break along current
            # subtoken boundaries.
            subtoken_counts = collections.defaultdict(int)
            for token, count in six.iteritems(token_counts):
                subtokens = subwords_instance.token_to_subtokens(token)
                start = 0
                for subtoken in subtokens:
                    last_position = len(token) + 1
                    if subtoken_length_limit is not None:
                        last_position = min(last_position, start + subtoken_length_limit)
                    for end in range(start + 1, last_position):
                        new_subtoken = token[start:end]
                        subtoken_counts[new_subtoken] += count
                    start += len(subtoken)

            # Array of sets of candidate subtoken strings, by length.
            len_to_subtoken_strings = []
            for subtoken_string, count in six.iteritems(subtoken_counts):
                lsub = len(subtoken_string)
                if count >= min_count:
                    while len(len_to_subtoken_strings) <= lsub:
                        len_to_subtoken_strings.append(set())
                    len_to_subtoken_strings[lsub].add(subtoken_string)
            # Consider the candidates longest to shortest, so that if we accept
            # a longer subtoken string, we can decrement the counts of its prefixes.
            new_subtoken_strings = []
            for lsub in range(len(len_to_subtoken_strings) - 1, 0, -1):
                subtoken_strings = len_to_subtoken_strings[lsub]
                for subtoken_string in subtoken_strings:
                    count = subtoken_counts[subtoken_string]
                    if count >= min_count:
                        # Exclude alphabet tokens here, as they must be included later,
                        # explicitly, regardless of count.
                        if subtoken_string not in alphabet:
                            new_subtoken_strings.append((count, subtoken_string))
                        for l in range(1, lsub):
                            subtoken_counts[subtoken_string[:l]] -= count
    
            # Include the alphabet explicitly to guarantee all strings are encodable.
            new_subtoken_strings.extend((subtoken_counts.get(a, 0), a) for a in alphabet)
            new_subtoken_strings.sort(reverse=True)
            # Reinitialize to the candidate vocabulary.
            new_subtoken_strings = [subtoken for _, subtoken in new_subtoken_strings]
            subwords_instance = cls(reserved_tokens + new_subtoken_strings)
        return subwords_instance

    @classmethod
    def build_to_target_size(cls, target_size, token_counts, min_val, max_val,
                             reserved_tokens, alphabet, subtoken_length_limit=None, num_iterations=4):
        """Builds a Subwords that has `vocab_size` near `target_size`.
        Uses simple recursive binary search to find a minimum token count that most
        closely matches the `target_size`.
        Args:
          target_size: Desired vocab_size to approximate.
          token_counts: A dictionary of token counts, mapping string to int.
          min_val: An integer; lower bound for the minimum token count.
          max_val: An integer; upper bound for the minimum token count.
          reserved_tokens: List of reserved tokens. The global variable
            `RESERVED_TOKENS` must be a prefix of `reserved_tokens`.
          alphabet: allowed unicode symbols, all other symbols have to be encoded
          subtoken_length_limit: Maximum length of a subtoken. If this is not set,
            then the runtime and memory use of creating the vocab is quadratic in
            the length of the longest token. If this is set, then it is instead
            O(subtoken_length_limit * length of longest token).
          num_iterations: An integer; how many iterations of refinement.
        Returns:
          A Subword instance.
        Raises:
          ValueError: If `min_val` is greater than `max_val`.
        """
        if min_val > max_val:
            raise ValueError("Lower bound for the minimum token count "
                             "is greater than the upper bound.")
        if target_size < 1:
            raise ValueError("Target size must be positive.")

        def bisect(min_val, max_val):
            """Bisection to find the right size."""
            present_count = (max_val + min_val) // 2
            subtokenizer = cls.build_from_token_counts(
                token_counts, present_count, reserved_tokens, alphabet,
                num_iterations, subtoken_length_limit=subtoken_length_limit)

            # Being within 1% of the target size is ok.
            is_ok = abs(subtokenizer.vocab_size - target_size) * 100 < target_size
            # If min_val == max_val, we can't do any better than this.
            if is_ok or min_val >= max_val or present_count < 2:
                return subtokenizer

            if subtokenizer.vocab_size > target_size:
                other_subtokenizer = bisect(present_count + 1, max_val)
            else:
                other_subtokenizer = bisect(min_val, present_count - 1)

            if other_subtokenizer is None:
                return subtokenizer

            if (abs(other_subtokenizer.vocab_size - target_size) <
                abs(subtokenizer.vocab_size - target_size)):
                return other_subtokenizer
            return subtokenizer

        return bisect(min_val, max_val)

