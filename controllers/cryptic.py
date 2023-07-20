from rsa import encrypt, decrypt


def _encrypt(text, key):
    encryptedData = encrypt(text.encode("ascii"), key)

    return encryptedData.hex()

def _decrypt(data, key):
    cipherText = bytes.fromhex(data)
    print(cipherText)
    text = decrypt(cipherText, key).decode("ascii")

    return text