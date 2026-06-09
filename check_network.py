from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://rpc.tanenbaum.io", request_kwargs={"timeout": 30}))

txs = [
    "0x6faf6098cdbc3b55205cf9678e66de110df9b5931a038f87c473f0c0c796a318",
    "0xf3926872449d3476e41538ed7b587ecf238b4b92429ca22e65cd29396f2cf29f"
]
for tx in txs:
    try:
        receipt = w3.eth.get_transaction_receipt(tx)
        print("TX " + tx[:18] + " -> CONFIRMADA Status=" + str(receipt.status) + " Contract=" + str(receipt.contractAddress))
    except Exception:
        try:
            t = w3.eth.get_transaction(tx)
            print("TX " + tx[:18] + " -> PENDIENTE nonce=" + str(t.nonce) + " gasPrice=" + str(t.gasPrice))
        except Exception:
            print("TX " + tx[:18] + " -> NO ENCONTRADA")

wallet = Web3.to_checksum_address("0xf538AF7359480322cB189572B17161B59Cb754dE")
nonce_pending = w3.eth.get_transaction_count(wallet, "pending")
nonce_latest = w3.eth.get_transaction_count(wallet, "latest")
gas_price = w3.eth.gas_price
block = w3.eth.block_number
bal = w3.from_wei(w3.eth.get_balance(wallet), "ether")
gp_gwei = w3.from_wei(gas_price, "gwei")

print("Nonce latest: " + str(nonce_latest) + ", pending: " + str(nonce_pending))
print("Gas price red: " + str(gas_price) + " wei = " + str(gp_gwei) + " gwei")
print("Bloque actual: " + str(block))
print("Balance: " + str(bal) + " tSYS")

# Check latest block gas info
latest_block = w3.eth.get_block("latest")
print("Base fee: " + str(getattr(latest_block, "baseFeePerGas", "N/A")))
print("Block gas limit: " + str(latest_block.gasLimit))
print("Block gas used: " + str(latest_block.gasUsed))
print("Block txs: " + str(len(latest_block.transactions)))
