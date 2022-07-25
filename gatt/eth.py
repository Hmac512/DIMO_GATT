from eth_account import Account
from eth_account.messages import encode_defunct
from web3.auto import w3
from web3 import Web3


WALLET_SEED = "ridge mystery enact hover spell vanish element stove street yard metal reflect"
WALLET_ADDRESS = "0x5B78b008d4801a4FFae138ed3890eDBFa2de5f2D"

Account.enable_unaudited_hdwallet_features()
ETH_ACCOUNT = Account.from_mnemonic(WALLET_SEED)


def sign_message(msg):
    message = encode_defunct(text=msg)
    signed_message = w3.eth.account.sign_message(
        message, private_key=ETH_ACCOUNT._private_key)
    return Web3.toHex(signed_message.signature)
