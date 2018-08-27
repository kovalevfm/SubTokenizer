import re
import six
import collections
from itertools import chain

# Reserved tokens for things like padding and EOS symbols.
PAD = "<pad>"
EOS = "<EOS>"
RESERVED_TOKENS = [PAD, EOS]
NUM_RESERVED_TOKENS = len(RESERVED_TOKENS)
PAD_ID = RESERVED_TOKENS.index(PAD)  # Normally 0
EOS_ID = RESERVED_TOKENS.index(EOS)  # Normally 1

if six.PY2:
    RESERVED_TOKENS_BYTES = RESERVED_TOKENS
else:
    RESERVED_TOKENS_BYTES = [bytes(PAD, "ascii"), bytes(EOS, "ascii")]

# Regular expression for unescaping token strings.
# '\u' is converted to '_'
# '\\' is converted to '\'
# '\213;' is converted to unichr(213)
_UNESCAPE_REGEX = re.compile(r"\\u|\\\\|\\([0-9]+);")
_ESCAPE_CHARS = set(u"\\_u;0123456789")

# Unicode utility functions that work with Python 2 and 3
def native_to_unicode(s):
    return s if is_unicode(s) else to_unicode(s)


def unicode_to_native(s):
    if six.PY2:
        return s.encode("utf-8") if is_unicode(s) else s
    else:
        return s


def is_unicode(s):
    if six.PY2:
        if isinstance(s, unicode):
            return True
    else:
        if isinstance(s, str):
            return True
    return False


def to_unicode(s, ignore_errors=False):
    if is_unicode(s):
        return s
    error_mode = "ignore" if ignore_errors else "strict"
    return s.decode("utf-8", errors=error_mode)


def _escape_token(token, alphabet):
    """Escape away underscores and OOV characters and append '_'.

    This allows the token to be expressed as the concatenation of a list
    of subtokens from the vocabulary. The underscore acts as a sentinel
    which allows us to invertibly concatenate multiple such lists.

    Args:
        token: A unicode string to be escaped.
        alphabet: A set of all characters in the vocabulary's alphabet.

    Returns:
        escaped_token: An escaped unicode string.

    Raises:
        ValueError: If the provided token is not unicode.
    """
    if not isinstance(token, six.text_type):
        raise ValueError("Expected string type for token, got %s" % type(token))

    token = token.replace(u"\\", u"\\\\").replace(u"_", u"\\u")
    ret = [c if c in alphabet and c != u"\n" else r"\%d;" % ord(c) for c in token]
    return u"".join(ret) + "_"


def _unescape_token(escaped_token):
    """Inverse of _escape_token().

    Args:
        escaped_token: a unicode string

    Returns:
        token: a unicode string
      """

    def match(m):
        if m.group(1) is None:
            return u"_" if m.group(0) == u"\\u" else u"\\"

        try:
            return six.unichr(int(m.group(1)))
        except (ValueError, OverflowError) as _:
            return u"\u3013"  # Unicode for undefined character.

    trimmed = escaped_token[:-1] if escaped_token.endswith("_") else escaped_token
    return _UNESCAPE_REGEX.sub(match, trimmed)


class Subwords(object):
    def __init__(self, filename=None):
        """Initialize and read from a file, if provided.
        Args:
          filename: filename from which to read vocab. If None, do not load a
            vocab
        """
        self._alphabet = set()
        self.filename = filename
        self.cache_size = 2 ** 20
        self.cache = [(None, None)] * self.cache_size
        if filename is not None:
            self.load_from_file(filename)

    @property
    def vocab_size(self):
        """The subtoken vocabulary size."""
        return len(self.all_subtoken_strings)

    def init_alphabet_from_tokens(self, tokens):
        """Initialize alphabet from an iterable of token or subtoken strings."""
        # Include all characters from all tokens in the alphabet to guarantee that
        # any token can be encoded. Additionally, include all escaping characters.
        self._alphabet = {c for token in tokens for c in token}
        self._alphabet |= _ESCAPE_CHARS

    def init_subtokens_from_list(self, subtoken_strings, reserved_tokens=None):
        """Initialize token information from a list of subtoken strings.
    
        Args:
          subtoken_strings: a list of subtokens
          reserved_tokens: List of reserved tokens. We must have `reserved_tokens`
            as None or the empty list, or else the global variable `RESERVED_TOKENS`
            must be a prefix of `reserved_tokens`.
    
        Raises:
          ValueError: if reserved is not 0 or len(RESERVED_TOKENS). In this case, it
            is not clear what the space is being reserved for, or when it will be
            filled in.
        """
        if reserved_tokens is None:
              reserved_tokens = []

        if reserved_tokens:
              self.all_subtoken_strings = reserved_tokens + subtoken_strings
        else:
              self.all_subtoken_strings = subtoken_strings

        # we remember the maximum length of any subtoken to avoid having to
        # check arbitrarily long strings.
        self.max_subtoken_len = max([len(s) for s in subtoken_strings])
        self.subtoken_string_to_id = {
            s: i + len(reserved_tokens)
            for i, s in enumerate(subtoken_strings) if s
        }
        # reset cache.
        self.cache = [(None, None)] * self.cache_size

    def escaped_token_to_subtoken_strings(self, escaped_token):
        """Converts an escaped token string to a list of subtoken strings.

        Args:
          escaped_token: An escaped token as a unicode string.
        Returns:
          A list of subtokens as unicode strings.
        """
        # NOTE: This algorithm is greedy; it won't necessarily produce the "best"
        # list of subtokens.
        ret = []
        start = 0
        token_len = len(escaped_token)
        while start < token_len:
            for end in range(min(token_len, start + self.max_subtoken_len), start, -1):
                subtoken = escaped_token[start:end]
                if subtoken in self.subtoken_string_to_id:
                    ret.append(subtoken)
                    start = end
                    break

            else:  # Did not break
                # If there is no possible encoding of the escaped token then one of the
                # characters in the token is not in the alphabet. This should be
                # impossible and would be indicative of a bug.
                assert False, "Token substring not found in subtoken vocabulary."
    
        return ret

    def build_from_token_counts(self, token_counts, min_count, num_iterations=4,
                                reserved_tokens=None, max_subtoken_length=None):
        if reserved_tokens is None:
            reserved_tokens = RESERVED_TOKENS
        else:
          # There is not complete freedom in replacing RESERVED_TOKENS.
            for default, proposed in zip(RESERVED_TOKENS, reserved_tokens):
                if default != proposed:
                      raise ValueError("RESERVED_TOKENS must be a prefix of reserved_tokens.")
        # Initialize the alphabet. Note, this must include reserved tokens or it can
        # result in encoding failures.
        alphabet_tokens = chain(six.iterkeys(token_counts), [native_to_unicode(t) for t in reserved_tokens])
        self.init_alphabet_from_tokens(alphabet_tokens)
        # Bootstrap the initial list of subtokens with the characters from the
        # alphabet plus the escaping characters.
        self.init_subtokens_from_list(list(self._alphabet), reserved_tokens=reserved_tokens)
        # We build iteratively.  On each iteration, we segment all the words,
        # then count the resulting potential subtokens, keeping the ones
        # with high enough counts for our new vocabulary.
        if min_count < 1:
              min_count = 1
        for i in range(num_iterations):
            # Collect all substrings of the encoded token that break along current
            # subtoken boundaries.
            subtoken_counts = collections.defaultdict(int)
            for token, count in six.iteritems(token_counts):
                escaped_token = _escape_token(token, self._alphabet)
                subtokens = self.escaped_token_to_subtoken_strings(escaped_token)
                start = 0
                for subtoken in subtokens:
                    last_position = len(escaped_token) + 1
                    if max_subtoken_length is not None:
                        last_position = min(last_position, start + max_subtoken_length)
    
                    for end in range(start + 1, last_position):
                        new_subtoken = escaped_token[start:end]
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
                        if subtoken_string not in self._alphabet:
                            new_subtoken_strings.append((count, subtoken_string))
                        for l in range(1, lsub):
                            subtoken_counts[subtoken_string[:l]] -= count
    
            # Include the alphabet explicitly to guarantee all strings are encodable.
            new_subtoken_strings.extend((subtoken_counts.get(a, 0), a) for a in self._alphabet)
            new_subtoken_strings.sort(reverse=True)

            # Reinitialize to the candidate vocabulary.
            new_subtoken_strings = [subtoken for _, subtoken in new_subtoken_strings]
            if reserved_tokens:
                escaped_reserved_tokens = [_escape_token(native_to_unicode(t), self._alphabet) for t in reserved_tokens]
                new_subtoken_strings = escaped_reserved_tokens + new_subtoken_strings
            self.init_subtokens_from_list(new_subtoken_strings)


    def token_to_subtokens_ids(self, token):
        """Converts token to a list of subtoken ids.

        Args:
          token: a string.
        Returns:
          a list of integers in the range [0, vocab_size)
        """
        return list(self.subtoken_string_to_id[subtoken] for subtoken in self.token_to_subtokens(token))


    def token_to_subtokens(self, token):
        """Converts token to a list of subtoken ids.

        Args:
          token: a string.
        Returns:
          a list of tokens from vocablurary
        """
        cache_location = hash(token) % self.cache_size
        cache_key, cache_value = self.cache[cache_location]
        if cache_key == token:
            return cache_value
        ret = self.escaped_token_to_subtoken_strings(_escape_token(token, self._alphabet))
        self.cache[cache_location] = (token, ret)
        return ret


    def subtoken_ids_to_tokens(self, subtokens):
        """Converts a subtoken integer ID to a list of tokens."""
        ret = []
        for subtoken in subtokens:
            if 0 <= subtoken < self.vocab_size:
                ret.append(self.all_subtoken_strings[subtoken])
            else: ret.append(u"")
        return self.subtokens_to_tokens(ret)


    def subtokens_to_tokens(self, subtokens):
        """Converts a list of subtoken ids to a list of tokens.

        Args:
          subtokens: a list of integers in the range [0, vocab_size)
        Returns:
          a list of strings.
        """
        concatenated = "".join(subtokens)
        split = concatenated.split("_")
        ret = []
        for t in split:
            if t:
                unescaped = _unescape_token(t + "_")
                if unescaped:
                    ret.append(unescaped)
        return ret

    def load_from_file(self, filename):
        """Load from a file object.
        Args:
          f: File object to load vocabulary from
        """
        subtoken_strings = []
        with open(filename) as f:
            for line in f:
                s = line.strip()
                # Some vocab files wrap words in single quotes, but others don't
                if ((s.startswith("'") and s.endswith("'")) or (s.startswith("\"") and s.endswith("\""))):
                    s = s[1:-1]
                subtoken_strings.append(native_to_unicode(s))
            self.init_subtokens_from_list(subtoken_strings)
            self.init_alphabet_from_tokens(subtoken_strings)

    def store_to_file(self, filename, add_single_quotes=True):
        with open(filename, "w") as f:
            for subtoken_string in self.all_subtoken_strings:
                if add_single_quotes:
                    f.write("'" + unicode_to_native(subtoken_string) + "'\n")
                else:
                    f.write(unicode_to_native(subtoken_string) + "\n")

    @classmethod
    def build_to_target_size(cls,
                             target_size,
                             token_counts,
                             min_val,
                             max_val,
                             max_subtoken_length=None,
                             reserved_tokens=None,
                             num_iterations=4):
        """Builds a SubwordTextEncoder that has `vocab_size` near `target_size`.
        Uses simple recursive binary search to find a minimum token count that most
        closely matches the `target_size`.
        Args:
          target_size: Desired vocab_size to approximate.
          token_counts: A dictionary of token counts, mapping string to int.
          min_val: An integer; lower bound for the minimum token count.
          max_val: An integer; upper bound for the minimum token count.
          max_subtoken_length: Maximum length of a subtoken. If this is not set,
            then the runtime and memory use of creating the vocab is quadratic in
            the length of the longest token. If this is set, then it is instead
            O(max_subtoken_length * length of longest token).
          reserved_tokens: List of reserved tokens. The global variable
            `RESERVED_TOKENS` must be a prefix of `reserved_tokens`. If this
            argument is `None`, it will use `RESERVED_TOKENS`.
          num_iterations: An integer; how many iterations of refinement.
        Returns:
          A SubwordTextEncoder instance.
        Raises:
          ValueError: If `min_val` is greater than `max_val`.
        """
        if min_val > max_val:
            raise ValueError("Lower bound for the minimum token count "
                             "is greater than the upper bound.")
        if target_size < 1:
            raise ValueError("Target size must be positive.")
    
        if reserved_tokens is None:
            reserved_tokens = RESERVED_TOKENS

        def bisect(min_val, max_val):
            """Bisection to find the right size."""
            present_count = (max_val + min_val) // 2
            subtokenizer = cls()
            subtokenizer.build_from_token_counts(
                token_counts, present_count, num_iterations,
                max_subtoken_length=max_subtoken_length,
                reserved_tokens=reserved_tokens)

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
