import logging

import pytest
from data.bip32_vectors import INVALID_KEYS, VECTORS

from bip32 import to_master_key
from bip32types import parse_ext_key
from bip85 import derive
from util import LOGGER, from_hex

logger = logging.getLogger(LOGGER)


@pytest.mark.parametrize(
    "vector",
    VECTORS,
    ids=[
        f"Vector-{i + 1}-{', '.join(e['chain'].keys())}" for i, e in enumerate(VECTORS)
    ],
)
def test_vectors(vector):
    seed = from_hex(vector["seed_hex"])
    for ch, tests in vector["chain"].items():
        for type_, expected in tests.items():
            assert type_ in ("ext pub", "ext prv")
            master = to_master_key(seed, mainnet=True, private=True)
            derived = derive(master, ch, private=type_ == "ext prv")
            if not str(derived) == expected:
                logger.error("derived:")
                logger.error(repr(derived))
                logger.error("expected:")
                logger.error(repr(parse_ext_key(expected)))
            assert str(derived) == expected


@pytest.mark.parametrize(
    "key, reason",
    INVALID_KEYS,
    ids=[f"Vector-5-{reason[:32]}-{key[:8]}" for key, reason in INVALID_KEYS],
)
def test_invalid_keys(key, reason):
    with pytest.raises((AssertionError, ValueError)):
        parse_ext_key(key)
