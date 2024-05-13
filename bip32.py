import hashlib
import hmac
import os
from collections import namedtuple

import base58
from ecdsa import SigningKey, SECP256k1

"""
https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
"""


class ExtendedKey(
    namedtuple(
        "ExtendedKey",
        [
            "version",
            "depth",
            "finger",
            "child_number",
            "chain_code",
            "key_data",
        ],
    )
):
    def __str__(self):
        # return super().__str__()
        key_ = (
            self.version
            + self.depth
            + self.finger
            + self.child_number
            + self.chain_code
            + self.key_data
        )
        return base58.b58encode_check(key_, alphabet=base58.BITCOIN_ALPHABET).decode()


VERSIONS = {
    "mainnet": {
        "public": bytes.fromhex("0488B21E"),
        "private": bytes.fromhex("0488ADE4"),
    },
    "testnet": {
        "public": bytes.fromhex("043587CF"),
        "private": bytes.fromhex("04358394"),
    },
}


def gen_master_key(seed: bytes, mainnet=True, private=False) -> ExtendedKey:
    master = hmac.new(
        key=b"Bitcoin seed",
        msg=seed,
        digestmod="sha512",
    ).digest()
    assert len(master) == 64
    left = master[:32]
    right = master[32:]

    left_int = int.from_bytes(left, "big")

    if (left_int == 0) or (left_int >= SECP256k1.order):
        raise ValueError("Invalid master key")

    private_key = SigningKey.from_secret_exponent(left_int, curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    ser_p = public_key.to_string("compressed")
    ser_256 = bytes(1) + left

    assert len(ser_p) == len(ser_256) == 33

    net = "mainnet" if mainnet else "testnet"
    vis = "private" if private else "public"

    return ExtendedKey(
        version=VERSIONS[net][vis],
        depth=bytes(1),
        finger=bytes(4),
        child_number=bytes(4),
        chain_code=right,
        key_data=ser_256 if private else ser_p,
    )


def parse_ext_key(key: str):
    """
    master - master bip32 root (extended) key, base 58
    """
    master_dec = base58.b58decode_check(
        key,
        alphabet=base58.BITCOIN_ALPHABET,
    )
    assert len(master_dec) == 78, "expected 78 bytes"
    # serialization order
    # https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#serialization-format
    key = ExtendedKey(
        version=master_dec[:4],
        depth=master_dec[4:5],  # slice to preserve bytes and not get an int
        finger=master_dec[5:9],
        child_number=master_dec[9:13],
        chain_code=master_dec[13:45],
        key_data=master_dec[45:],
    )

    assert key.version in (
        set(VERSIONS["mainnet"].values()) | set(VERSIONS["testnet"].values())
    )
    assert len(key.version) == 4
    assert len(key.finger) == len(key.child_number) == 4
    assert len(key.key_data) - 1 == 32 == len(key.chain_code)

    return key


def write_ext_key(key: str):
    pass


def CKDpriv(parent_key: ExtendedKey, path: str) -> ExtendedKey:
    # Generate a seed byte sequence S of a chosen length (between 128 and 512 bits; 256 bits is advised) from a (P)RNG.
    # Calculate I = HMAC-SHA512(Key = "Bitcoin seed", Data = S)
    # Split I into two 32-byte sequences, IL and IR.
    # Use parse256(IL) as master secret key, and IR as master chain code.
    # In case parse256(IL) is 0 or parse256(IL) ≥ n, the master key is invalid.

    # if path starts with m
    # ensure this is in fact the master key with asserts
    # recursively call CKDpriv on a chopped down path
    print(parent_key, type(parent_key.index))
    # TODO: check for master key (fingerprint 0x00... and child number 0x0000)
    hardened = parent_key.index >= 2**31
    index = parent_key.index.to_bytes(4, "big")
    if hardened:
        data = b"\x00\x00" + parent_key.key_data + index
    else:
        point = SECP256k1.generator * int.from_bytes(parent_key.key_data)
        data = point._compressed_encode() + index

    myI = hmac.new(parent_key.chain_code, data, digestmod=hashlib.sha512).digest()
