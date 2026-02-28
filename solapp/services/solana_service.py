import hashlib
import hmac
import base58
from nacl.signing import SigningKey
from nacl.encoding import RawEncoder


def _derive_master_keys(seed):
    h = hmac.new(b"ed25519 seed", seed, hashlib.sha512)
    master = h.digest()
    return master[:32], master[32:]


def _derive_child_key(parent_key, parent_chain_code, index):
    if index < 0x80000000:
        index += 0x80000000
    data = b'\x00' + parent_key + index.to_bytes(4, 'big')
    h = hmac.new(parent_chain_code, data, hashlib.sha512)
    child = h.digest()
    return child[:32], child[32:]


def _derive_path(seed, path):
    parts = path.replace('m/', '').split('/')
    key, chain = _derive_master_keys(seed)
    for part in parts:
        index = int(part[:-1]) if part.endswith("'") else int(part)
        key, chain = _derive_child_key(key, chain, index)
    return key


def derive_solana_addresses(mnemonic, num_accounts=1):
    """
    Derive Solana addresses from a BIP39 mnemonic phrase.

    Args:
        mnemonic     (str): BIP39 mnemonic string (12 space-separated words)
        num_accounts (int): Number of account indices to derive (1-10)

    Returns:
        list of dicts, each with:
            'address'         (str): base58-encoded Solana public key
            'derivation_path' (str): BIP32 path used
            'account_index'   (int): account index (0-based)
    """
    seed = hashlib.pbkdf2_hmac(
        "sha512",
        mnemonic.encode("utf-8"),
        b"mnemonic",
        2048,
        64,
    )

    results = []
    for account in range(num_accounts):
        path = f"m/44'/501'/{account}'/0'"
        private_key_bytes = _derive_path(seed, path)
        signing_key = SigningKey(private_key_bytes)
        public_key_bytes = signing_key.verify_key.encode(encoder=RawEncoder)
        address = base58.b58encode(public_key_bytes).decode('utf-8')
        results.append({
            'address': address,
            'derivation_path': path,
            'account_index': account,
        })

    return results
