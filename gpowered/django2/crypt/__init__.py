"""RSA module

Module for calculating large primes, and RSA encryption, decryption,
signing and verification. Includes generating public and private keys.
"""

__author__ = "Sybren Stuvel, Marloes de Boer and Ivo Tamboer"
__date__ = "2008-04-23"

# NOTE: Python's modulo can return negative numbers. We compensate for
# this behaviour using the abs() function

import math
import sys
import random   # For picking semi-random numbers
import types
from cPickle import dumps, loads
import base64
import zlib

RANDOM_DEV="/dev/urandom"
has_broken_randint = False

try:
    random.randint(1, 10000000000000000000000000L)
except:
    has_broken_randint = True
    print "This system's random.randint() can't handle large numbers"
    print "Random integers will all be read from %s" % RANDOM_DEV


def log(x, base = 10):
    return math.log(x) / math.log(base)

def gcd(p, q):
    """Returns the greatest common divisor of p and q


    >>> gcd(42, 6)
    6
    """
    if p<q: return gcd(q, p)
    if q == 0: return p
    return gcd(q, abs(p%q))

def bytes2int(bytes):
    """Converts a list of bytes or a string to an integer

    >>> (128*256 + 64)*256 + + 15
    8405007
    >>> l = [128, 64, 15]
    >>> bytes2int(l)
    8405007
    """

    if not (type(bytes) is types.ListType or type(bytes) is types.StringType):
        raise TypeError("You must pass a string or a list")

    # Convert byte stream to integer
    integer = 0
    for byte in bytes:
        integer *= 256
        if type(byte) is types.StringType: byte = ord(byte)
        integer += byte

    return integer

def int2bytes(number):
    """Converts a number to a string of bytes
    
    >>> bytes2int(int2bytes(123456789))
    123456789
    """

    if not (type(number) is types.LongType or type(number) is types.IntType):
        raise TypeError("You must pass a long or an int")

    string = ""

    while number > 0:
        string = "%s%s" % (chr(number & 0xFF), string)
        number /= 256
    
    return string

def fast_exponentiation(a, p, n):
    """Calculates r = a^p mod n
    """
    result = a % n
    remainders = []
    while p != 1:
        remainders.append(p & 1)
        p = p >> 1
    while remainders:
        rem = remainders.pop()
        result = ((a ** rem) * result ** 2) % n
    return result

def read_random_int(nbits):
    """Reads a random integer from RANDOM_DEV of approximately nbits
    bits rounded up to whole bytes"""

    nbytes = ceil(nbits/8)

    # Read 'nbits' bits of random data
    fd = open(RANDOM_DEV)
    randomdata = fd.read(nbytes)
    fd.close()

    if len(randomdata) != nbytes:
        raise Exception("Unable to read enough random bytes")

    return bytes2int(randomdata)

def ceil(x):
    """Returns int(math.ceil(x))"""

    return int(math.ceil(x))
    
def randint(minvalue, maxvalue):
    """Returns a random integer x with minvalue <= x <= maxvalue"""

    if not has_broken_randint:
        return random.randint(minvalue, maxvalue)

    # Safety - get a lot of random data even if the range is fairly
    # small
    min_nbits = 32

    # The range of the random numbers we need to generate
    range = maxvalue - minvalue

    # Which is this number of bytes
    rangebytes = ceil(log(range, 2) / 8)

    # Convert to bits, but make sure it's always at least min_nbits*2
    rangebits = max(rangebytes * 8, min_nbits * 2)
    
    # Take a random number of bits between min_nbits and rangebits
    nbits = random.randint(min_nbits, rangebits)
    
    return (read_random_int(nbits) % range) + minvalue

def fermat_little_theorem(p):
    """Returns 1 if p may be prime, and something else if p definitely
    is not prime"""

    a = randint(1, p-1)
    return fast_exponentiation(a, p-1, p)

def jacobi(a, b):
    """Calculates the value of the Jacobi symbol (a/b)
    """

    if a % b == 0:
        return 0
    result = 1
    while a > 1:
        if a & 1:
            if ((a-1)*(b-1) >> 2) & 1:
                result = -result
            b, a = a, b % a
        else:
            if ((b ** 2 - 1) >> 3) & 1:
                result = -result
            a = a >> 1
    return result

def jacobi_witness(x, n):
    """Returns False if n is an Euler pseudo-prime with base x, and
    True otherwise.
    """

    j = jacobi(x, n) % n
    f = fast_exponentiation(x, (n-1)/2, n)

    if j == f: return False
    return True

def randomized_primality_testing(n, k):
    """Calculates whether n is composite (which is always correct) or
    prime (which is incorrect with error probability 2**-k)

    Returns False if the number if composite, and True if it's
    probably prime.
    """

    q = 0.5     # Property of the jacobi_witness function

    # t = int(math.ceil(k / log(1/q, 2)))
    t = ceil(k / log(1/q, 2))
    for i in range(t+1):
        x = randint(1, n-1)
        if jacobi_witness(x, n): return False
    
    return True

def is_prime(number):
    """Returns True if the number is prime, and False otherwise.

    >>> is_prime(42)
    0
    >>> is_prime(41)
    1
    """

    """
    if not fermat_little_theorem(number) == 1:
        # Not prime, according to Fermat's little theorem
        return False
    """

    if randomized_primality_testing(number, 5):
        # Prime, according to Jacobi
        return True
    
    # Not prime
    return False

    
def getprime(nbits):
    """Returns a prime number of max. 'math.ceil(nbits/8)*8' bits. In
    other words: nbits is rounded up to whole bytes.

    >>> p = getprime(8)
    >>> is_prime(p-1)
    0
    >>> is_prime(p)
    1
    >>> is_prime(p+1)
    0
    """

    nbytes = int(math.ceil(nbits/8))

    while True:
        integer = read_random_int(nbits)

        # Make sure it's odd
        integer |= 1

        # Test for primeness
        if is_prime(integer): break

        # Retry if not prime

    return integer

def are_relatively_prime(a, b):
    """Returns True if a and b are relatively prime, and False if they
    are not.

    >>> are_relatively_prime(2, 3)
    1
    >>> are_relatively_prime(2, 4)
    0
    """

    d = gcd(a, b)
    return (d == 1)

def find_p_q(nbits):
    """Returns a tuple of two different primes of nbits bits"""

    p = getprime(nbits)
    while True:
        q = getprime(nbits)
        if not q == p: break
    
    return (p, q)

def extended_euclid_gcd(a, b):
    """Returns a tuple (d, i, j) such that d = gcd(a, b) = ia + jb
    """

    if b == 0:
        return (a, 1, 0)

    q = abs(a % b)
    r = long(a / b)
    (d, k, l) = extended_euclid_gcd(b, q)

    return (d, l, k - l*r)

# Main function: calculate encryption and decryption keys
def calculate_keys(p, q, nbits):
    """Calculates an encryption and a decryption key for p and q, and
    returns them as a tuple (e, d)"""

    n = p * q
    phi_n = (p-1) * (q-1)

    while True:
        # Make sure e has enough bits so we ensure "wrapping" through
        # modulo n
        e = getprime(max(8, nbits/2))
        if are_relatively_prime(e, n) and are_relatively_prime(e, phi_n): break

    (d, i, j) = extended_euclid_gcd(e, phi_n)

    if not d == 1:
        raise Exception("e (%d) and phi_n (%d) are not relatively prime" % (e, phi_n))

    if not (e * i) % phi_n == 1:
        raise Exception("e (%d) and i (%d) are not mult. inv. modulo phi_n (%d)" % (e, i, phi_n))

    return (e, i)


def gen_keys(nbits):
    """Generate RSA keys of nbits bits. Returns (p, q, e, d).
    """

    while True:
        (p, q) = find_p_q(nbits)
        (e, d) = calculate_keys(p, q, nbits)

        # For some reason, d is sometimes negative. We don't know how
        # to fix it (yet), so we keep trying until everything is shiny
        if d > 0: break

    return (p, q, e, d)

def gen_pubpriv_keys(nbits):
    """Generates public and private keys, and returns them as (pub,
    priv).

    The public key consists of a dict {e: ..., , n: ....). The private
    key consists of a dict {d: ...., p: ...., q: ....).
    """
    
    (p, q, e, d) = gen_keys(nbits)

    return ( {'e': e, 'n': p*q}, {'d': d, 'p': p, 'q': q} )

def encrypt_int(message, ekey, n):
    """Encrypts a message using encryption key 'ekey', working modulo
    n"""

    if type(message) is types.IntType:
        return encrypt_int(long(message), ekey, n)

    if not type(message) is types.LongType:
        raise TypeError("You must pass a long or an int")

    if math.floor(log(message, 2)) > math.floor(log(n, 2)):
        raise OverflowError("The message is too long")

    return fast_exponentiation(message, ekey, n)

def decrypt_int(cyphertext, dkey, n):
    """Decrypts a cypher text using the decryption key 'dkey', working
    modulo n"""

    return encrypt_int(cyphertext, dkey, n)

def sign_int(message, dkey, n):
    """Signs 'message' using key 'dkey', working modulo n"""

    return decrypt_int(message, dkey, n)

def verify_int(signed, ekey, n):
    """verifies 'signed' using key 'ekey', working modulo n"""

    return encrypt_int(signed, ekey, n)

def picklechops(chops):
    """Pickles and base64encodes it's argument chops"""

    value = zlib.compress(dumps(chops))
    encoded = base64.encodestring(value)
    return encoded.strip()

def unpicklechops(string):
    """base64decodes and unpickes it's argument string into chops"""

    return loads(zlib.decompress(base64.decodestring(string)))

def chopstring(message, key, n, funcref):
    """Splits 'message' into chops that are at most as long as n,
    converts these into integers, and calls funcref(integer, key, n)
    for each chop.

    Used by 'encrypt' and 'sign'.
    """

    msglen = len(message)
    mbits = msglen * 8
    nbits = int(math.floor(log(n, 2)))
    nbytes = nbits / 8
    blocks = msglen / nbytes

    if msglen % nbytes > 0:
        blocks += 1

    cypher = []
    
    for bindex in range(blocks):
        offset = bindex * nbytes
        block = message[offset:offset+nbytes]
        value = bytes2int(block)
        cypher.append(funcref(value, key, n))

    return picklechops(cypher)

def gluechops(chops, key, n, funcref):
    """Glues chops back together into a string.  calls
    funcref(integer, key, n) for each chop.

    Used by 'decrypt' and 'verify'.
    """
    message = ""

    chops = unpicklechops(chops)
    
    for cpart in chops:
        mpart = funcref(cpart, key, n)
        message += int2bytes(mpart)
    
    return message

def encrypt(message, key):
    """Encrypts a string 'message' with the public key 'key'"""
    
    return chopstring(message, key['e'], key['n'], encrypt_int)

def sign(message, key):
    """Signs a string 'message' with the private key 'key'"""
    
    return chopstring(message, key['d'], key['p']*key['q'], decrypt_int)

def decrypt(cypher, key):
    """Decrypts a cypher with the private key 'key'"""

    return gluechops(cypher, key['d'], key['p']*key['q'], decrypt_int)

def verify(cypher, key):
    """Verifies a cypher with the public key 'key'"""

    return gluechops(cypher, key['e'], key['n'], encrypt_int)

def makePubKey(k):
    temp = k.split('!')
    pubkey = {'e': long(temp[0]), 'n': long(temp[1])}
    return pubkey

def makePrivKey(k):
    temp = k.split('!')
    privkey = {'d': long(temp[0]), 'p': long(temp[1]), 'q': long(temp[2])}        
    return privkey 

def test():
    orrig = "hello there"
    opub, opriv = gen_pubpriv_keys(28)
    print opub
    print opriv

# Do doctest if we're not imported
if __name__ == "__main__":
    import doctest
    doctest.testmod()

__all__ = ["gen_pubpriv_keys", "encrypt", "decrypt", "sign", "verify"]

