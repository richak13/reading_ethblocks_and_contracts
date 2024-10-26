import random
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.providers.rpc import HTTPProvider


# If you use one of the suggested infrastructure providers, the url will be of the form
# now_url  = f"https://eth.nownodes.io/{now_token}"
# alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
# infura_url = f"https://mainnet.infura.io/v3/{infura_token}"

def connect_to_eth():
    url = "https://mainnet.infura.io/v3/f474620ee28c4a6185ac4f3facbd6cf6"
    w3 = Web3(HTTPProvider(url))
    assert w3.is_connected(), f"Failed to connect to provider at {url}"
    return w3


def connect_with_middleware(contract_json):
    with open(contract_json, "r") as f:
        d = json.load(f)
        d = d['bsc']
        address = d['address']
        abi = d['abi']

    bnb_url = "https://bsc-dataseed.binance.org/"
    w3 = Web3(HTTPProvider(bnb_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.is_connected(), f"Failed to connect to provider at {bnb_url}"
    contract = w3.eth.contract(address=address, abi=abi)

    return w3, contract


def is_ordered_block(w3, block_num):
    """
    Determines if transactions in the block are ordered by priority fee.
    """
    block = w3.eth.get_block(block_num, full_transactions=True)
    ordered = True  # Assume ordered until proven otherwise

    # Before EIP-1559: check decreasing order of gasPrice
    for i in range(len(block.transactions) - 1):
        if block.transactions[i].gasPrice < block.transactions[i + 1].gasPrice:
            ordered = False
            break

    # After EIP-1559: check priority fee for type 0 and 2 transactions
    if block.number >= 12965000:  # London Hard Fork introduced EIP-1559
        base_fee = block.baseFeePerGas
        for tx in block.transactions:
            if tx.type == "0x0":  # Type 0 transaction
                priority_fee = tx.gasPrice - base_fee
            elif tx.type == "0x2":  # Type 2 transaction
                priority_fee = min(tx.maxPriorityFeePerGas, tx.maxFeePerGas - base_fee)

            if i > 0 and priority_fee > previous_priority_fee:
                ordered = False
                break

            previous_priority_fee = priority_fee

    return ordered


def get_contract_values(contract, admin_address, owner_address):
    """
    Retrieves contract values, checking for Merkle root, admin role, and prime ownership.
    """
    default_admin_role = int.to_bytes(0, 32, byteorder="big")

    # Get Merkle root from the contract
    onchain_root = contract.functions.merkleRoot().call()

    # Check if the admin address has the default admin role
    has_role = contract.functions.hasRole(default_admin_role, admin_address).call()

    # Get prime owned by the owner address
    prime = contract.functions.prime(owner_address).call()

    return onchain_root, has_role, prime


if __name__ == "__main__":
    admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
    owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
    contract_file = "contract_info.json"

    eth_w3 = connect_to_eth()
    cont_w3, contract = connect_with_middleware(contract_file)

    latest_block = eth_w3.eth.get_block_number()
    london_hard_fork_block_num = 12965000
    assert latest_block > london_hard_fork_block_num, f"Error: the chain never got past the London Hard Fork"

    n = 5
    for _ in range(n):
        block_num = random.randint(1, latest_block)
        ordered = is_ordered_block(eth_w3, block_num)
        if ordered:
            print(f"Block {block_num} is ordered")
        else:
            print(f"Block {block_num} is not ordered")
