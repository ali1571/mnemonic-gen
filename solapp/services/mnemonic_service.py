import random
import hashlib
import os
from django.conf import settings


class MnemonicGenerator:
    """BIP39 Mnemonic Generator Service"""

    def __init__(self):
        # Load word lists once when class is instantiated
        self.words = self._load_wordlist()
        self.binary_dict = self._load_binary_dict()

    def _load_wordlist(self):
        """Load BIP39 word list"""
        # Put your KEYTOWORD.txt in solapp/data/
        wordlist_path = os.path.join(settings.BASE_DIR, 'solapp', 'data', 'KEYTOWORD.txt')
        with open(wordlist_path, 'r') as f:
            return f.read().split()

    def _load_binary_dict(self):
        """Load binary mappings"""
        binary_path = os.path.join(settings.BASE_DIR, 'solapp', 'data', 'BIP39-Binaries.txt')
        with open(binary_path, 'r') as f:
            return dict(line.strip().split() for line in f)

    def _generate_single_mnemonic(self):
        """Generate one valid mnemonic phrase"""
        while True:
            # Generate 12 random words
            random_words = [random.choice(self.words) for _ in range(12)]

            # Build 132-bit binary string
            bit132_binary_list = [self.binary_dict[word] for word in random_words]
            bit132_binary_string = "".join(bit132_binary_list)

            # Extract checksum and entropy
            last_4_check_bits = bit132_binary_string[128:132]
            entropy_bit = bit132_binary_string[0:128]

            # Calculate SHA-256 hash
            byte_data = int(entropy_bit, 2).to_bytes(16, byteorder='big')
            sha256_hash = hashlib.sha256(byte_data).hexdigest()
            sha_hex_bin = bin(int(sha256_hash, 16))[2:].zfill(256)
            first_four_shabit = sha_hex_bin[0:4]

            # Validate checksum
            if first_four_shabit == last_4_check_bits:
                return " ".join(random_words)  # Return as single string

    def generate(self, count=1):
        """
        Generate multiple valid mnemonics

        Args:
            count (int): Number of mnemonics to generate (1-100)

        Returns:
            list: List of mnemonic phrases (strings)
        """
        return [self._generate_single_mnemonic() for _ in range(count)]


# Create singleton instance
mnemonic_generator = MnemonicGenerator()


# Simple function interface for views
def generate_mnemonics(count=1):
    """
    Public API for generating mnemonics

    Args:
        count (int): Number of mnemonics (1-100)

    Returns:
        list: List of mnemonic phrase strings
    """
    if count < 1 or count > 100:
        raise ValueError("Count must be between 1 and 100")

    return mnemonic_generator.generate(count)

